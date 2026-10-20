
from app.services.embedding_service import (
    create_embeddings,
    load_vectorstore,
)


def main():
    print("Loading embedding model...")
    embeddings = create_embeddings()

    print("Loading FAISS index...")
    vectorstore = load_vectorstore(embeddings)

    questions = [
        "Can I return a product after 20 days?",
        "How long does an approved refund take?",
        "Can I cancel an order after it has shipped?",
        "Does ShopEase offer free international shipping?",
    ]

    for question in questions:
        print("\n" + "=" * 70)
        print(f"QUESTION: {question}")

        results = vectorstore.similarity_search_with_score(
            question,
            k=3,
        )

        for rank, (document, score) in enumerate(results, start=1):
            print(f"\nResult {rank}")
            print(f"Source: {document.metadata.get('source', 'Unknown')}")
            print(f"Distance: {score:.4f}")
            print(f"Content: {document.page_content}")


if __name__ == "__main__":
    main()
