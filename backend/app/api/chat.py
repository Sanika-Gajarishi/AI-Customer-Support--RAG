
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Message
from app.services.rag_service import answer_question

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
):
    message_text = request.message.strip()

    if not message_text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    try:
        # 1. Find the existing conversation or create a new one.
        if request.conversation_id:
            conversation = db.scalar(
                select(Conversation).where(
                    Conversation.session_id == request.conversation_id
                )
            )

            if conversation is None:
                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found.",
                )
        else:
            conversation = Conversation(session_id=str(uuid4()))
            db.add(conversation)
            db.flush()

        # 2. Load the six most recent messages BEFORE saving the
        # current question. This prevents the current question from
        # appearing twice in the conversation history.
        history_rows = db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
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

        # 3. Save the current customer's question.
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=message_text,
        )
        db.add(user_message)
        db.flush()

        # 4. Generate an answer using RAG and conversation history.
        result = answer_question(
            message_text,
            chat_history=chat_history,
        )

        # 5. Save the assistant's answer.
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
        )
        db.add(assistant_message)
        db.flush()

        # 6. Commit both messages to PostgreSQL.
        db.commit()

        # 7. Return the answer, sources, conversation ID,
        # and assistant message ID for the feedback feature.
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
