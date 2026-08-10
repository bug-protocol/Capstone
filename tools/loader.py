import fitz
from pathlib import Path

def load_pdf_text(pdf_path: str) -> str:
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        raise FileNotFoundError("Pdf file not found: {pdf_path}")
    
    document = fitz.open(pdf_path)
    
    pages = []
    
    for page_number, page in enumerate(document, start=1):
        text = page.get_text()
        
        pages.append(
            f"\n--- PAGE{page_number} ---\n{text}"
        )
        
    document.close()
    
    return "\n".join(pages)
        