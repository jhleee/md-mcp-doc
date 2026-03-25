from __future__ import annotations

RRF_K = 60


def reciprocal_rank_fusion(
    *ranked_lists: list[str],
    k: int = RRF_K,
) -> list[tuple[str, float]]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    Each input is a list of keys ordered by relevance (best first).
    Returns (key, score) pairs sorted by descending RRF score.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, key in enumerate(ranked, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
