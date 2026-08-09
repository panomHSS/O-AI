from collections.abc import Sequence

SearchRecord = dict[str, object]

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    *rankings: Sequence[SearchRecord],
    limit: int,
    k: int = DEFAULT_RRF_K,
) -> list[SearchRecord]:
    """Fuse ranked search results using reciprocal rank fusion."""

    if limit <= 0:
        return []

    if k < 0:
        raise ValueError(
            "RRF rank constant must not be negative."
        )

    scores: dict[str, float] = {}
    records: dict[str, SearchRecord] = {}

    for ranking in rankings:
        seen: set[str] = set()

        for rank, record in enumerate(
            ranking,
            start=1,
        ):
            chunk_id = str(record["chunk_id"])

            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            scores[chunk_id] = (
                scores.get(chunk_id, 0.0)
                + 1.0 / (k + rank)
            )

            if chunk_id not in records:
                records[chunk_id] = dict(record)

    ordered = sorted(
        scores,
        key=lambda chunk_id: (
            -scores[chunk_id],
            chunk_id,
        ),
    )

    results: list[SearchRecord] = []

    for chunk_id in ordered[:limit]:
        record = dict(records[chunk_id])
        record["relevance_score"] = scores[chunk_id]
        results.append(record)

    return results