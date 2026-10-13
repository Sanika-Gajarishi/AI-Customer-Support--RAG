from fastapi import FastAPI
from app.api.feedback import router as feedback_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router

app = FastAPI(
    title="ShopEase AI Customer Support",
    description="A RAG-based customer support API.",
    version="0.2.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(chat_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")