# Capstone
## Description
A drug-safety and medical-information agent built with the Strands Agents SDK, deployed on Amazon Bedrock AgentCore Runtime, and served through a full FastAPI backend with real login and auth. This project is the practical test of AgentCore Runtime, Observability and Production Engineering modules.

## Process

### LabelAgent

- Initially we're starting with LabelAgent where we'll store 3 PDF files for 3 different medicines.

- **Inside data\labels**

        We've 3 pdfs:
            1. azi.pdf => Contains descriptions about azithromycine
            2. ozempic.pdf => Contains descriptions about ozempic
            3. pcm.pdf => Contains descriptions about Paracetamol

- **Reading PDFs => loader.py**
        We used PyMuPDF for extracting the text from PDF.
