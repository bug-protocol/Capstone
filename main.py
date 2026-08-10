from tools.loader import load_pdf_text
from tools.chunker import chunk_text
from tools.vector_store import store_chunks
from tools.retriever import search_labels


text = load_pdf_text("data/labels/azi.pdf")

chunks = chunk_text(text)

store_chunks(
    chunks=chunks,
    source="azi"
)

results = search_labels(
    "What are the adverse reactions?"
)

print(results)