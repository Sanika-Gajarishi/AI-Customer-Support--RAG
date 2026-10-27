# 🛍️ ShopEase AI Customer Support — RAG-Based Support System

ShopEase AI Customer Support is a full-stack AI-powered customer-support application for a fictional e-commerce store. It combines **Retrieval-Augmented Generation (RAG), Large Language Models (LLMs), and the Model Context Protocol (MCP)** to answer customer questions, retrieve order information, and manage support tickets.

The application uses a **FastAPI backend**, a **Streamlit frontend**, **PostgreSQL** for persistent application data, and **FAISS** for semantic search across customer-support policies. Google Gemini powers AI responses and determines when the agent should use available tools.

The MCP integration allows the AI agent to interact with the existing application services through structured tools for knowledge-base search, authenticated order lookup, and confirmation-protected support-ticket creation.

The project demonstrates how RAG, LLMs, MCP, semantic search, API development, authentication, database management, and agentic workflows can work together to build a practical AI customer-support system.

---

## 📌 Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [How the MCP Integration Works](#-how-the-mcp-integration-works)
- [Available MCP Tools](#-available-mcp-tools)
- [How RAG Works](#-how-rag-works)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Setup on Windows](#-setup-on-windows)
- [Environment Configuration](#-environment-configuration)
- [Database and Migrations](#-database-and-migrations)
- [Running the Application](#-running-the-application)
- [Using the Application](#-using-the-application)
- [API Overview](#-api-overview)
- [Testing](#-testing)
- [Knowledge-Base Management](#-knowledge-base-management)
- [Security and Reliability](#-security-and-reliability)
- [Known Limitations and Troubleshooting](#-known-limitations-and-troubleshooting)
- [Future Improvements](#-future-improvements)
- [Author](#-author)
- [License](#-license)

---

## ✨ Features

### 👤 Customer Experience

- Register an account and log in using an email address and password.
- Authenticate API requests using JWT bearer access tokens.
- Ask customer-support questions through a conversational Streamlit interface.
- Receive answers grounded in relevant ShopEase policy documents.
- View the source documents associated with supported answers.
- Maintain conversations and access persisted conversation history.
- Submit feedback on assistant messages.
- Create support tickets through the ticket API or the confirmation-protected conversational workflow.
- View personal support tickets and their statuses.
- Ask the AI agent to retrieve the status of an order associated with the authenticated account.

### 🤖 AI and RAG Capabilities

- Retrieval-Augmented Generation using existing policy documents.
- Semantic search using Sentence Transformers and FAISS.
- Gemini-powered natural-language responses.
- Retrieval relevance threshold to help reject unrelated questions.
- Source-aware responses based on retrieved policy passages.
- Cached embedding-model and vector-store initialization.
- Policy document ingestion and FAISS index rebuilding.
- MCP tools that let the AI agent access existing application services.

### 🔌 MCP and Agentic AI

- Official Python MCP SDK integration.
- MCP client communication with a dedicated MCP server using standard input/output (stdio) transport.
- Gemini function calling for supported customer-support tools.
- MCP knowledge-base search using the existing RAG retrieval service.
- Authenticated order-status lookup.
- Server-side order ownership verification.
- Support-ticket creation through a persistent confirmation workflow.
- Confirmation codes bound to the authenticated customer and conversation.
- Expiration and single-use validation of ticket confirmations.
- Replay protection against repeated ticket-creation requests.

### 🎫 Support-Ticket Management

- Create tickets with a subject, description, and priority.
- Associate tickets with conversations when applicable.
- Generate unique ticket numbers.
- Track ticket status and assigned administrator.
- Store pending ticket confirmations in PostgreSQL.
- Create a ticket only after a valid confirmation is consumed.
- Reject expired, invalid, reused, or incorrectly associated confirmation codes.

### 🛠️ Administrator Experience

- Role-restricted administration endpoints and dashboard.
- View system usage summaries covering users, conversations, messages, and feedback.
- Upload, list, and delete supported PDF/TXT policy documents.
- Validate file extensions, size, basic PDF signatures, UTF-8 text content, and filenames.
- Rebuild the FAISS knowledge-base index after document changes.
- View tickets with status and priority filters.
- Update ticket status, priority, and administrator assignment.
- Enforce administrative authorization on the backend independently of the frontend.

---

## 🏗️ Architecture

The system combines a traditional application backend with an MCP-based AI agent.

```text
                 Customer / Administrator
                           |
                           v
                   Streamlit Frontend
                    frontend/app.py
                           |
                           | HTTP + JWT
                           v
                     FastAPI Backend
                    backend/app/main.py
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
   Authentication     Chat / History    Ticket APIs
   and Authorization  and Feedback      and Admin APIs
          |                |                |
          |                v                |
          |         Agent Service           |
          |       agent_service.py          |
          |                |                |
          |                v                |
          |         Google Gemini           |
          |       LLM + Function Calls      |
          |                |                |
          |                v                |
          |           MCP Client             |
          |                |                |
          |         stdio communication     |
          |                |                |
          |                v                |
          |           MCP Server             |
          |          mcp_server.py           |
          |                |                |
          |       +--------+---------+       |
          |       |        |         |       |
          |       v        v         v       |
          |     Search   Order     Ticket    |
          |     Tool     Tool      Tool      |
          |       |        |         |       |
          |       v        v         v       |
          |      RAG    Order      Ticket    |
          |    Service  Service    Services   |
          |       |        |         |       |
          +-------+--------+---------+-------+
                           |
                           v
                     PostgreSQL
                 Users, Orders, Tickets,
                 Confirmations, Messages
                           
       RAG Knowledge Base
              |
              +--> PDF/TXT policy documents
              +--> Text extraction and chunking
              +--> Sentence Transformer embeddings
              +--> FAISS vector index
```

### Architectural responsibilities

**Streamlit frontend:** Provides the customer and administrator interfaces. It sends HTTP requests to FastAPI and displays responses.

**FastAPI backend:** Handles authentication, authorization, conversations, feedback, tickets, and administrative operations.

**Gemini agent:** Understands customer questions, generates natural-language responses, and selects supported tools when needed.

**MCP client:** Connects the agent service to the MCP server using the Python MCP SDK.

**MCP server:** Exposes tools through a standard interface, allowing the agent to call existing Python services without duplicating their business logic.

**RAG service:** Retrieves relevant passages from the FAISS vector store.

**PostgreSQL:** Persists users, conversations, messages, feedback, orders, support tickets, and pending ticket confirmations.

---

## 🔌 How the MCP Integration Works

MCP stands for **Model Context Protocol**. It provides a standard way for AI applications to discover and invoke tools exposed by a server.

In this project, MCP connects the Gemini-powered agent to existing ShopEase application functionality.

### Request flow

1. A customer submits a question through Streamlit.
2. Streamlit sends the message to the authenticated FastAPI `/api/chat` endpoint.
3. FastAPI identifies the authenticated customer and loads the relevant conversation context.
4. The agent service sends the question to Gemini, along with the tools available for the current interaction.
5. Gemini may request a tool call, such as searching the policy knowledge base or checking an order.
6. The MCP client invokes the corresponding tool on the MCP server.
7. The MCP server calls the existing Python service and obtains its result.
8. The result is returned to the agent, which generates a customer-friendly answer.
9. FastAPI persists the conversation and returns the response to Streamlit.

Tool selection is controlled by the agent, while business rules and data-access checks remain in the Python services.

### MCP implementation files

| File | Responsibility |
|---|---|
| `backend/app/mcp_server.py` | Defines and exposes MCP tools |
| `backend/app/services/agent_service.py` | Coordinates Gemini, MCP communication, tool calls, and ticket confirmations |
| `backend/app/services/rag_service.py` | Searches the existing RAG knowledge base |
| `backend/app/services/order_service.py` | Retrieves order details and checks customer ownership |
| `backend/app/services/ticket_service.py` | Provides reusable support-ticket creation logic |
| `backend/app/services/ticket_confirmation_service.py` | Creates and consumes persistent ticket confirmations |
| `backend/app/api/chat.py` | Connects the chat endpoint to the MCP-enabled agent |

The MCP server runs as a separate Python subprocess launched by the backend's MCP client. The server receives authenticated customer and conversation context from trusted application code rather than relying on values supplied by Gemini.

---

## 🧰 Available MCP Tools

The MCP server exposes three tools for the customer-support workflow.

### 1. `search_knowledge_base`

Searches the existing FAISS knowledge base for passages relevant to a customer-support question.

**Input:**

- `query`: The text to search for.

**Output:**

- Retrieved passages.
- Source document names.
- Retrieval distances.
- A flag indicating whether relevant content was found.

The MCP tool reuses the existing retrieval function rather than implementing a second vector-search pipeline. Gemini can use the retrieved evidence to prepare an answer.

Example question:

> Can I return a product after 20 days?

The tool searches relevant policy passages and returns the results to the agent.

### 2. `get_order_status`

Retrieves an order's status and available shipping details.

**Input:**

- `order_number`: The order identifier supplied by the customer.

**Potential output fields:**

- Order number.
- Current status.
- Shipping carrier.
- Tracking number.
- Estimated delivery date.

The tool receives the authenticated customer ID through trusted server-side context. The order service checks the order number and customer ID together, preventing customers from accessing another customer's order information.

Example question:

> Where is my order? My order number is ORD-TEST-C9507DB3.

The example number above was used as a local development test order; it is not a real shipment. For a valid order belonging to the authenticated customer, the tool can return its stored details.

If the order is not found or does not belong to the customer, the service must not expose another customer's tracking information.

### 3. `create_support_ticket`

Creates a support ticket through a confirmation-protected workflow.

Unlike an ordinary search, creating a ticket changes application data. The workflow therefore requires explicit customer confirmation.

**Workflow:**

1. The agent recognizes an explicit ticket-creation request.
2. The application prepares a ticket draft with a subject, description, and priority.
3. A pending confirmation code is stored in PostgreSQL.
4. The confirmation is associated with the authenticated user and conversation and receives an expiration time.
5. The customer explicitly confirms the proposed ticket.
6. The application validates and consumes the confirmation through the MCP ticket tool.
7. The ticket is created and associated with the conversation when applicable.
8. The confirmation is marked as consumed so it cannot be used again.

The confirmation workflow is designed to reject invalid, expired, reused, or incorrectly associated confirmation codes.

This separation keeps the ticket-creation decision within trusted application code instead of allowing an unconfirmed model-generated tool call to create a ticket directly.

---

## 🔍 How RAG Works

Retrieval-Augmented Generation combines document retrieval with language-model generation.

The ShopEase knowledge-base workflow is:

1. **Prepare documents:** Policy documents are stored in `backend/data/documents/` or uploaded through the administrator interface.
2. **Extract text:** The ingestion service extracts text from supported PDF and TXT files.
3. **Split text into chunks:** The extracted content is divided into smaller overlapping passages.
4. **Create embeddings:** The `sentence-transformers/all-MiniLM-L6-v2` model converts passages into vectors.
5. **Build the FAISS index:** FAISS stores the vector index and associated document information.
6. **Retrieve passages:** The RAG service searches for the most relevant passages for a new question.
7. **Apply the relevance threshold:** The retrieval logic can reject results that exceed the configured distance threshold.
8. **Generate an answer:** Relevant evidence is passed to the configured Gemini model or returned to the MCP agent for use in its response.
9. **Return sources:** The API returns source information when available.
10. **Persist the conversation:** The application stores messages and conversation metadata in PostgreSQL.

The existing retrieval service uses a top-\(k\) value of 3 and a distance threshold of 1.5 for new questions. These are configuration choices for this project, not universal semantic-search standards.

### Retrieval evaluation

The project's previous retrieval evaluation reported:

| Metric | Result |
|---|---:|
| Hit Rate@3 | 100% |
| Mean Reciprocal Rank (MRR) | 0.917 |

These metrics represent the evaluation set used during development. They do not guarantee that every customer question will receive a correct or complete answer.

---

## 🛠️ Technology Stack

| Area | Technologies |
|---|---|
| Programming language | Python 3.10 |
| Frontend | Streamlit |
| Backend API | FastAPI, Uvicorn |
| LLM | Google Gemini using the Google Gen AI SDK |
| AI tool calling | Gemini function calling |
| Tool integration | Official Python MCP SDK |
| MCP transport | Standard input/output (stdio) |
| RAG | LangChain components |
| Embeddings | Sentence Transformers, Hugging Face |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector search | FAISS CPU |
| Document processing | PyMuPDF and UTF-8 TXT documents |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Schema migrations | Alembic |
| Authentication | JWT access tokens |
| Password hashing | Argon2 through `pwdlib` |
| Validation | Pydantic |
| HTTP client | Requests |
| Testing | pytest and FastAPI testing utilities |
| Configuration | Environment variables and a local `.env` file |

---

## 📁 Project Structure

The principal project files are organized as follows:

```text
RAG-Based Support System/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── history.py
│   │   │   ├── feedback.py
│   │   │   ├── admin.py
│   │   │   └── tickets.py
│   │   │
│   │   ├── services/
│   │   │   ├── agent_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── document_service.py
│   │   │   ├── ingest_service.py
│   │   │   ├── order_service.py
│   │   │   ├── ticket_service.py
│   │   │   └── ticket_confirmation_service.py
│   │   │
│   │   ├── data/
│   │   │   ├── documents/
│   │   │   └── vectorstore/
│   │   │
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── mcp_server.py
│   │   ├── models.py
│   │   └── security.py
│   │
│   ├── tests/
│   │   ├── test_admin_api.py
│   │   ├── test_database.py
│   │   ├── test_documents.py
│   │   ├── test_rag.py
│   │   ├── test_rag_threshold.py
│   │   ├── test_retrieval.py
│   │   ├── test_tickets_api.py
│   │   ├── agent_service_smoke_test.py
│   │   ├── agent_order_status_smoke_test.py
│   │   ├── agent_order_authorization_smoke_test.py
│   │   ├── mcp_client_smoke_test.py
│   │   └── ...
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── app.py
│   └── requirements.txt
│
├── alembic/
│   ├── env.py
│   └── versions/
│
├── alembic.ini
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

The generated vector store is a local artifact and is ignored by Git. The source policy documents should be retained so the vector store can be generated again when needed.

---

## ✅ Prerequisites

Before running the application, make sure you have:

- Windows 10/11 or another supported Python environment.
- Python 3.10; the project was developed with Python 3.10.11.
- PostgreSQL installed and running.
- A Google Gemini API key with access to the configured model.
- Git, if cloning the repository.
- An internet connection for downloading Python packages and the Hugging Face embedding model during initial setup.

The initial installation and embedding-model download may take some time because the project uses machine-learning dependencies.

---

## 🚀 Setup on Windows

### 1. Clone the repository

Clone the GitHub repository and enter the project directory.

```powershell
git clone https://github.com/Sanika-Gajarishi/AI-Customer-Support-Agent--RAG.git
cd AI-Customer-Support-Agent--RAG
```

If the repository has been renamed, use the current clone URL shown on its GitHub page.

If you already have the project on your machine, open PowerShell in the existing repository root instead.

### 2. Create and activate a virtual environment

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip --version
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The project uses packages for API development, RAG, Gemini, MCP, PostgreSQL, and the frontend.

If dependency installation fails, review the first package installation error before changing versions in the requirements file.

### 4. Configure environment variables

Create a local `.env` file in the project root. The file must contain your own database connection details, Gemini API key, and JWT signing secret.

Example:

```dotenv
# PostgreSQL connection
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/shopease_support

# Google Gemini API key
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# JWT signing secret
JWT_SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
```

Replace all placeholder values before running the application.

Do not upload your actual `.env` file to GitHub or expose its contents in logs or screenshots. Keep environment-variable names consistent with the current application configuration.

### 5. Create the PostgreSQL database

Create a PostgreSQL database named `shopease_support`, or choose another name and update `DATABASE_URL` accordingly.

Make sure that the database host, port, username, password, and database name match your configuration.

Use a dedicated development database and avoid using production customer data during testing.

### 6. Configure the Python import path

From the repository root:

```powershell
$env:PYTHONPATH = "$PWD\backend"
```

This allows the backend's `app` package to be imported by the application and the command-line tools in the current PowerShell session.

---

## 🗄️ Database and Migrations

The application uses SQLAlchemy models with Alembic migrations to manage the PostgreSQL schema.

The database contains application entities such as:

- Users and roles.
- Conversations and messages.
- Feedback.
- Support tickets.
- Orders.
- Pending ticket confirmations.

### Check the current migration revision

Run from the project root:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
```

### Apply pending migrations

```powershell
python -m alembic upgrade head
```

### Review migration history

```powershell
python -m alembic history
```

The migrations should be applied to the intended database before exercising features that depend on the new tables.

**Important:** Verify `DATABASE_URL` before applying migrations. Back up databases containing valuable data before schema changes. Do not reset a database simply to resolve a migration error.

---

## ▶️ Running the Application

Use two separate PowerShell terminals from the repository root.

### Terminal 1 — FastAPI backend

Activate the virtual environment and configure the import path:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
```

Start FastAPI:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

The development API is available at:

- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- Alternative API documentation: http://127.0.0.1:8000/redoc

A successful health check returns:

```json
{
  "status": "ok"
}
```

### Terminal 2 — Streamlit frontend

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start the UI:

```powershell
python -m streamlit run frontend/app.py
```

Open the URL printed by Streamlit, usually:

http://localhost:8501

The frontend communicates with the FastAPI backend using the configured `API_BASE_URL`. During local development, its default is `http://127.0.0.1:8000`.

### First-time knowledge-base setup

The generated FAISS index is ignored by Git and may not exist after cloning the repository.

Before testing RAG queries in a fresh environment, make sure the source policy documents are present and build the knowledge-base index using the application's ingestion or administrator rebuild workflow.

---

## 💬 Using the Application

### Customer-support questions

After logging in, ask questions such as:

- Can I return a product after 20 days?
- How long does a refund take?
- What are the shipping options?
- Can I cancel my order?
- Is my product covered by warranty?

For questions covered by the policy documents, the agent can search the knowledge base and generate an answer using retrieved evidence.

### Order tracking

Provide an order number associated with the authenticated account.

Example:

```text
Where is my order? My order number is ORD-TEST-C9507DB3.
```

The order number above was used for local testing. It is a test record, not a real shipment, and should not be presented as a real customer order.

The order-status tool checks the supplied order number against the authenticated user's ID before returning order information.

### Creating a support ticket through the agent

A customer can ask the AI to create a support ticket for an issue such as a damaged product.

The system prepares a draft, requests explicit confirmation, and creates the ticket only after the application's confirmation checks succeed.

The confirmation is associated with a customer and conversation, expires after a limited period, and cannot be reused after successful consumption.

### Viewing and managing tickets

Customers can view their own tickets and statuses through the customer interface.

Administrators can review tickets and update their status, priority, or assignment through the administrative interface, subject to backend authorization.

---

## 📡 API Overview

The interactive API documentation at `/docs` is the authoritative reference for the request and response schemas of the running application.

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/health` | Check backend health | Public |
| POST | `/api/auth/register` | Register a customer | Public |
| POST | `/api/auth/login` | Authenticate and obtain an access token | Public |
| GET | `/api/auth/me` | Retrieve the current user's profile | Authenticated |
| POST | `/api/chat` | Submit a question or continue a conversation | Authenticated |
| GET | `/api/history/{conversation_id}` | Retrieve conversation history | Authenticated; ownership checked |
| POST | `/api/feedback` | Submit message feedback | Authenticated; ownership checked |
| GET | `/api/admin/summary` | Retrieve system usage and feedback summaries | Admin |
| GET | `/api/admin/documents` | List policy documents | Admin |
| POST | `/api/admin/documents/upload` | Upload a supported policy document | Admin |
| DELETE | `/api/admin/documents/{filename}` | Delete a policy document | Admin |
| POST | `/api/admin/rebuild-knowledge-base` | Rebuild the FAISS index | Admin |
| POST | `/api/tickets` | Create a support ticket through the ticket API | Authenticated |
| GET | `/api/tickets` | List the current user's tickets | Authenticated |
| GET | `/api/tickets/{ticket_number}` | Retrieve one of the current user's tickets | Authenticated; ownership checked |
| GET | `/api/tickets/admin/all` | List or filter all tickets | Admin |
| PATCH | `/api/tickets/admin/{ticket_number}` | Update ticket status, priority, or assignment | Admin |

Protected endpoints use the standard bearer-token header:

```http
Authorization: Bearer <access_token>
```

The MCP tools are internal agent integrations rather than public HTTP endpoints. The customer uses the chat endpoint, and the backend's agent service communicates with the MCP server.

Ticket statuses supported by the API include `open`, `in_progress`, `resolved`, and `closed`. Priorities include `low`, `medium`, and `high`.

---

## 🧪 Testing

Run the automated test suite from the project root:

```powershell
python -m pytest backend\tests -q
```

The latest reported regression-test run during development was:

```text
41 passed, 1 warning
```

This result describes that specific run. Execute the test suite again after changing application code, dependencies, database models, or configuration.

The warning reported during development concerned the deprecation of the `langchain-community` FAISS integration. It did not cause the tests to fail.

### Useful validation commands

Check installed dependencies:

```powershell
python -m pip check
```

Inspect the current migration revision:

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
```

### MCP and agent testing

The test directory includes checks and smoke tests for MCP client communication, the agent service, order lookup, order authorization, and persistent ticket confirmations.

Tests that invoke Gemini may consume API quota. Tests that interact with PostgreSQL must use the intended development or test database.

Review any smoke-test script before executing it independently, particularly if it creates database records or consumes external API resources.

### Important testing scenarios

1. Search the knowledge base for a supported policy question.
2. Ask an unrelated question and verify that the application does not invent policy evidence.
3. Request the status of an order belonging to the authenticated customer.
4. Attempt to access an order belonging to another customer and verify that its details are not disclosed.
5. Request support-ticket creation and verify that no ticket is created before confirmation.
6. Confirm the ticket and verify that it is created and linked to the correct conversation.
7. Replay the same confirmation and verify that a duplicate ticket is not created.
8. Verify that customers cannot view or modify another customer's protected records.

---

## 📚 Knowledge-Base Management

Policy documents are stored under:

```text
backend/data/documents/
```

The project supports PDF and UTF-8 TXT policy documents.

### Recommended update workflow

1. Review the policy document before adding it.
2. Upload it through the administrator dashboard or place it in the configured document directory.
3. Rebuild the knowledge-base index after document changes.
4. Ask known questions and verify that the expected source passages are retrieved.
5. Check that out-of-scope queries do not receive unsupported policy answers.

Uploading or deleting a document does not automatically rebuild the index. Use the explicit rebuild workflow.

### FAISS files

The generated vector store is stored under:

```text
backend/data/vectorstore/
├── index.faiss
└── index.pkl
```

These are generated local artifacts and are excluded from Git. A fresh setup must regenerate them from the available source documents before relying on RAG retrieval.

The `index.pkl` file uses Python serialization. Only load vector-store artifacts generated from trusted sources; do not replace them with untrusted files.

---

## 🔐 Security and Reliability

- Keep `.env`, Gemini API keys, database credentials, JWT secrets, and private customer data out of version control.
- Use a strong, unique JWT signing secret for each environment.
- Keep authentication and authorization checks in the backend; hiding a UI control is not sufficient.
- Enforce record ownership on order, conversation, ticket, and feedback access.
- Derive authenticated customer context from trusted server-side authentication, not model-generated arguments.
- Require explicit confirmation for ticket creation and reject expired or replayed confirmations.
- Use least-privilege PostgreSQL credentials rather than a database superuser for normal application execution.
- Protect administrator routes with server-side role checks.
- Review uploaded documents before indexing them.
- Treat retrieved text as evidence, not executable instructions. RAG does not make prompt injection or malicious content impossible.
- Do not expose internal errors, secrets, or sensitive customer records in user-facing responses.
- Back up PostgreSQL data before running migrations or maintenance tasks.
- Use appropriate HTTPS, logging, monitoring, rate limiting, and secret management before exposing the application to public traffic.
- Keep test data separate from real customer data.

---

## ⚠️ Known Limitations and Troubleshooting

### 1. Gemini quota exceeded

An API request may fail with `429 RESOURCE_EXHAUSTED` when the configured Gemini project or model has exhausted its quota.

Check the project's Gemini API usage, model availability, rate limits, and billing configuration. Generating another API key within the same project does not necessarily resolve a project-level quota limit.

### 2. PostgreSQL connection failure

Verify:

- PostgreSQL is running.
- The database exists.
- `DATABASE_URL` contains the correct host, port, database name, username, and password.
- The database user has the required permissions.
- Pending migrations have been applied.

### 3. FAISS index not found

If the application reports that `index.faiss` is missing, verify that the source policy documents exist and rebuild the knowledge base before testing retrieval.

### 4. Hugging Face model download problems

The embedding model is downloaded from Hugging Face when needed. An initial request can fail because of network connectivity or download restrictions.

Check network access and retry the operation after resolving the underlying download problem.

### 5. MCP tool invocation failure

Verify that:

- The backend dependencies include the official Python MCP SDK.
- The MCP server module is available in the backend Python path.
- The MCP client is launching the server with the correct working directory.
- The MCP server can access the configured database and RAG files.
- The authenticated user and conversation context are passed through trusted application code.
- Gemini has remaining quota when the test requires a model-generated tool call.

A failed Gemini API request does not by itself prove that the MCP server or its tools are broken. Test MCP server communication separately when diagnosing agent failures.

### 6. Ticket confirmation rejected

An invalid, expired, reused, or incorrectly associated confirmation code should be rejected. Start a new ticket-confirmation workflow and confirm it within the allowed time using the same authenticated user and conversation.

---

## 🚀 Future Improvements

Potential future improvements include:

- Expanded automated evaluation of retrieval quality and answer faithfulness.
- More robust observability for tool calls, retrieval results, and model errors.
- More extensive API-level tests for order lookup and confirmation workflows.
- Improved handling of model quota exhaustion and other external-service failures.
- Additional order-management tools where appropriate.
- Improved support for multilingual customer questions.
- More extensive performance testing and production monitoring.
- Dependency maintenance as upstream libraries evolve.

These are possible improvements, not claims that the features have already been implemented.

---

## 👩‍💻 Author

**Sanika Gajarishi**

GitHub: [Sanika-Gajarishi](https://github.com/Sanika-Gajarishi)

---

## 📄 License

This project is intended for educational, learning, and demonstration purposes. Add an explicit license file if you intend to grant others permission to use, modify, and distribute the project.
