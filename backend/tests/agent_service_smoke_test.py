from pathlib import Path
import sys

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import User
from app.services.agent_service import answer_with_mcp_agent


def main() -> None:
    with SessionLocal() as db:
        user_id = db.scalar(
            select(User.id)
            .where(User.is_active.is_(True))
            .order_by(User.id)
            .limit(1)
        )

    if user_id is None:
        raise RuntimeError(
            "No active user found. Register a test user first."
        )

    question = "Can I return a product after 20 days?"

    print("Testing the actual Gemini + MCP agent service...")

    result = answer_with_mcp_agent(
        question,
        user_id=user_id,
    )

    print("\nAnswer:")
    print(result["answer"])

    print("\nSources:")
    for source in result["sources"]:
        print(f"- {source}")

    assert result["answer"], "The answer is empty."
    assert result["sources"], "No source filenames were returned."

    print("\nSUCCESS: Agent returned an answer and sources.")


if __name__ == "__main__":
    main()