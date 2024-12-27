from nltk.tokenize import sent_tokenize
from rapidfuzz import fuzz
import re

"""Supposed to match statements and citations in first page of frontend to extracted text and highlight the matches in extracted text but I could not get it to work in time :("""

def preprocess_text(text):
    """
    Normalize text for consistent matching.
    """
    # Remove hyphens at line breaks and newline characters
    text = re.sub(r'-\s+', '', text)  # Remove hyphens followed by whitespace
    text = text.replace('\n', ' ')    # Replace newline characters with a space
    # Normalize whitespace and lowercase
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return text

def match_texts(file_text, db_documents, threshold=70):
    """
    Matches text from a .txt file with MongoDB documents using NLTK and RapidFuzz.
    Returns original sentences for accurate highlighting.
    """
    # Remove newline characters from the file text for consistent tokenization
    file_text = file_text.replace('\n', '')

    # Tokenize the original file text into sentences
    file_sentences = sent_tokenize(file_text)

    # Preprocess each sentence for matching
    preprocessed_sentences = [preprocess_text(sentence) for sentence in file_sentences]

    # Set to store highlightable substrings (original sentences)
    highlight_words = set()

    # Fields in the database documents to be matched
    relevant_fields = ["Reference text in main article", "Date", "Name of authors", "Reference article name"]

    for doc in db_documents:
        for field in relevant_fields:
            db_field_text = preprocess_text(doc.get(field, ""))
            if not db_field_text:
                continue  # Skip empty fields

            # Fuzzy match preprocessed sentences
            for preprocessed_sentence, original_sentence in zip(preprocessed_sentences, file_sentences):
                if fuzz.partial_ratio(db_field_text, preprocessed_sentence) >= threshold:
                    # Remove newline characters from the original sentence
                    clean_sentence = original_sentence.replace('\n', '').strip()
                    highlight_words.add(clean_sentence)

    return highlight_words

