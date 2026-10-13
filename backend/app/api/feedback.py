
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Feedback, Message

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: int
    is_helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


@router.post("/feedback")
def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
):
    try:
        message = db.get(Message, request.message_id)

        if message is None:
            raise HTTPException(
                status_code=404,
                detail="Message not found.",
            )

        if message.role != "assistant":
            raise HTTPException(
                status_code=400,
                detail="Feedback can only be submitted for assistant messages.",
            )

        feedback = Feedback(
            message_id=message.id,
            is_helpful=request.is_helpful,
            comment=request.comment.strip() if request.comment else None,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return {
            "status": "success",
            "feedback_id": feedback.id,
            "message": "Thank you for your feedback!",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to save feedback.",
        )
