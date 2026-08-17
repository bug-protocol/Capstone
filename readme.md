# Capstone: Drug Safety & Medical Information Service

Capstone is an enterprise-grade drug-safety and pharmacovigilance assistant built using the **Strands Agents SDK**, deployed on **Amazon Bedrock AgentCore Runtime**, and served through a full-featured **FastAPI backend** with real authentication, database persistence, streaming chat, structured adverse-event intake, and OpenTelemetry observability.

---

## 1. System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Backend                                  │
│  - JWT Auth (/auth/signup, /auth/login, /auth/refresh)                          │
│  - SSE Streaming Chat (/chat) & Session Turn History                            │
│  - Non-Conversational AE Intake (/intake) & Review Queue (/cases)               │
│  - PII Redaction & OpenTelemetry Observability Instrumentation                  │
│  - PostgreSQL Persistence (Users, Sessions, Messages, Cases)           │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                   Amazon Bedrock AgentCore Runtime Container                    │
│   ARN: arn:aws:bedrock-agentcore:ap-south-1:025066239748:runtime/Capstone_Agent │
│                                                                                 │
│                        ┌──────────────────────────┐                             │
│                        │     Supervisor Agent     │                             │
│                        │ (Routing, Guardrails, LTM)│                             │
│                        └─────────────┬────────────┘                             │
│               ┌──────────────────────┼──────────────────────┐                   │
│               ▼                      ▼                      ▼                   │
│        ┌──────────────┐       ┌──────────────┐       ┌──────────────┐           │
│        │  LabelAgent  │       │ SafetyAgent  │       │ TrialsAgent  │           │
│        └──────┬───────┘       └──────┬───────┘       └──────┬───────┘           │
│               │                      │                      │                   │
└───────────────┼──────────────────────┼──────────────────────┼───────────────────┘
                │                      │                      │
                ▼                      ▼                      ▼
    ┌──────────────────────┐  ┌────────────────────────────────────────┐
    │  openFDA Drug Label  │  │        AgentCore Gateway (MCP)         │
    │         API          │  │  - openFDA Drug Event Tool             │
    │  (Approved Labeling) │  │  - ClinicalTrials.gov v2 Tool          │
    └──────────────────────┘  └────────────────────────────────────────┘
```

---

## 2. Multi-Agent Team (Agents-as-Tools Pattern)

| Agent | Responsibility | Primary Tool & Data Source |
| :--- | :--- | :--- |
| **Supervisor** | Intent routing, refusal policy enforcement, LTM user profile context, escalation to human | Specialist agents as tools, `escalate_to_human` |
| **LabelAgent** | Answers factual product questions strictly from approved drug labels with citations | openFDA Drug Label API (`search_drug_label`) |
| **SafetyAgent** | Summarizes reported adverse-event frequencies with mandatory causality caveats | AgentCore Gateway MCP (`gateway_search_adverse_events`) / openFDA Drug Event API |
| **TrialsAgent** | Finds matching active and completed clinical trials | AgentCore Gateway MCP (`gateway_search_clinical_trials`) / ClinicalTrials.gov v2 |
| **IntakeAgent** | Non-conversational extraction of structured `AdverseEventCase` from free-text narratives | Strands Pydantic structured output model |

---

## 3. Memory Architecture: STM vs LTM

| Memory Dimension | Implementation | Stored Data | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Short-Term Memory (STM)** | `FileSessionManager` / `AgentCoreMemorySessionManager` (`data/sessions/`) | In-session conversational turns, follow-up context | **Ephemeral Dialogue Context**: Multi-turn clarifications (e.g. *"What are its contraindications?"* after asking about Ozempic) are transient and should not leak into unrelated sessions. |
| **Long-Term Memory (LTM)** | `LongTermMemoryStore` (`data/ltm_store.json`) | Permanent user profile: drug allergies (e.g. *Macrolides, Penicillin*), chronic conditions (*Type 2 Diabetes*), clinical profile | **Permanent Clinical Safety**: Critical patient allergy and health profiles must persist across months and multiple sessions so the agent continuously guards against contraindicated drug recommendations. |

---

## 4. AgentCore Gateway & MCP Integration

Tools are decoupled from in-process execution and exposed as standardized **Model Context Protocol (MCP)** targets via `tools/mcp_server.py` and `tools/gateway.py`:
- **Centralized Governance**: Rate limiting, API key rotation, and audit logs are managed at the Gateway layer.
- **Enterprise MCP Standards**: Uses `FastMCP` to serve `search_adverse_events_mcp` and `search_clinical_trials_mcp`.

---

## 5. Production Guardrails & Safety Policies

1. **Clinical Advice Refusal**:
   - Dosing, diagnosis, or personalized treatment queries trigger immediate refusal and redirection via `escalate_to_human`.
2. **Citation or Silence**:
   - Every factual drug label statement includes the source name and section citation.
3. **Signal ≠ Causality**:
   - Every adverse event statistical output explicitly notes: *"Reported adverse-event frequencies are based on spontaneous reports and do not establish causality."*
4. **Pre-Trace PII Redaction**:
   - Free-text narratives are sanitized of names, phone numbers, emails, SSNs, DOBs, and MRNs before emitting logs, traces, or database records.

---

## 6. FastAPI Backend API Reference

### Authentication
* `POST /auth/signup`: Register user with email, username, password, and optional full_name.
* `POST /auth/login`: Authenticate and receive JWT access token (60 min) + refresh token (7 days).
* `POST /auth/refresh`: Exchange refresh token for a fresh access token.
* `GET /auth/me`: Retrieve authenticated user profile (JWT protected).

### Consultation & Streaming Chat
* `POST /chat`: Call the supervisor agent. Supports Server-Sent Events (`stream: true`) or standard JSON (`stream: false`).
* `GET /chat/sessions`: List all consultation sessions for the logged-in user.
* `GET /chat/sessions/{session_id}`: Retrieve turn history for a session.

### Adverse Event Intake & Review Queue
* `POST /intake`: Submit free-text narrative, redact PII, extract structured `AdverseEventCase`, and persist to triage queue.
* `GET /cases`: Query triage review queue with status and drug filters.
* `GET /cases/{id}`: Retrieve detailed case record.
* `PATCH /cases/{id}`: Update review status (`PENDING_REVIEW`, `TRIAGED`, `ESCALATED`, `RESOLVED`) and reviewer notes.

### System & Health
* `GET /health` & `GET /ping`: Service health status, AgentCore ARN, and database status.

---

## 7. Quickstart & Verification

### 1. Install Dependencies
```bash
pip install -r requirements.txt
pip install fastapi uvicorn pydantic-settings sqlalchemy asyncpg psycopg2-binary pyjwt bcrypt opentelemetry-api opentelemetry-sdk httpx pytest pytest-asyncio tabulate
```

### 2. Run the End-to-End Demo Script
Executes the full test suite (Signup $\to$ Login $\to$ Grounded Label Query $\to$ Safety Signal $\to$ Refusal $\to$ Intake with PII Redaction $\to$ Review Queue $\to$ OpenTelemetry Traces):
```bash
python scripts/e2e_trace_demo.py
```

### 3. Run Automated Tests
```bash
pytest tests/test_backend.py -v
```

### 4. Start the FastAPI Backend Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger API documentation available at: `http://localhost:8000/docs`
