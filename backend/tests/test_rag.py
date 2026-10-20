
from app.services.rag_service import answer_question


def main():
    questions = [
        "Can I return a product after 20 days?",
        "How long does an approved refund take?",
        "Does ShopEase offer free international shipping?",
    ]

    for question in questions:
        print("\n" + "=" * 60)
        print(f"QUESTION: {question}")

        result = answer_question(question)

        print(f"\nANSWER: {result['answer']}")
        print(f"SOURCES: {result['sources']}")


if __name__ == "__main__":
    main()
