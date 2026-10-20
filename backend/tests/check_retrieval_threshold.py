
from app.services.embedding_service import (
    create_embeddings,
    load_vectorstore,
)

TEST_QUESTIONS = [
    # Legitimate ShopEase questions
    ("Can I return a product after 20 days?", "IN_SCOPE"),
    ("How long does an approved refund take?", "IN_SCOPE"),
    ("Can I cancel an order after it has shipped?", "IN_SCOPE"),
    ("Does ShopEase offer free international shipping?", "IN_SCOPE"),
    ("What warranty coverage is available?", "IN_SCOPE"),
    ("How can I contact ShopEase support?", "IN_SCOPE"),
    ("Does ShopEase guarantee instant refunds?", "IN_SCOPE"),

    # Questions outside the available policy knowledge base
    ("What is the weather on Mars today?", "OUT_OF_SCOPE"),
    ("What is my personal bank account balance?", "OUT_OF_SCOPE"),
    ("Who won the latest World Cup?", "OUT_OF_SCOPE"),
    ("What is the capital of France?", "OUT_OF_SCOPE"),
]


def main():
    embeddings = create_embeddings()
    vectorstore = load_vectorstore(embeddings)

    print("\n=== Retrieval Threshold Diagnostics ===")

    for question, category in TEST_QUESTIONS:
        results = vectorstore.similarity_search_with_score(
            question,
            k=3,
        )

        print(f"\n[{category}] {question}")

        for rank, (document, distance) in enumerate(results, start=1):
            source = document.metadata.get("source", "Unknown")
            print(
                f"  Rank {rank}: "
                f"distance={float(distance):.4f}, source={source}"
            )


if __name__ == "__main__":
    main()
