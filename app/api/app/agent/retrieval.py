"""Lexical search over approved demo documents. No model writes the answer."""

import re

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "what",
    "when",
    "where",
    "does",
    "are",
    "was",
    "how",
    "can",
    "into",
    "about",
}


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if token not in STOPWORDS and len(token) > 2
    }


def search_chunks(
    chunks: list[dict[str, str]], query: str
) -> tuple[list[dict[str, str]], str | None]:
    query_tokens = tokens(query)
    if len(query_tokens) < 2:
        return [], "The question does not contain enough terms to search the approved documents."
    scored: list[tuple[int, dict[str, str]]] = []
    for chunk in chunks:
        overlap = query_tokens & tokens(chunk["text"])
        if len(overlap) >= 2:
            scored.append((len(overlap), chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["title"], item[1]["text"]))
    if not scored:
        return [], "No approved document covers that question."
    return [item[1] for item in scored[:3]], None
