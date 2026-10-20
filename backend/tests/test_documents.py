
from app.services.document_service import load_documents, split_documents


def main():
    documents = load_documents()
    chunks = split_documents(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    for chunk in chunks:
        print(
            f"\nSource: {chunk.metadata['source']}"
            f"\nChunk ID: {chunk.metadata['chunk_id']}"
            f"\nContent: {chunk.page_content[:200]}"
        )


if __name__ == "__main__":
    main()
