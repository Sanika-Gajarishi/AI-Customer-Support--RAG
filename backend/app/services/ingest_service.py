
import logging

from app.services.document_service import load_documents, split_documents
from app.services.embedding_service import create_embeddings, build_vectorstore

logger = logging.getLogger(__name__)


def main():
    logger.info("Loading ShopEase policy documents...")
    documents = load_documents()

    if not documents:
        raise ValueError(
            "No policy documents found. The knowledge base was not rebuilt."
        )

    logger.info("Loaded %s documents.", len(documents))

    logger.info("Splitting documents into chunks...")
    chunks = split_documents(documents)

    if not chunks:
        raise ValueError(
            "No document chunks were created. The knowledge base was not rebuilt."
        )

    logger.info("Created %s chunks.", len(chunks))

    logger.info("Loading the embedding model...")
    embeddings = create_embeddings()

    logger.info("Building the FAISS vector index...")
    vectorstore = build_vectorstore(chunks, embeddings)

    logger.info(
        "FAISS index built successfully. Indexed chunks: %s",
        vectorstore.index.ntotal,
    )

    return vectorstore


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
