
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


PROJECT_ROOT = Path(__file__).resolve().parents[3]
VECTORSTORE_DIR = PROJECT_ROOT / "backend" / "data" / "vectorstore"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def create_embeddings() -> HuggingFaceEmbeddings:
    """Initialize and reuse the local embedding model."""
    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=1)
def _load_vectorstore_cached() -> FAISS:
    """Load and cache the FAISS index for the current process."""
    index_file = VECTORSTORE_DIR / "index.faiss"

    if not index_file.exists():
        raise FileNotFoundError(
            f"FAISS index not found at {index_file}. "
            "Build the vector store first."
        )

    return FAISS.load_local(
        str(VECTORSTORE_DIR),
        create_embeddings(),
        allow_dangerous_deserialization=True,
    )


def load_vectorstore(
    embeddings: HuggingFaceEmbeddings | None = None,
) -> FAISS:
    """Load the cached FAISS index.

    The optional argument preserves compatibility with existing callers.
    """
    return _load_vectorstore_cached()


def build_vectorstore(
    chunks: list[Document],
    embeddings: HuggingFaceEmbeddings,
) -> FAISS:
    """Create and persist a FAISS index from document chunks."""
    if not chunks:
        raise ValueError("Cannot build a vector store without document chunks")

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    vectorstore = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )

    vectorstore.save_local(str(VECTORSTORE_DIR))

    # Ensure subsequent loads use the newly built index.
    _load_vectorstore_cached.cache_clear()

    return vectorstore
