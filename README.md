## 🛍️ ShopEase AI Customer Support — RAG + MCP
ShopEase is a full-stack AI customer-support application for a fictional e-commerce store. It combines Retrieval-Augmented Generation (RAG) with Model Context Protocol (MCP) tools, a FastAPI backend, a Streamlit interface, and PostgreSQL persistence.

Customers can ask questions about ShopEase policies, continue conversations, submit answer feedback, check their own order status, and create support tickets. Administrators can review usage, manage policy documents, rebuild the knowledge-base index, and manage support tickets.

The project demonstrates how semantic retrieval, an LLM, tool calling through MCP, API development, authentication, database modeling, and a user interface fit together in a practical customer-support workflow.
Contents
- Features
- Architecture
- MCP integration
- Technology stack
- Project structure
- How RAG works
- Prerequisites
- Setup on Windows
- Environment configuration
- Database and migrations
- Running the application
- API overview
- Testing
- Knowledge-base management
- Security and safeguards
- Current limitations
- Author
  
## Features
Customer experience
- Register and log in with an email address and password.
- Authenticated API requests using bearer JWT access tokens.
- Ask ShopEase customer-support questions in a Streamlit chat interface.
- Receive answers grounded in retrieved policy content, with source names returned by the API when available.
- Continue conversations with persisted conversation and message history.
- Submit feedback on assistant answers.
- View the authenticated customer's support tickets and their status.
- Ask for order status through the conversational agent, with the order lookup restricted to the authenticated customer.
- Request a support ticket through the chat flow and explicitly confirm its creation.
  
Administrator experience
- Role-restricted administrator dashboard.
- Usage summary for users, conversations, messages, and feedback.
- List, upload, and delete supported PDF/TXT policy documents.
- Validate uploaded file type, size, basic PDF signature, UTF-8 TXT content, and filenames.
- Rebuild the FAISS knowledge-base index after document changes.
- Filter support tickets by status and priority, and update ticket status, priority, and assignment.
- Enforce administrator permissions in the backend API, independently of the frontend UI.

RAG and agent capabilities
- Semantic retrieval using Sentence Transformers embeddings and a FAISS vector index.
- Gemini-generated answers based on retrieved ShopEase policy passages.
- Retrieval threshold to avoid answering new, out-of-scope questions using weakly relevant policy matches.
- MCP tools for knowledge-base search, customer-specific order lookup, and confirmation-protected ticket creation.
- PostgreSQL persistence for users, conversations, messages, feedback, support tickets, orders, and pending ticket confirmations.

  
## Architecture
The frontend sends customer requests to FastAPI. The chat endpoint passes authenticated context to the Gemini-backed agent. The agent uses the MCP client to invoke tools exposed by the local MCP server. The tools call existing Python services and the RAG index or PostgreSQL database.
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
          +--> Chat, conversation history, and feedback
          +--> Support-ticket and administrator APIs
          |
          +--> Gemini-backed agent
                    |
                    +--> MCP client (stdio)
                              |
                              v
                        MCP server
                        backend/app/mcp_server.py
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       RAG retrieval     Order service    Ticket confirmation
       FAISS index       PostgreSQL       + ticket service
             |                |                |
             +----------------+----------------+
                              |
                              v
                     Results returned to agent
                              |
                              v
                    Answer returned to customer
MCP integration
The project uses the official Python MCP SDK. The MCP server exposes application capabilities as tools, and the agent's MCP client discovers and calls those tools over standard input/output (stdio). The client passes trusted authentication context to the server through its process environment; the LLM does not get to choose the authenticated user ID.
Available MCP tools
Tool	Purpose	Safeguard
search_knowledge_base(query)	Search the existing FAISS policy index and return relevant passages and source names.	Applies the retrieval relevance threshold for new questions.
get_order_status(order_number)	Retrieve an order's status, carrier, tracking number, and estimated delivery when available.	Looks up the order using both the supplied order number and the authenticated customer's user ID.
create_support_ticket(confirmation_code)	Create a support ticket after the customer confirms the proposed ticket.	Consumes a pending, expiring, one-time confirmation tied to the authenticated user and conversation.


Ticket confirmation flow
1. The customer asks the assistant to create a support ticket.
2. The agent prepares a ticket draft and provides a confirmation code. The request does not create a ticket immediately.
3. The customer confirms using the confirmation command shown by the application (for example, CONFIRM TICKET <confirmation_code>).
4. The application validates the confirmation and invokes the MCP ticket tool.
5. The confirmation record is consumed and the ticket is created in a single database transaction.
Pending confirmations expire after 10 minutes and are bound to the authenticated user and conversation. Reusing a code, using another user's code, or confirming from another conversation is rejected. The ticket API also remains available for the separate ticket form.
Order status behavior
The get_order_status tool accepts an order number, not the database's numeric primary key. An order is returned only when it belongs to the authenticated user. Test orders used during development are placeholders and do not represent real shipments.
Technology stack
Area	Technologies
Language	Python 3.10
Frontend	Streamlit
API	FastAPI, Uvicorn
LLM	Google Gemini via the Google Gen AI SDK
Tool integration	Official MCP Python SDK, MCP client/server over stdio
Retrieval orchestration	LangChain components
Embeddings	Sentence Transformers / Hugging Face, sentence-transformers/all-MiniLM-L6-v2
Vector search	FAISS CPU
Document parsing	PyMuPDF for PDFs; UTF-8 text documents
Database	PostgreSQL, SQLAlchemy, Psycopg 3
Database migrations	Alembic
Authentication	JWT access tokens, Argon2 password hashing via pwdlib
Validation	Pydantic
Tests	pytest and FastAPI test utilities
Configuration	Environment variables in a local .env file


Project structure
RAG-Based Support System/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py              # Registration, login, current-user profile
│   │   │   ├── chat.py              # Authenticated chat endpoint and agent integration
│   │   │   ├── history.py           # Conversation history
│   │   │   ├── feedback.py          # Answer feedback
│   │   │   ├── admin.py             # Admin summary and document management
│   │   │   └── tickets.py           # Customer/admin ticket operations
│   │   ├── services/
│   │   │   ├── agent_service.py     # Gemini agent and MCP client orchestration
│   │   │   ├── rag_service.py       # Knowledge retrieval and RAG answer flow
│   │   │   ├── embedding_service.py # Embeddings and FAISS vector-store access
│   │   │   ├── document_service.py  # Document processing helpers
│   │   │   ├── ingest_service.py    # Document ingestion and FAISS rebuild
│   │   │   ├── llm_service.py       # Gemini client and answer generation
│   │   │   ├── order_service.py     # Customer-specific order lookup
│   │   │   ├── ticket_service.py    # Reusable support-ticket creation logic
│   │   │   └── ticket_confirmation_service.py # Persistent one-time confirmation
│   │   ├── data/
│   │   │   ├── documents/           # Source TXT/PDF policy documents
│   │   │   └── vectorstore/         # Local generated FAISS index files
│   │   ├── database.py              # SQLAlchemy engine and sessions
│   │   ├── mcp_server.py            # MCP tool definitions and server
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── security.py              # Password/JWT and role dependencies
│   │   └── main.py                  # FastAPI application and route registration
│   └── tests/                       # API, RAG, MCP, order, and ticket tests
├── frontend/
│   └── app.py                       # Streamlit customer/admin interface
├── alembic/
│   ├── env.py
│   └── versions/                    # Database migration revisions
├── alembic.ini
├── requirements.txt
├── .env.example                     # Placeholder configuration template
├── .gitignore
└── README.md
The generated files under backend/data/vectorstore/ are ignored by Git in the current configuration. On a fresh checkout, make sure the FAISS index exists before querying the knowledge base; if it does not, regenerate it from the source policy documents using the ingestion workflow.
How RAG works
1. Prepare documents: Administrators add policy documents to the configured document directory or upload them through the admin interface.
2. Extract text: The ingestion workflow extracts readable text from supported PDF and TXT documents.
3. Split into chunks: Text is divided into smaller overlapping sections to help retrieve relevant passages.
4. Create embeddings: sentence-transformers/all-MiniLM-L6-v2 converts document chunks into vectors.
5. Build FAISS index: The vectors and metadata are saved in the local vector store.
6. Retrieve context: The RAG service embeds each question and searches for relevant chunks in FAISS.
7. Apply relevance checks: For new questions, low-relevance results can be rejected rather than treated as policy evidence.
8. Generate an answer: Relevant passages are provided to Gemini so the response can be grounded in the retrieved policy context.
9. Return and persist: The API returns the answer and source names where available and persists conversation messages.
The development retrieval evaluation previously reported Hit Rate@3 = 100% and Mean Reciprocal Rank (MRR) = 0.917 on its evaluation set. These metrics describe that test set; they are not a guarantee of accuracy for every question or for production traffic.
Prerequisites
- Windows 10/11 with PowerShell (the commands below target Windows).
- Python 3.10 (the project was developed and tested with Python 3.10.11).
- PostgreSQL running locally or accessible through the configured connection URL.
- A Google Gemini API key with access to the configured model.
- Git, if cloning the repository.
The Sentence Transformers model may download from Hugging Face on first use. Initial model loading and knowledge-base ingestion can take longer than subsequent requests.
Setup on Windows
1. Clone and enter the project
git clone https://github.com/Sanika-Gajarishi/AI-Customer-Support--RAG.git
cd AI-Customer-Support--RAG
If you already have the repository locally, open PowerShell in the project root.
2. Create and activate a virtual environment
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
If PowerShell blocks activation, you can call the virtual environment's Python directly as \.venv\Scripts\python.exe instead of changing a system-wide execution policy.
3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
4. Configure environment variables
Create a local .env file in the repository root. Use your own values and keep the real .env file out of source control.

Typical required settings include:
# Example only — replace with your own local credentials.
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/shopease_support
GEMINI_API_KEY=replace_with_your_gemini_api_key
JWT_SECRET_KEY=replace_with_a_long_random_secret
Use the exact variable names expected by the code in your checkout. Values above are placeholders, not working credentials. Never commit API keys, database passwords, JWT secrets, or customer data.
5. Create the PostgreSQL database
Create a development database (for example, shopease_support) and ensure the name, username, password, host, and port match DATABASE_URL. Use a least-privilege database account and avoid using production customer data for local development or tests.
6. Set the backend import path
From the project root in PowerShell:
$env:PYTHONPATH = "$PWD\backend"
Set this again in each new terminal session before running backend commands.
Database and migrations
The application uses SQLAlchemy models and Alembic migrations. The schema includes user and conversation data, messages, feedback, support tickets, orders, and pending ticket confirmations.

Check the current revision:
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
Apply pending migrations:
python -m alembic upgrade head
Review migration history:
python -m alembic history
Before running migrations, verify that DATABASE_URL points to the intended database. Back up databases that contain valuable data before applying schema changes.
Running the application
Use two separate PowerShell terminals from the project root.
Terminal 1 — FastAPI backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --app-dir backend --reload
Available development endpoints:
- Health check: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs
- Alternative API docs: http://127.0.0.1:8000/redoc
A healthy backend responds to GET /health with:
{"status": "ok"}
Terminal 2 — Streamlit frontend
.\.venv\Scripts\Activate.ps1
python -m streamlit run frontend/app.py
Open the local URL printed by Streamlit (typically http://localhost:8501). The frontend sends API calls to the configured FastAPI base URL; start the backend first.
API overview
The running OpenAPI schema at /docs is the authoritative reference for actual request and response models.
Method	Endpoint	Purpose	Access
GET	/health	Backend health check	Public
POST	/api/auth/register	Register a customer	Public
POST	/api/auth/login	Obtain a bearer access token	Public
GET	/api/auth/me	Get the current user's profile	Authenticated
POST	/api/chat	Ask a question or continue a conversation	Authenticated
GET	/api/history/{conversation_id}	Fetch conversation history	Authenticated; owner-only
POST	/api/feedback	Submit feedback on a message	Authenticated; ownership-checked
GET	/api/admin/summary	Usage and feedback summary	Admin
GET	/api/admin/documents	List policy documents	Admin
POST	/api/admin/documents/upload	Upload a supported policy document	Admin
DELETE	/api/admin/documents/{filename}	Delete a policy document	Admin
POST	/api/admin/rebuild-knowledge-base	Rebuild the FAISS index	Admin
POST	/api/tickets	Create a support ticket using the ticket form	Authenticated
GET	/api/tickets	List the current user's tickets	Authenticated
GET	/api/tickets/{ticket_number}	Get one of the current user's tickets	Authenticated; owner-only
GET	/api/tickets/admin/all	List/filter all tickets	Admin
PATCH	/api/tickets/admin/{ticket_number}	Update status, priority, or assignee	Admin


Order status lookup and confirmation-protected ticket creation are available to the conversational agent as MCP tools; they are not separate public endpoints in this API table.

Protected endpoints use the standard authorization header:
Authorization: Bearer <access_token>
Ticket statuses used by the application include open, in_progress, resolved, and closed. Priorities are low, medium, and high.
Testing
Run the test suite from the repository root:
python -m pytest backend\tests -q
The most recent reported local run before the current deployment-configuration work was:
41 passed, 1 warning
The warning was a non-failing deprecation warning related to the current LangChain community FAISS integration. Rerun the suite after changing application code or dependencies to confirm the current result.

Useful checks:
python -m pip check
$env:PYTHONPATH = "$PWD\backend"
python -m alembic current
Development smoke tests are also present for MCP tool discovery, agent operation, order lookup and authorization, and persistent ticket confirmation. Review a smoke test before running it, because some tests may contact an external Gemini API or interact with the configured database.
Knowledge-base management
Policy source documents are stored under backend/data/documents/ and can be PDF or UTF-8 TXT files.

Recommended workflow after adding or changing policy content:
1. Review the source document.
2. Add it through the administrator dashboard or place it in the configured document directory.
3. Trigger the explicit knowledge-base rebuild action.
4. Test a few known questions and check that the sources and answers reflect the updated policy.
Changing a source document does not automatically rebuild the FAISS index. The index files are generated artifacts; regenerate them from the source documents when setting up a fresh checkout if the index is not present.
Security and safeguards
- Keep .env, API keys, database credentials, JWT secrets, and real customer data out of source control.
- Generate a strong, unique JWT signing secret for each environment.
- Use least-privilege database credentials.
- Enforce authentication and ownership checks on customer data in the backend, not only in the UI.
- Keep administrative APIs protected by backend role checks.
- Order lookup checks both the order number and authenticated user ID so one customer cannot retrieve another customer's tracking details.
- Ticket confirmation codes are short-lived, one-time, and bound to a user and conversation; failed or repeated confirmations must not create another ticket.
- Review uploaded documents before indexing them. Retrieved text is evidence for the model, not trusted instructions.
- Before any public production deployment, review HTTPS, CORS, rate limiting, monitoring, logging, backup, and secret-management requirements.
Current limitations
- Answers depend on the quality and coverage of the indexed policy documents and can be limited when retrieval does not find relevant evidence.
- Gemini requests can fail if the API key is invalid, network access is unavailable, or the project's API quota is exhausted.
- The FAISS vector store is a generated local artifact and may need to be rebuilt on a fresh checkout.
- A development order or tracking number is only test data; it does not represent a real shipment.
Author
Sanika Gajarishi
GitHub: https://github.com/Sanika-Gajarishi
License
This project is intended for educational and demonstration purposes. Add a specific license file if you plan to distribute the repository under an open-source license.
