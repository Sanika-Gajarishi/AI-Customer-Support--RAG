
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Message, User
from app.security import get_current_user

router = APIRouter()


@router.get("/history/{conversation_id}")
def get_conversation_history(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.session_id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id.asc())
    ).all()

    return {
        "conversation_id": conversation.session_id,
        "messages": [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in messages
        ],
    }
