
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
TOOL_TIMEOUT_SECONDS = 120

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-u", "-m", "app.mcp_server"],
    env={
        **os.environ,
        "PYTHONPATH": str(BACKEND_DIR),
    },
    cwd=str(PROJECT_ROOT),
)


def extract_payload(result: Any) -> dict:
    """Extract the tool's structured JSON result or parse its text output."""
    structured = getattr(result, "structuredContent", None)

    if structured is None:
        structured = getattr(result, "structured_content", None)

    if isinstance(structured, dict):
        return structured

    for block in result.content:
        if isinstance(block, types.TextContent):
            try:
                payload = json.loads(block.text)
            except json.JSONDecodeError:
                continue

            if isinstance(payload, dict):
                return payload

    raise RuntimeError(
        "MCP returned no readable JSON object. "
        f"Result content: {result.content!r}"
    )


async def call_tool_with_timeout(
    session: ClientSession,
    query: str,
) -> dict:
    """Call the RAG search tool, report errors, and prevent indefinite waits."""
    print(
        f"[mcp-client] Calling search tool with query: {query}",
        flush=True,
    )

    try:
        result = await asyncio.wait_for(
            session.call_tool(
                "search_knowledge_base",
                {"query": query},
            ),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        print(
            f"[mcp-client] TIMEOUT after {TOOL_TIMEOUT_SECONDS} seconds.",
            flush=True,
        )
        raise RuntimeError(
            "MCP tool did not return in time. "
            "Check the [mcp-server] diagnostics printed above."
        ) from exc

    is_error = getattr(
        result,
        "isError",
        getattr(result, "is_error", False),
    )

    if is_error:
        details = [
            block.text
            for block in result.content
            if isinstance(block, types.TextContent)
        ]
        raise RuntimeError(
            "MCP tool reported an error: " + "\n".join(details)
        )

    payload = extract_payload(result)
    print("[mcp-client] Tool response received.", flush=True)
    return payload


async def main() -> None:
    print("Starting ShopEase MCP server through stdio...", flush=True)

    async with stdio_client(SERVER_PARAMS) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("MCP handshake successful.", flush=True)

            response = await session.list_tools()
            tool_names = [tool.name for tool in response.tools]

            print("Discovered tools:", tool_names, flush=True)

            if "search_knowledge_base" not in tool_names:
                raise RuntimeError(
                    "Expected search_knowledge_base was not discovered."
                )

            # Test 1: A policy question that should retrieve evidence.
            print("\nTest 1: In-scope policy question", flush=True)

            payload = await call_tool_with_timeout(
                session,
                "Can I return a product after 20 days?",
            )

            print("Found:", payload.get("found"))
            print("Sources:", payload.get("sources", []))
            print("Passage count:", len(payload.get("results", [])))

            for item in payload.get("results", []):
                print(
                    f"- {item.get('source', 'Unknown source')} "
                    f"(distance: {item.get('distance', 'N/A')})"
                )
                print(
                    item.get("content", "")[:180].replace("\n", " ")
                )

            if not payload.get("found"):
                raise RuntimeError(
                    "Expected policy evidence, but no passages were found."
                )

            # Test 2: An unrelated question should be rejected.
            print("\nTest 2: Out-of-scope question", flush=True)

            payload = await call_tool_with_timeout(
                session,
                "What is the capital of Japan?",
            )

            print("Found:", payload.get("found"))
            print("Sources:", payload.get("sources", []))

            if payload.get("found"):
                raise RuntimeError(
                    "An out-of-scope question unexpectedly returned results."
                )

            print(
                "\nSUCCESS: MCP discovery and both retrieval checks passed.",
                flush=True,
            )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.", file=sys.stderr, flush=True)
        raise
