import json
from datetime import date
from uuid import uuid4

from sqlalchemy import delete, select

from app.database import SessionLocal, engine
from app.models import Order, User
from app.services.agent_service import answer_with_mcp_agent


EXPECTED_DATABASE = "shopease_support"


def main() -> None:
    # Prevent this test from running against an unexpected database.
    database_name = engine.url.database

    if database_name != EXPECTED_DATABASE:
        raise RuntimeError(
            f"Expected database {EXPECTED_DATABASE!r}; "
            f"found {database_name!r}. Test cancelled."
        )

    print(f"Development database confirmed: {database_name}")

    order_number = f"ORD-MCP-{uuid4().hex[:12].upper()}"
    tracking_number = f"MCP-TRACK-{uuid4().hex[:8].upper()}"

    customer_id = None
    order_created = False

    try:
        # Use an existing active account, but create no real order.
        with SessionLocal() as db:
            customer = db.scalar(
                select(User)
                .where(User.is_active.is_(True))
                .order_by(User.id)
                .limit(1)
            )

            if customer is None:
                raise RuntimeError(
                    "No active user exists. Register a test user first."
                )

            customer_id = customer.id

            demo_order = Order(
                order_number=order_number,
                user_id=customer_id,
                status="shipped",
                carrier="Demo Courier",
                tracking_number=tracking_number,
                estimated_delivery=date(2026, 10, 30),
            )

            db.add(demo_order)
            db.commit()
            order_created = True

        print("\nTemporary demo order created.")
        print("\nTest: Ask Gemini for the order status through MCP.")

        question = (
            f"Please check my order {order_number}. "
            "Tell me its current status, delivery carrier, "
            "tracking number, and estimated delivery date. "
            "Use the actual order lookup tool. Do not guess."
        )

        result = answer_with_mcp_agent(
            question,
            user_id=customer_id,
        )

        print("\nAgent response:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        answer = result["answer"].casefold()

        assert "shipped" in answer, (
            "Expected the answer to include the actual status 'shipped'."
        )

        assert tracking_number.casefold() in answer, (
            "Expected the answer to contain the exact tracking number. "
            "Check whether Gemini called get_order_status."
        )

        assert "demo courier" in answer, (
            "Expected the answer to identify the actual demo carrier."
        )

        print("\nSUCCESS: Gemini retrieved the demo order through MCP.")

    finally:
        if order_created and customer_id is not None:
            with SessionLocal() as db:
                db.execute(
                    delete(Order).where(
                        Order.order_number == order_number,
                        Order.user_id == customer_id,
                    )
                )
                db.commit()

            print("Temporary demo order cleaned up.")


if __name__ == "__main__":
    main()