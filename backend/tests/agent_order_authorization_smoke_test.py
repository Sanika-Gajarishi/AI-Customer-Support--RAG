from datetime import date
from uuid import uuid4

from sqlalchemy import delete

from app.database import SessionLocal, engine
from app.models import Order, User
from app.services.agent_service import answer_with_mcp_agent


EXPECTED_DATABASE = "shopease_migration_test_20261021"


def main() -> None:
    if engine.url.database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"Safety check failed: expected {EXPECTED_DATABASE!r}, "
            f"got {engine.url.database!r}. Test cancelled."
        )

    print(f"Test database confirmed: {engine.url.database}")

    suffix = uuid4().hex[:10].upper()
    owner_email = f"mcp-owner-{suffix}@example.invalid"
    other_email = f"mcp-other-{suffix}@example.invalid"
    order_number = f"ORD-SECURITY-{suffix}"
    tracking_number = f"TRACK-SECRET-{suffix}"
    carrier_name = f"Private Carrier {suffix}"

    created_user_ids = []

    try:
        # Create two temporary customers and an order owned by the first.
        with SessionLocal() as db:
            owner = User(
                email=owner_email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )

            other_customer = User(
                email=other_email,
                hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
                is_active=True,
                is_admin=False,
            )

            db.add_all([owner, other_customer])
            db.flush()

            owner_id = owner.id
            other_id = other_customer.id
            created_user_ids.extend([owner_id, other_id])

            order = Order(
                order_number=order_number,
                user_id=owner_id,
                status="shipped",
                carrier=carrier_name,
                tracking_number=tracking_number,
                estimated_delivery=date(2026, 10, 30),
            )

            db.add(order)
            db.commit()

        print("\nTest 1: Owner requests their own order")

        owner_result = answer_with_mcp_agent(
            (
                f"Please check order {order_number}. "
                "Tell me its status, carrier, and tracking number. "
                "Use the order lookup tool and do not guess."
            ),
            user_id=owner_id,
        )

        owner_answer = owner_result["answer"].casefold()
        assert "shipped" in owner_answer, owner_result
        assert tracking_number.casefold() in owner_answer, owner_result
        assert carrier_name.casefold() in owner_answer, owner_result

        print("PASS: Owner received their order information.")

        print("\nTest 2: A different customer requests the same order")

        other_result = answer_with_mcp_agent(
            (
                f"Please look up order {order_number}. "
                "Tell me its status, carrier, and tracking number. "
                "Use the order lookup tool and do not guess."
            ),
            user_id=other_id,
        )

        other_answer = other_result["answer"].casefold()

        # These unique values must never appear in the other customer's
        # answer, even if the model tries to invent a response.
        assert tracking_number.casefold() not in other_answer, (
            "SECURITY FAILURE: another customer received the tracking number."
        )

        assert carrier_name.casefold() not in other_answer, (
            "SECURITY FAILURE: another customer received the carrier."
        )

        print("PASS: Private order details were not disclosed.")
        print("\nSUCCESS: Both agent authorization checks passed.")

    finally:
        # Remove only this run's test order and temporary users.
        with SessionLocal() as db:
            db.execute(
                delete(Order).where(
                    Order.order_number == order_number
                )
            )

            if created_user_ids:
                db.execute(
                    delete(User).where(
                        User.id.in_(created_user_ids)
                    )
                )

            db.commit()

        print("Temporary test order and users cleaned up.")


if __name__ == "__main__":
    main()