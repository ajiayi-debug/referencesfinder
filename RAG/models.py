from pydantic import BaseModel
from typing import List, Optional

class Article(BaseModel):
    id: str
    sentiment: str
    sievingByGPT4o: List[str]
    chunk: List[str]
    articleName: str
    statement: str
    summary: str
    authors: str
    date: int
    rating: str

class Reference(BaseModel):
    id: str
    articleName: str
    authors: str
    date: int

class ReplacementTask(BaseModel):
    statement: str
    oldReferences: List[Reference]
    newReferences: List[Reference]

class AdditionTask(BaseModel):
    statement: str
    newReferences: List[Reference]

class EditTask(BaseModel):
    statement:str
    edits:str
    newReferences: List[Reference]


