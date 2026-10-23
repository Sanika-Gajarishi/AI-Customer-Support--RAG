
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Message, User
from app.security import get_current_user
from app.services.agent_service import answer_with_mcp_agent

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    conversation_id: str
    assistant_message_id: int


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message_text = request.message.strip()

    if not message_text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        # 1. Find the user's conversation or create a new one.
        if request.conversation_id:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.session_id == request.conversation_id,
                    Conversation.user_id == current_user.id,
                )
            )

            # Do not reveal whether another user's conversation exists.
            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found.",
                )

        else:
            conversation = Conversation(
                session_id=str(uuid4()),
                user_id=current_user.id,
            )
            db.add(conversation)
            db.flush()

        # 2. Load the six most recent messages before saving
        # the current question.
        history_rows = db.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation.id
            )
            .order_by(Message.id.desc())
            .limit(6)
        ).all()

        chat_history = [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in reversed(history_rows)
        ]

        # 3. Save the customer's question.
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=message_text,
        )
        db.add(user_message)
        db.flush()

        # 4. Generate the answer using RAG and conversation history.
        result = answer_with_mcp_agent(
            message_text,
            user_id=current_user.id,
            chat_history=chat_history,
            conversation_session_id=conversation.session_id,
        )

        # 5. Save the assistant's response.
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
        )
        db.add(assistant_message)
        db.flush()

        # 6. Commit the conversation messages.
        db.commit()

        # 7. Return the response expected by the frontend.
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            conversation_id=conversation.session_id,
            assistant_message_id=assistant_message.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception("Chat request failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to process your question. Please try again.",
        )
