import os
import subprocess
from openai import AzureOpenAI
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage

from langgraph.graph.message import add_messages
from prompt_template import *

from typing import Annotated, Literal, Sequence, TypedDict

from langchain import hub
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import AzureChatOpenAI

from langgraph.prebuilt import tools_condition
from langchain_community.document_loaders import PyPDFLoader

from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode


import pprint

os.environ['USER_AGENT'] = 'myagent'

load_dotenv()


az_path = os.getenv("az_path")

# Fetch Azure OpenAI access token
result = subprocess.run([az_path, 'account', 'get-access-token', '--resource', 'https://cognitiveservices.azure.com', '--query', 'accessToken', '-o', 'tsv'], stdout=subprocess.PIPE)
token = result.stdout.decode('utf-8').strip()

# Set environment variables
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv('endpoint')
os.environ['AZURE_OPENAI_API_KEY'] = token
embedding_model=os.getenv('embed_model')


# urls = [
#     "https://lilianweng.github.io/posts/2023-06-23-agent/",
#     "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
#     "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
# ]

# docs = [WebBaseLoader(url).load() for url in urls]
# docs_list = [item for sublist in docs for item in sublist]

directory='text'
pdf_paths = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.pdf')]

# Load documents from each PDF
docs = [PyPDFLoader(pdf_path).load() for pdf_path in pdf_paths]

# Flatten the list of documents
docs_list = [item for sublist in docs for item in sublist]


text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=100, chunk_overlap=50
)
doc_splits = text_splitter.split_documents(docs_list)

# Add to vectorDB
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="rag-chroma",
    embedding=AzureOpenAIEmbeddings(model=embedding_model, api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver')),
)
retriever = vectorstore.as_retriever()


from langchain.tools.retriever import create_retriever_tool

retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_blog_posts",
    "Search and return information about Lactose intolerance.",
)

tools = [retriever_tool]

class AgentState(TypedDict):
    # The add_messages function defines how an update should be processed
    # Default is to replace. add_messages says "append"
    messages: Annotated[Sequence[BaseMessage], add_messages]

def grade_documents(state) -> Literal["generate", "rewrite"]:
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (messages): The current state

    Returns:
        str: A decision for whether the documents are relevant or not
    """

    print("---CHECK RELEVANCE---")

    # Data model
    class grade(BaseModel):
        """Binary score for relevance check."""

        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    # LLM
    model = AzureChatOpenAI(temperature=0, model=os.getenv('gpt-4'), streaming=True, api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver'))

    # LLM with tool and validation
    llm_with_tool = model.with_structured_output(grade)

    # Prompt
    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
        Here is the retrieved document: \n\n {context} \n\n
        Here is the user question: {question} \n
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
        input_variables=["context", "question"],
    )

    # Chain
    chain = prompt | llm_with_tool

    messages = state["messages"]
    last_message = messages[-1]

    question = messages[0].content
    docs = last_message.content

    scored_result = chain.invoke({"question": question, "context": docs})

    score = scored_result.binary_score

    if score == "yes":
        print("---DECISION: DOCS RELEVANT---")
        return "generate"

    else:
        print("---DECISION: DOCS NOT RELEVANT---")
        print(score)
        return "rewrite"


### Nodes


def agent(state):
    """
    Invokes the agent model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply end.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with the agent response appended to messages
    """
    print("---CALL AGENT---")
    messages = state["messages"]
    model = AzureChatOpenAI(temperature=0, streaming=True, model=os.getenv('gpt-4'), api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver') )
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


def rewrite(state):
    """
    Transform the query to produce a better question.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with re-phrased question
    """

    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    question = messages[0].content

    msg = [
        HumanMessage(
            content=f""" \n 
    Look at the input and try to reason about the underlying semantic intent / meaning. \n 
    Here is the initial question:
    \n ------- \n
    {question} 
    \n ------- \n
    Formulate an improved question: """,
        )
    ]

    # Grader
    model = AzureChatOpenAI(temperature=0, streaming=True, model=os.getenv('gpt-4'), api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver') )
    response = model.invoke(msg)
    return {"messages": [response]}

import requests
from requests.exceptions import SSLError



def generate(state):
    """
    Generate answer

    Args:
        state (messages): The current state

    Returns:
         dict: The updated state with re-phrased question
    """
    try:
        print("---GENERATE---")
        messages = state["messages"]
        question = messages[0].content
        last_message = messages[-1]

        docs = last_message.content

        # Prompt
        # prompt = hub.pull("rlm/rag-prompt")
    

        # LLM
        llm = AzureChatOpenAI(temperature=0, streaming=True, model=os.getenv('gpt-35'), api_key=token, azure_endpoint=os.getenv('endpoint'), api_version=os.getenv('ver'))

        # Post-processing
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Chain
        rag_chain = prompt | llm | StrOutputParser()

        # Run
        response = rag_chain.invoke({"context": docs, "question": question})
        return {"messages": [response]}

    except SSLError as ssl_error:
        print(f"SSL Error occurred: {ssl_error}")
        return {"messages": [("system", "An SSL error occurred. Please try again later.")]}
    except Exception as e:
        print(f"An error occurred: {e}")
        return {"messages": [("system", "An error occurred while generating the response. Please try again later.")]}

# Define a new graph
workflow = StateGraph(AgentState)

# Define the nodes we will cycle between
workflow.add_node("agent", agent)  # agent
retrieve = ToolNode([retriever_tool])
workflow.add_node("retrieve", retrieve)  # retrieval
workflow.add_node("rewrite", rewrite)  # Re-writing the question
workflow.add_node(
    "generate", generate
)  # Generating a response after we know the documents are relevant
# Call agent node to decide to retrieve or not
workflow.add_edge(START, "agent")

# Decide whether to retrieve
workflow.add_conditional_edges(
    "agent",
    # Assess agent decision
    tools_condition,
    {
        # Translate the condition outputs to nodes in our graph
        "tools": "retrieve",
        END: END,
    },
)

# Edges taken after the `action` node is called.
workflow.add_conditional_edges(
    "retrieve",
    # Assess agent decision
    grade_documents,
)
workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

# Compile
graph = workflow.compile()

inputs = {
    "messages": [
        ("user", "Is there any information about: A proportion of the world’s population is able to tolerate lactose as they have a genetic variation that ensures they continue to produce sufficient quantities of the enzyme lactase after childhood."),
    ]
}
for output in graph.stream(inputs):
    for key, value in output.items():
        pprint.pprint(f"Output from node '{key}':")
        pprint.pprint("---")
        pprint.pprint(value, indent=2, width=80, depth=None)
    pprint.pprint("\n---\n")