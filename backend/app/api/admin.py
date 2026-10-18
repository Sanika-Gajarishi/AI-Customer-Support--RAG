
import logging
import re
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conversation, Feedback, Message, User
from app.security import get_current_admin
from app.services.ingest_service import main as rebuild_faiss_index
logger = logging.getLogger(__name__)

router = APIRouter()

# backend/data/documents/
BACKEND_DIR = Path(__file__).resolve().parents[2]
DOCUMENTS_DIR = BACKEND_DIR / "data" / "documents"

ALLOWED_EXTENSIONS = {".txt", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def ensure_documents_directory():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_filename(filename: str | None) -> str:
    if not filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    # Reject paths and traversal attempts.
    if "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    if filename in {".", ".."}:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    # Permit common policy-document filename characters.
    if not re.fullmatch(r"[A-Za-z0-9 _.-]+", filename):
        raise HTTPException(
            status_code=400,
            detail="Filename contains unsupported characters.",
        )

    if filename.startswith("."):
        raise HTTPException(
            status_code=400,
            detail="Hidden filenames are not allowed.",
        )

    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only TXT and PDF files are supported.",
        )

    return filename


@router.get("/summary")
def get_admin_summary(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    total_users = db.scalar(
        select(func.count()).select_from(User)
    ) or 0

    total_conversations = db.scalar(
        select(func.count()).select_from(Conversation)
    ) or 0

    total_messages = db.scalar(
        select(func.count()).select_from(Message)
    ) or 0

    total_feedback = db.scalar(
        select(func.count()).select_from(Feedback)
    ) or 0

    helpful_feedback = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.is_helpful.is_(True))
    ) or 0

    unhelpful_feedback = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(Feedback.is_helpful.is_(False))
    ) or 0

    return {
        "admin_email": current_admin.email,
        "total_users": total_users,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_feedback": total_feedback,
        "helpful_feedback": helpful_feedback,
        "unhelpful_feedback": unhelpful_feedback,
    }


@router.get("/documents")
def list_documents(
    current_admin: User = Depends(get_current_admin),
):
    ensure_documents_directory()

    documents = []

    for path in sorted(DOCUMENTS_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            documents.append({
                "filename": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
            })

    return {
        "count": len(documents),
        "documents": documents,
    }



@router.post("/documents/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
):
    ensure_documents_directory()

    filename = validate_filename(file.filename)
    destination = DOCUMENTS_DIR / filename
    created_file = False

    try:
        content = await file.read(MAX_FILE_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 10 MB upload limit.",
            )

        if (
            destination.suffix.lower() == ".pdf"
            and not content.startswith(b"%PDF-")
        ):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file does not appear to be a valid PDF.",
            )

        if destination.suffix.lower() == ".txt":
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="TXT files must use UTF-8 encoding.",
                )

        # Exclusive creation prevents overwriting existing files.
        with destination.open("xb") as output:
            created_file = True
            output.write(content)

        return {
            "message": "Document uploaded successfully.",
            "filename": filename,
            "rebuild_required": True,
        }

    except HTTPException:
        raise

    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="A document with this filename already exists.",
        )

    except Exception:
        logger.exception("Document upload failed")

        if created_file and destination.exists():
            try:
                destination.unlink()
            except OSError:
                logger.exception("Could not remove partial upload")

        raise HTTPException(
            status_code=500,
            detail="Unable to upload document.",
        )

    finally:
        await file.close()



@router.delete("/documents/{filename}")
def delete_document(
    filename: str,
    current_admin: User = Depends(get_current_admin),
):
    ensure_documents_directory()

    filename = validate_filename(filename)
    destination = DOCUMENTS_DIR / filename

    try:
        if not destination.is_file():
            raise HTTPException(
                status_code=404,
                detail="Document not found.",
            )

        destination.unlink()

        return {
            "message": "Document deleted successfully.",
            "filename": filename,
            "rebuild_required": True,
        }

    except HTTPException:
        raise

    except OSError:
        logger.exception("Document deletion failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to delete document.",
        )

@router.post("/rebuild-knowledge-base")
def rebuild_knowledge_base(
    current_admin: User = Depends(get_current_admin),
):
    try:
        vectorstore = rebuild_faiss_index()

        return {
            "message": "Knowledge base rebuilt successfully.",
            "indexed_chunks": vectorstore.index.ntotal,
        }

    except Exception:
        logger.exception("Knowledge-base rebuild failed")

        raise HTTPException(
            status_code=500,
            detail="Knowledge-base rebuild failed. Check the backend logs.",
        )