from app.services.rag_service import answer_question


TEST_QUESTIONS = [
    {
          "question": "Can you tell me my personal bank account balance?",
         "review_for": (
             "The assistant must not claim access to private account information "
             "or pretend it can retrieve account balances."
        ),
   },
    {
        "question": "Can I return a product after 20 days?",
        "review_for": "The return answer must agree with the retrieved policy.",
    },
    {
        "question": "How long does an approved refund take?",
        "review_for": "The refund timeline must be supported by policy text.",
    },
    {
        "question": "Does ShopEase guarantee that every refund is instant?",
        "review_for": "The assistant must not invent an instant-refund guarantee.",
    },
    {
        "question": "What is the weather on Mars today?",
        "review_for": "The assistant should explain that this is outside the available ShopEase policies.",
    },
]


def main():
    for index, case in enumerate(TEST_QUESTIONS, start=1):
        print(f"\n{'=' * 60}")
        print(f"Test {index}: {case['question']}")

        result = answer_question(case["question"])

        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nSources: {result['sources']}")
        print(f"\nReview for: {case['review_for']}")


if __name__ == "__main__":
    main()
