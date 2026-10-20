
from unittest.mock import MagicMock, patch

from app.services.rag_service import answer_question


def test_out_of_scope_question_is_rejected():
    fake_embeddings = MagicMock()
    fake_vectorstore = MagicMock()

    fake_vectorstore.similarity_search_with_score.return_value = [
        (MagicMock(), 1.9213),
        (MagicMock(), 2.0408),
        (MagicMock(), 2.0418),
    ]

    with (
        patch(
            "app.services.rag_service.create_embeddings",
            return_value=fake_embeddings,
        ),
        patch(
            "app.services.rag_service.load_vectorstore",
            return_value=fake_vectorstore,
        ),
        patch(
            "app.services.rag_service.generate_answer"
        ) as mock_generate,
    ):
        result = answer_question("What is the weather on Mars today?")

    assert "couldn't find sufficiently relevant information" in (
        result["answer"]
    )
    assert result["sources"] == []
    mock_generate.assert_not_called()


def test_relevant_question_calls_llm():
    fake_embeddings = MagicMock()
    fake_vectorstore = MagicMock()

    fake_document = MagicMock()
    fake_document.page_content = "Eligible products can be returned."
    fake_document.metadata = {"source": "return_policy.txt"}

    fake_vectorstore.similarity_search_with_score.return_value = [
        (fake_document, 0.6099),
    ]

    with (
        patch(
            "app.services.rag_service.create_embeddings",
            return_value=fake_embeddings,
        ),
        patch(
            "app.services.rag_service.load_vectorstore",
            return_value=fake_vectorstore,
        ),
        patch(
            "app.services.rag_service.generate_answer",
            return_value="Eligible products can be returned.",
        ) as mock_generate,
    ):
        result = answer_question("Can I return a product?")

    assert result["answer"] == "Eligible products can be returned."
    assert "return_policy.txt" in result["sources"]
    mock_generate.assert_called_once()
