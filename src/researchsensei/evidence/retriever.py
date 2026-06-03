from __future__ import annotations

import math
import re
from collections import Counter

from researchsensei.schemas.evidence import EvidenceRetrievalResult, PassageIndex

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tokenize(text: str) -> list[str]:
    """Lowercase and split into alphanumeric tokens, preserving decimals like 95.2."""
    return TOKEN_PATTERN.findall(text.lower())


def compute_idf(corpus_tokens: list[list[str]]) -> dict[str, float]:
    """Compute IDF for each term in the corpus."""
    n = len(corpus_tokens)
    if n == 0:
        return {}
    doc_freq: Counter = Counter()
    for tokens in corpus_tokens:
        doc_freq.update(set(tokens))
    return {
        term: math.log((n - df + 0.5) / (df + 0.5) + 1)
        for term, df in doc_freq.items()
    }


def bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    avg_doc_len: float,
    idf: dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """BM25 scoring function."""
    if avg_doc_len <= 0:
        return 0.0
    doc_len = len(doc_tokens)
    tf = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        if qt not in tf or qt not in idf:
            continue
        numerator = tf[qt] * (k1 + 1)
        denominator = tf[qt] + k1 * (1 - b + b * doc_len / avg_doc_len)
        score += idf[qt] * numerator / denominator
    return score


class EvidenceRetriever:
    def __init__(
        self,
        *,
        top_k: int = 5,
        min_score: float = 0.5,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.top_k = top_k
        self.min_score = min_score
        self.k1 = k1
        self.b = b

    def retrieve(
        self,
        query: str,
        passage_index: PassageIndex,
    ) -> list[EvidenceRetrievalResult]:
        """Retrieve passages relevant to a query using BM25."""
        if not query.strip():
            return []
        if not passage_index.passages:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Build corpus
        corpus_tokens = [tokenize(p.text) for p in passage_index.passages]
        total_tokens = sum(len(t) for t in corpus_tokens)
        avg_doc_len = total_tokens / len(corpus_tokens) if corpus_tokens else 0.0

        if avg_doc_len <= 0:
            return []

        idf = compute_idf(corpus_tokens)

        # Score each passage
        scored: list[tuple[int, float, list[str]]] = []
        for i, doc_tokens in enumerate(corpus_tokens):
            score = bm25_score(query_tokens, doc_tokens, avg_doc_len, idf, self.k1, self.b)
            matched = sorted(set(query_tokens) & set(doc_tokens))
            scored.append((i, score, matched))

        # Filter and sort
        results: list[EvidenceRetrievalResult] = []
        for i, score, matched in sorted(scored, key=lambda x: x[1], reverse=True):
            if score < self.min_score:
                continue
            passage = passage_index.passages[i]
            results.append(
                EvidenceRetrievalResult(
                    passage_id=passage.passage_id,
                    score=round(score, 6),
                    matched_terms=matched,
                    evidence_ref=passage.evidence_refs[0] if passage.evidence_refs else "",
                )
            )
            if len(results) >= self.top_k:
                break

        return results
