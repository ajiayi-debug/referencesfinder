from nltk.tokenize import sent_tokenize

def match_texts(file_text, db_documents):
    """
    Matches text from the .txt file with MongoDB documents.
    """
    file_sentences = set(sent_tokenize(file_text))
    print(file_sentences)
    matched_documents = []

    for doc in db_documents:
        matched = {
            "id": str(doc["_id"]),
            "matched_sentences": [],
            "matched_dates": [],
            "matched_authors": [],
            "matched_reference_names": []
        }

        # Match sentences
        if "referenceTextInMainArticle" in doc:
            sentence = doc["referenceTextInMainArticle"]
            if sentence in file_sentences:
                matched["matched_sentences"].append(sentence)

        # Match dates
        if "date" in doc and doc["date"] in file_text:
            matched["matched_dates"].append(doc["date"])

        # Match authors
        if "nameOfAuthors" in doc and doc["nameOfAuthors"] in file_text:
            matched["matched_authors"].append(doc["nameOfAuthors"])

        # Match reference article names
        if "referenceArticleName" in doc and doc["referenceArticleName"] in file_text:
            matched["matched_reference_names"].append(doc["referenceArticleName"])

        if (
            matched["matched_sentences"]
            or matched["matched_dates"]
            or matched["matched_authors"]
            or matched["matched_reference_names"]
        ):
            matched_documents.append(matched)
    print(matched_documents)
    return matched_documents
