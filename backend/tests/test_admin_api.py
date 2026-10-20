
import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import User
from app.security import get_current_admin, get_current_user

# Reuse the isolated SQLite test database and session factory.
from test_tickets_api import TestingSessionLocal, test_engine


@pytest.fixture
def admin_environment(monkeypatch, tmp_path):
    from app.api import admin as admin_module

    from app.database import Base

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as db:
        customer = User(
            email="admin-test-customer@example.com",
            hashed_password="test-password-hash",
            is_active=True,
            is_admin=False,
        )
        admin = User(
            email="admin-test-admin@example.com",
            hashed_password="test-password-hash",
            is_active=True,
            is_admin=True,
        )
        db.add_all([customer, admin])
        db.commit()
        db.refresh(customer)
        db.refresh(admin)

        identities = {"customer": customer, "admin": admin}

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        lambda: identities["customer"]
    )
    app.dependency_overrides[get_current_admin] = (
        lambda: identities["admin"]
    )

    monkeypatch.setattr(admin_module, "DOCUMENTS_DIR", tmp_path)

    with TestClient(app) as client:
        yield client, identities, tmp_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_admin_can_get_summary(admin_environment):
    client, _, _ = admin_environment

    response = client.get("/api/admin/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["admin_email"] == "admin-test-admin@example.com"
    assert data["total_users"] == 2
    assert data["total_conversations"] == 0
    assert data["total_messages"] == 0
    assert data["total_feedback"] == 0


def test_customer_cannot_access_admin_summary(admin_environment):
    client, identities, _ = admin_environment

    # Remove the override that bypasses administrator authorization.
    app.dependency_overrides.pop(get_current_admin, None)

    # The real get_current_admin dependency will now check this customer.
    app.dependency_overrides[get_current_user] = (
        lambda: identities["customer"]
    )

    response = client.get("/api/admin/summary")

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."



def test_admin_can_list_documents(admin_environment):
    client, _, documents_dir = admin_environment
    (documents_dir / "return_policy.txt").write_text(
        "Returns are accepted within the stated return period.",
        encoding="utf-8",
    )
    (documents_dir / "ignore.json").write_text(
        "{}",
        encoding="utf-8",
    )

    response = client.get("/api/admin/documents")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["documents"][0]["filename"] == "return_policy.txt"
    assert data["documents"][0]["extension"] == ".txt"


def test_admin_can_upload_txt_document(admin_environment):
    client, _, documents_dir = admin_environment

    response = client.post(
        "/api/admin/documents/upload",
        files={
            "file": (
                "new_policy.txt",
                b"Customers may return eligible items.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["rebuild_required"] is True
    assert (documents_dir / "new_policy.txt").read_text(
        encoding="utf-8"
    ) == "Customers may return eligible items."


def test_upload_rejects_unsupported_extension(admin_environment):
    client, _, documents_dir = admin_environment

    response = client.post(
        "/api/admin/documents/upload",
        files={
            "file": ("malware.exe", b"not allowed", "application/octet-stream")
        },
    )

    assert response.status_code == 400
    assert not (documents_dir / "malware.exe").exists()


def test_upload_rejects_invalid_pdf(admin_environment):
    client, _, documents_dir = admin_environment

    response = client.post(
        "/api/admin/documents/upload",
        files={
            "file": ("policy.pdf", b"this is not a PDF", "application/pdf")
        },
    )

    assert response.status_code == 400
    assert not (documents_dir / "policy.pdf").exists()


def test_upload_rejects_duplicate_filename(admin_environment):
    client, _, documents_dir = admin_environment
    original = b"Original policy contents."
    (documents_dir / "policy.txt").write_bytes(original)

    response = client.post(
        "/api/admin/documents/upload",
        files={
            "file": ("policy.txt", b"Replacement contents.", "text/plain")
        },
    )

    assert response.status_code == 409
    assert (documents_dir / "policy.txt").read_bytes() == original


def test_admin_can_delete_document(admin_environment):
    client, _, documents_dir = admin_environment
    (documents_dir / "old_policy.txt").write_text(
        "Old policy",
        encoding="utf-8",
    )

    response = client.delete("/api/admin/documents/old_policy.txt")

    assert response.status_code == 200
    assert response.json()["rebuild_required"] is True
    assert not (documents_dir / "old_policy.txt").exists()


def test_delete_rejects_path_traversal(admin_environment):
    client, _, _ = admin_environment

    response = client.delete(
        "/api/admin/documents/../secret.txt"
    )

    assert response.status_code in (400, 404)


def test_admin_rebuilds_knowledge_base(admin_environment, monkeypatch):
    client, _, _ = admin_environment

    class FakeIndex:
        ntotal = 42

    class FakeVectorStore:
        index = FakeIndex()

    from app.api import admin as admin_module

    monkeypatch.setattr(
        admin_module,
        "rebuild_faiss_index",
        lambda: FakeVectorStore(),
    )

    response = client.post("/api/admin/rebuild-knowledge-base")

    assert response.status_code == 200
    assert response.json()["indexed_chunks"] == 42


def test_knowledge_base_rebuild_failure_returns_500(
    admin_environment, monkeypatch
):
    client, _, _ = admin_environment

    from app.api import admin as admin_module

    def fail_rebuild():
        raise RuntimeError("Simulated ingestion failure")

    monkeypatch.setattr(
        admin_module,
        "rebuild_faiss_index",
        fail_rebuild,
    )

    response = client.post("/api/admin/rebuild-knowledge-base")

    assert response.status_code == 500
    assert response.json()["detail"].startswith(
        "Knowledge-base rebuild failed."
    )
