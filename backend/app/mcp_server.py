import os
import sys
import traceback
from typing import Any

# Preload native numerical libraries before starting MCP stdio.
# This avoids a known first-import hang on some Windows configurations.
import numpy
import scipy.sparse.linalg

from mcp.server.fastmcp import FastMCP

from app.services.embedding_service import (
    create_embeddings,
    load_vectorstore,
)
from app.services.rag_service import (
    search_knowledge_base as retrieve_knowledge_base,
)
from app.services.order_service import (
    get_order_status as lookup_order_status,
)
from app.services.ticket_confirmation_service import (
    consume_pending_ticket_confirmation,
)


mcp = FastMCP(
    "ShopEase Knowledge Base",
    json_response=True,
)


def log(message: str) -> None:
    """Write diagnostics to stderr, never to the MCP protocol stream."""
    print(f"[mcp-server] {message}", file=sys.stderr, flush=True)


def get_authenticated_user_id() -> int | None:
    """Read customer identity supplied by the trusted backend."""
    value = os.getenv("SHOPEASE_AUTHENTICATED_USER_ID")

    if not value:
        return None

    try:
        user_id = int(value)
    except (TypeError, ValueError):
        return None

    return user_id if user_id > 0 else None


@mcp.tool()
def search_knowledge_base(query: str) -> dict[str, Any]:
    """Search ShopEase support policies and FAQs using the existing FAISS index."""
    log("search_knowledge_base invoked.")

    if not isinstance(query, str):
        raise ValueError("The query must be a string.")

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("The search query cannot be empty.")

    if len(cleaned_query) > 1000:
        raise ValueError("The query cannot exceed 1000 characters.")

    try:
        result = retrieve_knowledge_base(
            cleaned_query,
            enforce_threshold=True,
        )

        log(
            "Knowledge search completed: "
            f"found={result.get('found')}, "
            f"passages={len(result.get('results', []))}"
        )

        return result

    except Exception as exc:
        log(f"Knowledge search failed: {type(exc).__name__}: {exc}")
        traceback.print_exc(file=sys.stderr)
        raise


@mcp.tool()
def get_order_status(order_number: str) -> dict[str, Any]:
    """
    Retrieve an order's status for the authenticated customer.

    The order number can come from Gemini. The customer ID comes
    only from trusted backend context.
    """
    log("get_order_status invoked.")

    if not isinstance(order_number, str):
        raise ValueError("The order number must be a string.")

    cleaned_order_number = order_number.strip()

    if not cleaned_order_number:
        raise ValueError("The order number cannot be empty.")

    if len(cleaned_order_number) > 40:
        raise ValueError("The order number cannot exceed 40 characters.")

    user_id = get_authenticated_user_id()

    if user_id is None:
        raise ValueError(
            "Order lookup requires authenticated customer context."
        )

    try:
        result = lookup_order_status(
            order_number=cleaned_order_number,
            user_id=user_id,
        )

        log(f"Order lookup completed: found={result.get('found')}")
        return result

    except Exception as exc:
        log(f"Order lookup failed: {type(exc).__name__}: {exc}")
        traceback.print_exc(file=sys.stderr)
        raise


@mcp.tool()
def create_support_ticket(
    confirmation_code: str,
) -> dict[str, Any]:
    """
    Create a ticket by consuming a stored, valid confirmation code.

    The confirmation must belong to the authenticated customer and
    the current conversation. Ticket details are read from the stored
    confirmation, not from model-generated tool arguments.
    """
    log("create_support_ticket invoked.")

    if not isinstance(confirmation_code, str):
        return {
            "created": False,
            "message": "A valid confirmation code is required.",
        }

    cleaned_code = confirmation_code.strip()

    if not 20 <= len(cleaned_code) <= 64:
        return {
            "created": False,
            "message": (
                "This confirmation is invalid, expired, already used, "
                "or not associated with this conversation. No ticket "
                "was created."
            ),
        }

    user_id = get_authenticated_user_id()

    conversation_session_id = os.getenv(
        "SHOPEASE_AUTHENTICATED_CONVERSATION_SESSION_ID"
    )

    if user_id is None or not conversation_session_id:
        log(
            "Ticket creation rejected: authenticated customer or "
            "conversation context is missing."
        )

        return {
            "created": False,
            "message": (
                "Authenticated customer and conversation context "
                "are required."
            ),
        }

    try:
        result = consume_pending_ticket_confirmation(
            confirmation_code=cleaned_code,
            user_id=user_id,
            conversation_session_id=conversation_session_id,
        )

        log(
            "Ticket confirmation processed: "
            f"created={result.get('created')}"
        )

        return result

    except Exception as exc:
        log(
            "Ticket confirmation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        traceback.print_exc(file=sys.stderr)

        return {
            "created": False,
            "message": "Unable to process the ticket confirmation.",
        }


def main() -> None:
    """Load retrieval resources before starting MCP stdio."""
    log("Initializing the embedding model...")
    embeddings = create_embeddings()

    log("Loading the existing FAISS index...")
    load_vectorstore(embeddings)

    log(
        "Initialization complete. Registered tools: "
        "search_knowledge_base, get_order_status, "
        "create_support_ticket. Starting MCP stdio transport."
    )

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()