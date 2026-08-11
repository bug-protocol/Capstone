import chromadb
from sentence_transformers import SentenceTransformer


model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path="data/chroma_db")

collection = client.get_or_create_collection(
    name="drug_labels"
)

def store_chunks(chunks: list[dict], source: str):
    
    documents = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(documents).tolist()

    ids = [
        f"{source}_{i}"
        for i in range(len(chunks))
    ]

    metadatas = [
        {
            "source": source,
            "chunk_id": i,
            "page_number": chunk["page_number"]
        }
        for i, chunk in (enumerate(chunks))
    ]

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
print(collection.count())