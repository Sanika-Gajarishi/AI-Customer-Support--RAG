## 🛍️ ShopEase AI Customer Support — RAG-Based Support System

The **AI Customer Support Agent** is a full-stack application designed to help customers of a fictional e-commerce company called ShopEase get quick and accurate answers to their questions about company policies, such as product returns, refunds, and other support-related issues.

The application uses **Retrieval-Augmented Generation (RAG)** to answer questions using information from the company's policy documents instead of relying only on the AI model's general knowledge. First, the system searches its knowledge base for relevant information. It then provides the retrieved information to a Google Gemini model, which generates a natural-language answer based on the available context. This helps the chatbot provide answers that are more relevant to ShopEase's policies.

The system also includes an **administrator dashboard** that allows authorized administrators to monitor usage statistics, upload or remove policy documents, rebuild the FAISS search index when the knowledge base changes, and manage customer support tickets by updating their status and priority.

Overall, this project demonstrates how RAG, large language models, semantic search, API development, database management, authentication, and a user interface can work together to build an AI-powered customer support solution.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [How RAG works](#how-rag-works)
- [Prerequisites](#prerequisites)
- [Setup on Windows](#setup-on-windows)
- [Environment configuration](#environment-configuration)
- [Database and migrations](#database-and-migrations)
- [Running the application](#running-the-application)
- [API overview](#api-overview)
- [Testing](#testing)
- [Knowledge-base management](#knowledge-base-management)
- [Security notes](#security-notes)


## Features

### Customer experience
- Register and log in using an email address and password.
- Authenticated customer sessions using bearer JWT access tokens.
- Ask customer-support questions through a Streamlit chat interface.
- Retrieval-grounded answers from configured policy documents, with source names returned by the API.
- Conversation identifiers and persisted conversation/message history.
- Submit feedback on assistant messages.
- Create support tickets, optionally linked to an existing conversation.
- View the customer's own support tickets and ticket status.

### Administrator experience
- Role-restricted admin dashboard.
- Usage summary including user, conversation, message, and feedback counts.
- View, upload, and delete PDF/TXT policy documents.
- Upload validation for supported extensions, file size, basic PDF signature, UTF-8 TXT content, and unsafe filenames.
- Explicitly rebuild the FAISS knowledge-base index after document changes.
- View tickets with status/priority filters; update status, priority, and administrator assignment.
- Backend authorization checks protect administrative endpoints independently of the UI.

## Architecture

The application is split into a Streamlit frontend and a FastAPI backend.

```text
Customer / Administrator
          |
          v
   Streamlit UI
   frontend/app.py
          |
          | HTTP requests + bearer token
          v
    FastAPI application
    backend/app/main.py
          |
          +--> Authentication and authorization
          +--> Chat / conversation history / feedback
          +--> Support-ticket API
          +--> Admin dashboard API and document management
          |
          +--> SQLAlchemy --> PostgreSQL database
          |
          +--> RAG service
                    |
                    +--> Document extraction (PDF/TXT)
                    +--> Text splitting / chunking
                    +--> Hugging Face sentence embeddings
                    +--> FAISS vector index
                    +--> Gemini model for answer generation
```

## Technology stack

| Area | Technologies |
|---|---|
| Language | Python |
| Frontend | Streamlit |
| API | FastAPI, Uvicorn |
| LLM | Google Gemini via the Google Gen AI / LangChain integration configured by the project |
| RAG orchestration | LangChain components |
| Embeddings | Sentence Transformers / Hugging Face, `sentence-transformers/all-MiniLM-L6-v2` |
| Vector search | FAISS CPU |
| Document parsing | PyMuPDF for PDFs; UTF-8 text documents |
| Database | PostgreSQL, SQLAlchemy |
| Database migrations | Alembic |
| Authentication | JWT access tokens, Argon2 password hashing via `pwdlib` |
| Validation | Pydantic |
| Tests | pytest, FastAPI TestClient |
| Configuration | environment variables in a local `.env` file |

## Project structure

The principal files and directories are:

```text
RAG-Based Support System/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py             # Register, login, current-user profile
│   │   │   ├── chat.py             # Authenticated chat endpoint
│   │   │   ├── history.py          # Conversation history
│   │   │   ├── feedback.py         # Message feedback
│   │   │   ├── admin.py            # Admin summary and document management
│   │   │   └── tickets.py          # Customer/admin ticket operations
│   │   ├── services/
│   │   │   ├── rag_service.py      # Retrieval + answer generation
│   │   │   ├── ingest_service.py   # Document ingestion / FAISS rebuild
│   │   │   ├── embedding_service.py# Embeddings and vector-store access
│   │   │   └── document_service.py # Document processing helpers
│   │   ├── data/
│   │   │   ├── documents/          # Source TXT/PDF policy documents
│   │   │   └── vectorstore/        # Generated FAISS index (not committed)
│   │   ├── database.py             # SQLAlchemy engine and session setup
│   │   ├── models.py               # ORM models
│   │   ├── security.py             # Password/JWT and role dependencies
│   │   └── main.py                 # FastAPI app and route registration
│   └── tests/
│       ├── test_admin_api.py
│       ├── test_database.py
│       ├── test_documents.py
│       ├── test_rag.py
│       ├── test_rag_threshold.py
│       ├── test_retrieval.py
│       └── test_tickets_api.py
├── frontend/
│   └── app.py                      # Streamlit customer/admin interface
├── alembic/
│   ├── env.py
│   └── versions/                   # Database migration revisions
├── alembic.ini
├── requirements.txt
├── .env                            # Local secrets; do not commit
├── .env.example                    # Create from the template below
├── .gitignore
└── README.md
```

Some developer utilities may also live in `backend/tests/`. Use them only after reviewing their purpose and any effect they may have on your local database or documents.

## How RAG works

1. **Prepare documents:** The administrator places relevant support policies in the document directory, or uploads PDF/TXT documents through the admin interface.
2. **Extract text:** The ingestion workflow extracts readable content from supported source documents.
3. **Split into chunks:** Text is broken into smaller overlapping sections to improve retrieval of relevant passages.
4. **Create embeddings:** A Sentence Transformers embedding model represents the chunks as vectors.
5. **Build FAISS index:** The vectors and associated document data are stored in a local FAISS vector store.
6. **Retrieve context:** For an incoming customer question, the RAG service searches for relevant chunks.
7. **Generate an answer:** The retrieved context is passed to the configured Gemini model to generate a response.
8. **Return and persist:** The API returns the answer, source information, and conversation identifier, and persists the conversation messages.

The current development evaluation previously reported **Hit Rate@3 = 100%** and **Mean Reciprocal Rank (MRR) = 0.917** on its evaluation set. These are results for that test set, not a guarantee of accuracy for all customer questions or production traffic.

## Prerequisites

- Windows 10/11 with PowerShell (commands below target Windows).
- Python **3.10** (the project was developed and tested with Python 3.10.11).
- PostgreSQL running locally or accessible at a configured database URL.
- A Google Gemini API key with access to the model configured in the project.
- Git, if cloning the repository.

The embedding model may download from Hugging Face on first use, and the first ingestion run can take longer while the model and index are initialized.

## Setup on Windows

### 1. Clone and enter the project

```powershell
git clone https://github.com/Sanika-Gajarishi/AI-Customer-Support--RAG.git
cd AI-Customer-Support--RAG
```

If you already have the project locally, open PowerShell in the project root instead.

### 2. Create and activate a virtual environment

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation because of its execution policy, you can invoke the environment's Python directly as `\.venv\Scripts\python.exe` instead of changing system-wide policy.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Use the project's actual variable names and your own local values. **Never commit the real `.env` file or paste secret values into issues or public documentation.**

A starter template is provided below. Check `backend/app/database.py` and `backend/app/security.py` if your local version uses different variable names.

```dotenv
# PostgreSQL connection string (adjust credentials/host/database to your environment)
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/shopease_support

# Google Gemini API key
GEMINI_API_KEY=replace_with_your_gemini_api_key

# Strong, random secret used to sign JWT access tokens
JWT_SECRET_KEY=replace_with_a_long_random_secret

# Optional settings, only if read by your current application
# JWT_ALGORITHM=HS256
# JWT_EXPIRE_MINUTES=30
```

The names of optional variables must match those actually read by your application. The values above are placeholders, not working credentials.

### 5. Create the PostgreSQL database

Create a database for the application in PostgreSQL (for example, `shopease_support`) and make sure the database name, username, password, host, and port match `DATABASE_URL`.

Do not use production customer data for local development or tests.

### 6. Set the backend import path

From the project root, run:

```powershell
$env:PYTHONPATH = "$PWD\backend"
```

This environment variable needs to be set in each new PowerShell session before running backend commands. It is not required for the Streamlit command shown below unless your local frontend code imports backend modules directly.

## Database and migrations

The project uses SQLAlchemy models and Alembic migrations to evolve the schema.

Check the current migration revision:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
```

Apply pending migrations:

```powershell
python -m alembic upgrade head
```

Review migration history:

```powershell
python -m alembic history
```

Run migrations only after verifying that `DATABASE_URL` points to the intended database. Back up data before applying schema changes to any database that contains valuable information.

## Running the application

Use two separate PowerShell terminals from the repository root.

### Terminal 1 — FastAPI backend

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --app-dir backend --reload
```

The default development API address is:

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- Alternative API documentation: http://127.0.0.1:8000/redoc

A healthy backend responds to `GET /health` with:

```json
{"status": "ok"}
```

### Terminal 2 — Streamlit frontend

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/app.py
```

Streamlit prints the local URL (typically http://localhost:8501). Open that address in your browser.

The frontend calls the FastAPI backend. Start the backend first and ensure the frontend's configured API base URL points to the backend address.

## API overview

The interactive OpenAPI schema at `/docs` is the authoritative reference for request/response schemas in the running version.

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/health` | Backend health check | Public |
| POST | `/api/auth/register` | Register a customer | Public |
| POST | `/api/auth/login` | Obtain a bearer access token | Public |
| GET | `/api/auth/me` | Get current user's profile | Authenticated |
| POST | `/api/chat` | Ask a question / continue a conversation | Authenticated |
| GET | `/api/history/{conversation_id}` | Fetch conversation history | Authenticated, owner-only |
| POST | `/api/feedback` | Submit feedback on a message | Authenticated, ownership-checked |
| GET | `/api/admin/summary` | Usage and feedback summary | Admin |
| GET | `/api/admin/documents` | List TXT/PDF policy documents | Admin |
| POST | `/api/admin/documents/upload` | Upload a policy document (max 10 MB) | Admin |
| DELETE | `/api/admin/documents/{filename}` | Delete a policy document | Admin |
| POST | `/api/admin/rebuild-knowledge-base` | Rebuild the FAISS index | Admin |
| POST | `/api/tickets` | Create a support ticket | Authenticated |
| GET | `/api/tickets` | List current user's tickets | Authenticated |
| GET | `/api/tickets/{ticket_number}` | Get one of the current user's tickets | Authenticated, owner-only |
| GET | `/api/tickets/admin/all` | List/filter all tickets | Admin |
| PATCH | `/api/tickets/admin/{ticket_number}` | Update status, priority, or assignee | Admin |

All protected endpoints expect an access token in the standard header:

```http
Authorization: Bearer <access_token>
```

Ticket statuses supported by the API are `open`, `in_progress`, `resolved`, and `closed`. Priorities are `low`, `medium`, and `high`.

## Testing

Run the automated test suite from the repository root:

```powershell
python -m pytest backend\tests -q
```

The most recent reported local run was:

```text
41 passed, 1 warning
```

The warning concerns the project's current LangChain community FAISS import being deprecated. It did not cause the tests to fail. Re-run tests after changing dependencies, RAG behavior, authentication, routes, or database models.

Useful checks:

```powershell
python -m pip check
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
```


## Knowledge-base management

Policy documents should be stored under `backend/data/documents/` and must be in PDF or UTF-8 TXT format.

Recommended workflow after policy content changes:

1. Review the new or changed policy document.
2. Upload it from the administrator dashboard, or place it in the configured document directory.
3. Rebuild the knowledge base from the admin dashboard.
4. Ask a small set of known questions and verify that retrieved sources and answers reflect the updated policy.

Uploading or deleting a document does **not** itself rebuild the index; use the explicit rebuild action. The generated files under `backend/data/vectorstore/` are local artifacts and are ignored by Git. Regenerate them from the source documents on a fresh setup.



## Security notes

- Keep `.env`, API keys, database credentials, JWT secrets, and real customer data out of source control.
- Generate a strong, unique JWT signing secret for each environment.
- Use HTTPS and suitable secret management before exposing the application publicly.
- Run with least-privilege database credentials; do not use a database superuser for a deployed service.
- Keep customer endpoints authenticated and enforce record ownership server-side.
- Administrative APIs use backend role checks; hiding admin UI controls is not a substitute for API authorization.
- Review uploaded documents before indexing them. RAG provides relevant text to a language model but does not make that text inherently trusted.
- Treat generated answers as assistive responses, and provide a route for escalation when policy information is missing or ambiguous.
- Configure production CORS, rate limits, logging, backups, timeouts, and monitoring before public deployment.



# 👩‍💻 Author

**Sanika Gajarishi**

GitHub:

https://github.com/Sanika-Gajarishi


## License

This project is intended for educational and demonstration purposes.
