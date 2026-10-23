import logging
from typing import Any

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Order


logger = logging.getLogger(__name__)


def get_order_status(
    order_number: str,
    user_id: int,
) -> dict[str, Any]:
    """
    Retrieve an order only when it belongs to the specified user.

    The user_id must come from trusted application context,
    not from Gemini-generated tool arguments.
    """

    if not isinstance(order_number, str):
        raise ValueError("Order number must be a string.")

    cleaned_order_number = order_number.strip()

    if not cleaned_order_number:
        raise ValueError("Order number cannot be empty.")

    if len(cleaned_order_number) > 40:
        raise ValueError("Order number cannot exceed 40 characters.")

    if (
        isinstance(user_id, bool)
        or not isinstance(user_id, int)
        or user_id <= 0
    ):
        raise ValueError("A valid customer ID is required.")

    db = SessionLocal()

    try:
        # IMPORTANT: filter by both order number and customer ID.
        # This prevents returning another customer's order details.
        order = db.scalar(
            select(Order).where(
                Order.order_number == cleaned_order_number,
                Order.user_id == user_id,
            )
        )

        if order is None:
            # Use the same response for nonexistent orders and
            # orders belonging to another customer.
            return {
                "found": False,
                "message": (
                    "No order was found for that order number "
                    "in your account."
                ),
            }

        return {
            "found": True,
            "order_number": order.order_number,
            "status": order.status,
            "carrier": order.carrier,
            "tracking_number": order.tracking_number,
            "estimated_delivery": (
                order.estimated_delivery.isoformat()
                if order.estimated_delivery
                else None
            ),
        }

    except ValueError:
        raise

    except Exception:
        logger.exception("Order lookup failed")
        raise

    finally:
        db.close()