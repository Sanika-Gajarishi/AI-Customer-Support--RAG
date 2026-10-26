from datetime import date

from sqlalchemy import delete, select

from app.database import SessionLocal, engine
from app.models import Order, User
from app.services.order_service import get_order_status


TEST_DATABASE = "shopease_migration_test_20261021"

OWNER_EMAIL = "mcp-order-owner@example.invalid"
OTHER_EMAIL = "mcp-order-other@example.invalid"

OWNER_ORDER = "ORD-MCP-TEST-1001"
OTHER_ORDER = "ORD-MCP-TEST-2002"


def get_or_create_test_user(db, email: str):
    user = db.scalar(
        select(User).where(User.email == email)
    )

    created = user is None

    if created:
        user = User(
            email=email,
            hashed_password="TEST-ONLY-NOT-A-REAL-PASSWORD-HASH",
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        db.flush()

    return user, created


def main() -> None:
    # Safety guard: refuse to seed data in any other database.
    if engine.url.database != TEST_DATABASE:
        raise RuntimeError(
            "Wrong database selected. Expected "
            f"{TEST_DATABASE!r}, got {engine.url.database!r}. "
            "No test data was added."
        )

    print(f"Test database confirmed: {engine.url.database}")

    db = SessionLocal()
    created_user_ids = []

    try:
        if not engine.dialect.has_table(
            engine.connect(),
            "orders",
        ):
            raise RuntimeError(
                "The orders table is missing from the test database."
            )

        owner, owner_created = get_or_create_test_user(
            db, OWNER_EMAIL
        )
        other, other_created = get_or_create_test_user(
            db, OTHER_EMAIL
        )

        if owner_created:
            created_user_ids.append(owner.id)

        if other_created:
            created_user_ids.append(other.id)

        db.flush()

        # Remove only these reserved test order numbers so the test
        # can be run again without creating duplicate records.
        db.execute(
            delete(Order).where(
                Order.order_number.in_(
                    [OWNER_ORDER, OTHER_ORDER]
                )
            )
        )

        db.add_all(
            [
                Order(
                    order_number=OWNER_ORDER,
                    user_id=owner.id,
                    status="shipped",
                    carrier="Demo Carrier",
                    tracking_number="TEST-TRACK-1001",
                    estimated_delivery=date(2026, 10, 30),
                ),
                Order(
                    order_number=OTHER_ORDER,
                    user_id=other.id,
                    status="processing",
                    carrier=None,
                    tracking_number=None,
                    estimated_delivery=None,
                ),
            ]
        )

        db.commit()

        owner_id = owner.id
        other_id = other.id

        print("\nTest 1: Customer retrieves their own order")
        result = get_order_status(OWNER_ORDER, owner_id)

        assert result["found"] is True, result
        assert result["status"] == "shipped", result
        assert result["tracking_number"] == "TEST-TRACK-1001"

        print("PASS: Own order status retrieved.")
        print("Status:", result["status"])
        print("Tracking number:", result["tracking_number"])

        print("\nTest 2: Customer tries to access another order")
        result = get_order_status(OTHER_ORDER, owner_id)

        assert result["found"] is False, result
        print("PASS: Another customer's order was not revealed.")

        print("\nTest 3: Another customer tries the first order")
        result = get_order_status(OWNER_ORDER, other_id)

        assert result["found"] is False, result
        print("PASS: Cross-customer lookup was rejected.")

        print("\nTest 4: Nonexistent order")
        result = get_order_status(
            "ORD-MCP-DOES-NOT-EXIST",
            owner_id,
        )

        assert result["found"] is False, result
        print("PASS: Nonexistent order returned not found.")

        print("\nSUCCESS: All order-service checks passed.")

    finally:
        # Clean up reserved demo order records and newly created users.
        try:
            db.rollback()
            db.execute(
                delete(Order).where(
                    Order.order_number.in_(
                        [OWNER_ORDER, OTHER_ORDER]
                    )
                )
            )

            for user_id in created_user_ids:
                db.execute(
                    delete(User).where(User.id == user_id)
                )

            db.commit()
            print("Temporary demo order records cleaned up.")

        except Exception:
            db.rollback()
            print(
                "WARNING: Test cleanup did not complete. "
                "Only the isolated test database was targeted."
            )

        db.close()


if __name__ == "__main__":
    main()