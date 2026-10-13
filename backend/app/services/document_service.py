
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS_DIR = PROJECT_ROOT / "backend" / "data" / "documents"


def load_documents() -> list[Document]:
    """Load supported text and PDF files from the knowledge base."""

    documents = []

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(
            f"Knowledge-base directory not found: {DOCUMENTS_DIR}"
        )

    for file_path in sorted(DOCUMENTS_DIR.iterdir()):
        if file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8")

        elif file_path.suffix.lower() == ".pdf":
            import fitz

            with fitz.open(file_path) as pdf:
                text = "\n".join(page.get_text() for page in pdf)

        else:
            continue

        text = text.strip()

        if not text:
            print(f"Warning: No extractable text in {file_path.name}")
            continue

        documents.append(
            Document(
                page_content=text,
                metadata={"source": file_path.name}
            )
        )

    if not documents:
        raise ValueError(
            f"No readable documents found in {DOCUMENTS_DIR}"
        )

    return documents


def split_documents(
    documents: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Document]:
    """Split documents into overlapping chunks for retrieval."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be non-negative and smaller than chunk_size"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index

    return chunks
