import numpy as np
import pytest

from app.ingest.embed import DIM, embed_texts


def test_empty_returns_correct_shape():
    arr = embed_texts([])
    assert arr.shape == (0, DIM)
    assert arr.dtype == np.float32


def test_single_text_shape_and_norm():
    arr = embed_texts(["def foo(): pass"])
    assert arr.shape == (1, DIM)
    # normalized → unit L2 norm within float32 tolerance
    assert np.isclose(np.linalg.norm(arr[0]), 1.0, atol=1e-5)


def test_batch_shape_and_norms():
    texts = ["x = 1", "y = 2", "def f(): return 42"]
    arr = embed_texts(texts, batch_size=2)
    assert arr.shape == (3, DIM)
    norms = np.linalg.norm(arr, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_similar_texts_are_closer_than_dissimilar():
    related = embed_texts(["how do I send a request?", "sending an HTTP request"])
    unrelated = embed_texts(["sort a list in python", "sending an HTTP request"])
    sim_related = float(related[0] @ related[1])
    sim_unrelated = float(unrelated[0] @ unrelated[1])
    assert sim_related > sim_unrelated
