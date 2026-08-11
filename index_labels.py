from tools.loader import load_pdf_pages
from tools.chunker import chunk_text
from tools.vector_store import store_chunks, collection


pages = load_pdf_pages(
    "data/labels/pcm.pdf"
)

print("Pages loaded:", len(pages))

chunks = chunk_text(pages)

print("Chunks created:", len(chunks))

store_chunks(
    chunks=chunks,
    source="paracetamol"
)

print("Documents in Chroma:", collection.count())