from tools.vector_store import model, collection

def search_labels(query: str, top_k: int = 4):
    query_embedding = model.encode(query).tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    
    return results