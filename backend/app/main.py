from fastapi import FastAPI
from app.api.feedback import router as feedback_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router

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
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(
    admin_router,
    prefix="/api/admin",
    tags=["Admin"],
)