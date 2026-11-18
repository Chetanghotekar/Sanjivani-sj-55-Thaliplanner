"""Shared test setup: a fast fake embedding model so tests need no download or internet."""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


STOPWORDS = {"which", "what", "can", "i", "make", "with", "do", "you", "the", "is", "a", "an", "in", "of",
             "to", "for", "and", "are", "how", "does", "it", "your", "have", "from", "on", "or"}


def fake_embed_texts(texts):
    """Hash each non-stopword into one of 128 slots, then normalise. Shared words give similar vectors."""
    vectors = np.zeros((len(texts), 128), dtype=np.float32)
    for row, text in enumerate(texts):
        words = str(text).lower().replace(",", " ").replace(".", " ").replace("?", " ").split()
        for word in words:
            if word in STOPWORDS:
                continue
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 128] += 1.0
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    """Point ChromaDB at a temp folder and replace the real embedding model."""
    import app.vectorstore as vs
    monkeypatch.setattr(vs, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(vs, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(vs, "_index_checked", False)
    return vs
