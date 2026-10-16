
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Feedback, Message, User
from app.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: int = Field(gt=0)
    is_helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/feedback", status_code=201)
def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 1. Find the assistant message.
        message = db.scalar(
            select(Message).where(
                Message.id == request.message_id,
                Message.role == "assistant",
            )
        )

        if message is None:
            raise HTTPException(
                status_code=404,
                detail="Assistant message not found.",
            )

        # 2. Find the conversation containing this message.
        conversation = db.get(
            Conversation,
            message.conversation_id,
        )

        # 3. Verify that the logged-in user owns the conversation.
        if (
            conversation is None
            or conversation.user_id != current_user.id
        ):
            raise HTTPException(
                status_code=404,
                detail="Assistant message not found.",
            )

        # 4. Save the feedback.
        feedback = Feedback(
            message_id=message.id,
            is_helpful=request.is_helpful,
            comment=(
                request.comment.strip()
                if request.comment and request.comment.strip()
                else None
            ),
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return {
            "message": "Feedback submitted successfully.",
            "feedback_id": feedback.id,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception("Feedback submission failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to submit feedback. Please try again.",
        )