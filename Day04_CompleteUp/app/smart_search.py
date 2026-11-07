"""Day 4: TF-IDF and cosine-similarity recipe search."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.records import load_records

def _document(record):
    ingredients = " ".join(record.get("ingredients", []) or [])
    return f'{record.get("dish_name", "")} {record.get("region_or_type", "")} {ingredients}'

def smart_search(query, limit=10):
    records = load_records()
    query = query.strip()
    if not query or not records:
        return []
    documents = [_document(record) for record in records]
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(documents + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    return [
        {**records[index], "score": round(float(score), 4)}
        for index, score in ranked[:limit] if score > 0
    ]
