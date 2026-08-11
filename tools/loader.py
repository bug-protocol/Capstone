import fitz
from pathlib import Path


def load_pdf_pages(pdf_path: str) -> list[dict]:
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    pages = []

    with fitz.open(pdf_path) as document:

        for page_number, page in enumerate(
            document,
            start=1
        ):
            text = page.get_text()

            pages.append({
                "page_number": page_number,
                "text": text
            })

    return pages