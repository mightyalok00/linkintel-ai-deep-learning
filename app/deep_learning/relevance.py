from functools import lru_cache


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    try:
        import importlib
        st = importlib.import_module("sentence_transformers")
        return st.SentenceTransformer(model_name)
    except (ImportError, ModuleNotFoundError) as err:
        raise ImportError(
            "sentence_transformers is not installed. Install requirements-ml.txt to enable deep learning."
        ) from err

def semantic_similarity(query_text: str, candidate_text: str,
                        model_name: str) -> float | None:
    if not query_text.strip() or not candidate_text.strip():
        return None
    try:
        model = _load_model(model_name)
        embeddings = model.encode([query_text, candidate_text], normalize_embeddings=True)
        import numpy as np
        value = float(np.dot(embeddings[0], embeddings[1]))
        return max(-1.0, min(1.0, value))
    except (ImportError, OSError, RuntimeError, ValueError):
        return None

def batch_semantic_similarity(query_text: str, candidate_texts: list[str],
                              model_name: str) -> list[float | None]:
    """
    Computes cosine similarity between query_text and multiple candidate_texts in a single
    vectorized batch forward pass for high throughput.
    """
    if not query_text.strip() or not candidate_texts:
        return [None] * len(candidate_texts)
    try:
        model = _load_model(model_name)
        valid_indices = [i for i, t in enumerate(candidate_texts) if t and t.strip()]
        if not valid_indices:
            return [None] * len(candidate_texts)
        texts_to_encode = [query_text] + [candidate_texts[i] for i in valid_indices]
        embeddings = model.encode(texts_to_encode, normalize_embeddings=True)
        import numpy as np
        query_vec = embeddings[0]
        results: list[float | None] = [None] * len(candidate_texts)
        for offset, orig_idx in enumerate(valid_indices):
            cand_vec = embeddings[1 + offset]
            sim = float(np.dot(query_vec, cand_vec))
            results[orig_idx] = max(-1.0, min(1.0, sim))
        return results
    except (ImportError, OSError, RuntimeError, ValueError):
        return [None] * len(candidate_texts)
