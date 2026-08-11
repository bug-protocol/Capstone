def chunk_text(pages:list[dict], chunk_size:int = 1000, overlap:int = 200):
    
    chunks = []

    for page in pages:

        text = page["text"]
        page_number = page["page_number"]

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunk_text = text[start:end]

            chunks.append({
                "text": chunk_text,
                "page_number": page_number
            })

            start += chunk_size - overlap

    return chunks
    