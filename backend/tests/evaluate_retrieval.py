
import json
from pathlib import Path

from app.services.embedding_service import (
    create_embeddings,
    load_vectorstore,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = (
    PROJECT_ROOT / "backend" / "data" / "evaluation_cases.json"
)

K = 3


def main():
    with CASES_FILE.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    embeddings = create_embeddings()
    vectorstore = load_vectorstore(embeddings)

    hits_at_k = 0
    reciprocal_ranks = []
    results = []

    for case in cases:
        question = case["question"]
        expected_source = case["expected_source"]

        retrieved = vectorstore.similarity_search_with_score(
            question,
            k=K,
        )

        retrieved_sources = [
            {
                "source": document.metadata.get("source", ""),
                "distance": round(float(score), 4)
            }
            for document, score in retrieved
        ]

        rank = None
        for position, item in enumerate(retrieved_sources, start=1):
            if Path(item["source"]).name.lower() == expected_source.lower():
                rank = position
                break

        hit = rank is not None
        hits_at_k += int(hit)
        reciprocal_ranks.append(1 / rank if rank else 0.0)

        results.append(
            {
                "question": question,
                "expected_source": expected_source,
                "retrieved_sources": retrieved_sources,
                "rank": rank,
                "hit_at_k": hit,
            }
        )

    hit_rate = hits_at_k / len(cases) if cases else 0
    mrr = (
        sum(reciprocal_ranks) / len(reciprocal_ranks)
        if reciprocal_ranks
        else 0
    )

    print("\n=== ShopEase RAG Retrieval Evaluation ===")
    print(f"Evaluation questions: {len(cases)}")
    print(f"Hit rate@{K}: {hit_rate:.2%}")
    print(f"Mean reciprocal rank (MRR): {mrr:.3f}")

    for result in results:
        status = "PASS" if result["hit_at_k"] else "MISS"

        print(f"\n[{status}] {result['question']}")
        print(f"Expected: {result['expected_source']}")
        print(f"Rank: {result['rank'] or 'Not in top ' + str(K)}")
        print(f"Retrieved: {result['retrieved_sources']}")

    report_file = (
        PROJECT_ROOT / "backend" / "data" / "retrieval_report.json"
    )
    report_file.write_text(
        json.dumps(
            {
                "k": K,
                "hit_rate_at_k": hit_rate,
                "mean_reciprocal_rank": mrr,
                "results": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
