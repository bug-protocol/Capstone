# Capstone

## Description

PharmaSentry is a drug-safety and medical-information assistant built using the **Strands Agents SDK**. The application will be deployed on **Amazon Bedrock AgentCore Runtime** and exposed through a **FastAPI backend** with authentication. The goal of this project is to demonstrate practical implementation of **RAG**, **multi-agent systems**, **AgentCore Runtime**, **Memory**, **Observability**, and **Production Engineering** concepts.

---

# Process

## LabelAgent

The first specialist agent implemented is **LabelAgent**.

Its responsibility is to answer questions **only from approved drug labelling**. Instead of relying on the LLM's internal knowledge, it retrieves relevant information from indexed FDA drug labels and generates grounded responses with citations.

---

### 1. Drug Label Dataset

Inside `data/labels` we store the approved PDF labels for the medicines supported by the system.

```text
data/
└── labels/
    ├── azi.pdf       -> Azithromycin Label
    ├── ozempic.pdf   -> Ozempic Label
    └── pcm.pdf       -> Paracetamol Label
```

Each PDF acts as the source of truth for LabelAgent.

---

### 2. PDF Loading (`loader.py`)

We use **PyMuPDF (fitz)** to extract text from each PDF.

Features:

* Opens the PDF safely.
* Reads every page individually.
* Preserves the page number.
* Returns structured page data.

Example output:

```python
[
    {
        "page_number": 1,
        "text": "..."
    },
    {
        "page_number": 2,
        "text": "..."
    }
]
```

Keeping the page number allows us to generate source citations later.

---

### 3. Text Chunking (`chunker.py`)

The extracted text is divided into smaller chunks before embedding.

Configuration:

```text
Chunk Size : 1000 characters
Overlap    : 200 characters
```

Why overlap?

Without overlap, important context may be split between two chunks. By repeating the last 200 characters of one chunk in the next, retrieval quality improves.

Each chunk is stored together with its page number.

Example:

```python
{
    "text": "...",
    "page_number": 5
}
```

---

### 4. Vector Embeddings (`vector_store.py`)

Each chunk is converted into a numerical embedding using the Sentence Transformers model:

```text
all-MiniLM-L6-v2
```

The embedding model converts human-readable text into vectors that capture semantic meaning.

Example:

```text
"The common adverse reactions include nausea."

↓

[0.14, -0.22, 0.81, ...]
```

These vectors enable semantic similarity search instead of simple keyword matching.

---

### 5. Vector Database (ChromaDB)

We use **ChromaDB** as the vector database.

Each stored record contains:

* Unique chunk ID
* Chunk text
* Embedding vector
* Metadata

Metadata includes:

```python
{
    "source": "pcm",
    "chunk_id": 12,
    "page_number": 7
}
```

This metadata helps LabelAgent generate grounded responses with citations.

---

### 6. Semantic Retrieval (`retriever.py`)

When the user asks a question:

1. The query is converted into an embedding.
2. ChromaDB compares the query vector with all stored vectors.
3. The most relevant chunks are returned.

Example:

```text
User Question

"What are the adverse reactions of Paracetamol?"

        │
        ▼

Sentence Transformer

        │
        ▼

Query Embedding

        │
        ▼

ChromaDB Similarity Search

        │
        ▼

Top 3 Relevant Chunks
```

Unlike keyword search, semantic retrieval finds information based on meaning.

---

### 7. Label Search Tool (`label_search.py`)

The retrieval functionality is exposed as a **Strands Tool** using the `@tool` decorator.

Responsibilities:

* Accept a natural language query.
* Retrieve the most relevant label chunks.
* Return the chunk text together with source metadata.

Example output:

```text
Source : pcm
Page   : 8
Chunk  : 15

<Retrieved Label Text>
```

This tool is the bridge between the vector database and the agent.

---

### 8. LabelAgent (`label_agent.py`)

The LabelAgent is implemented using the Strands SDK.

Responsibilities:

* Answer only from approved drug labels.
* Always use the label search tool before answering factual questions.
* Never fabricate information.
* Include source citations.
* Refuse to provide unsupported information.
* Avoid personalized medical advice.

Architecture:

```text
User Question
      │
      ▼
LabelAgent
      │
      ▼
search_drug_label Tool
      │
      ▼
Semantic Retrieval
      │
      ▼
ChromaDB
      │
      ▼
Relevant Chunks
      │
      ▼
Grounded Response with Citation
```

---

## SafetyAgent


The **SafetyAgent** is the second specialist agent in PharmaSentry.

Its responsibility is to answer questions related to **reported adverse drug events** by retrieving live data from the **openFDA Drug Event API**. Unlike the LabelAgent, which relies on a local vector database, the SafetyAgent works with real-time public safety reports published by the U.S. Food and Drug Administration (FDA).

---

### Purpose

SafetyAgent helps answer questions such as:

* What adverse events have been reported for Paracetamol?
* What are the most frequently reported reactions for Ozempic?
* What adverse events are associated with Azithromycin?

The agent **does not determine whether a drug caused an adverse event**. It only summarizes reported events from the FDA reporting system.

---

### Working Architecture

```text
                    User Question
                          │
                          ▼
                    SafetyAgent
                          │
                          ▼
             search_adverse_events Tool
                          │
                          ▼
                  openFDA Drug Event API
                          │
                          ▼
                  JSON Response (Reports)
                          │
                          ▼
             Extract Reported Reactions
                          │
                          ▼
                 Count Event Frequency
                          │
                          ▼
              Top Reported Adverse Events
                          │
                          ▼
          LLM Generates Human Summary
                          │
                          ▼
                    Final Response
```

---

### openFDA Drug Event API

The SafetyAgent retrieves adverse-event reports from the public **openFDA Drug Event API**.

API Endpoint:

```text
https://api.fda.gov/drug/event.json
```

The API contains spontaneous adverse-event reports submitted to the FDA.

Example request:

```text
https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:"PARACETAMOL"&limit=20
```

This request asks the FDA database to return the first 20 adverse-event reports that mention **Paracetamol** as the medicinal product.

---

### Safety Tool (`search_adverse_events`)

The openFDA integration is implemented as a **Strands Tool**.

Responsibilities:

* Receive a drug name.
* Query the openFDA API.
* Retrieve adverse-event reports.
* Extract reported reactions.
* Count the occurrence of each reaction.
* Return the most frequently reported reactions.

Since the tool is decorated using `@tool`, the SafetyAgent can invoke it automatically whenever required.

---

### Sending the API Request

The tool builds an HTTP GET request.

Example:

```python
params = {
    "search": 'patient.drug.medicinalproduct:"PARACETAMOL"',
    "limit": 20
}
```

This tells openFDA to search for reports involving **Paracetamol** and return up to **20 reports**.

The request is executed using the Python `requests` library.

---

### Processing the Response

The API returns JSON similar to:

```json
{
    "results": [
        {
            "patient": {
                "reaction": [
                    {
                        "reactionmeddrapt": "Headache"
                    },
                    {
                        "reactionmeddrapt": "Nausea"
                    }
                ]
            }
        }
    ]
}
```

Each report may contain one or more adverse reactions.

The tool iterates through every report and extracts the value of:

```text
reactionmeddrapt
```

which represents the standardized medical term describing the reported reaction.

Examples include:

* Headache
* Nausea
* Vomiting
* Rash
* Dizziness

---

### Counting Reported Reactions

The tool uses Python's `Counter` class to count how frequently each reaction appears.

Example:

Input:

```text
Report 1:
Headache
Nausea

Report 2:
Nausea

Report 3:
Headache
Vomiting
```

Counting:

```text
Headache → 2

Nausea → 2

Vomiting → 1
```

The tool returns:

```python
{
    "Headache": 2,
    "Nausea": 2,
    "Vomiting": 1
}
```

Only the most common reactions are returned to reduce unnecessary information passed to the language model.

---





    



