from strands import tool
from tools.retriever import search_labels


@tool
def search_drug_label(query: str) -> str:

    results = search_labels(query, top_k=4)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    response_parts = []

    for document, metadata in zip(documents, metadatas):

        response_parts.append(
              f"""
                Source: {metadata["source"]}
                Page: {metadata["page_number"]}
                Chunk: {metadata["chunk_id"]}

                {document}
                """
        )

    return "\n".join(response_parts)