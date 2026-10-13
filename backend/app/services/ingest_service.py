
from app.services.document_service import load_documents, split_documents
from app.services.embedding_service import create_embeddings, build_vectorstore

def main():
    print("Loading ShopEase policy documents...")
    documents = load_documents()
    print(f"Loaded {len(documents)} documents.")

    print("Splitting documents into chunks...")
    chunks = split_documents(documents)
    print(f"Created {len(chunks)} chunks.")

    print("Loading the embedding model...")
    embeddings = create_embeddings()

    print("Building the FAISS vector index...")
    vectorstore = build_vectorstore(chunks, embeddings)

    print("FAISS index created successfully.")
    print(f"Indexed chunks: {vectorstore.index.ntotal}")


if __name__ == "__main__":
    main()
