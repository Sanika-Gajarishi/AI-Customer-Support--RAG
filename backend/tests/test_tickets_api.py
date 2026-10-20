import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Conversation, Feedback, Message, User
from app.security import (
    create_access_token,
    get_current_admin,
    get_current_user,
)
from datetime import datetime, timedelta, timezone

import jwt

from app.security import JWT_ALGORITHM, JWT_SECRET_KEY



# An isolated in-memory SQLite database. This does not use your .env database.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture
def test_environment():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as db:
        customer = User(
            email="customer-test@example.com",
            hashed_password="test-password-hash",
            is_active=True,
            is_admin=False,
        )
        another_customer = User(
            email="another-customer-test@example.com",
            hashed_password="test-password-hash",
            is_active=True,
            is_admin=False,
        )
        admin = User(
            email="admin-test@example.com",
            hashed_password="test-password-hash",
            is_active=True,
            is_admin=True,
        )

        db.add_all([customer, another_customer, admin])
        db.commit()

        db.refresh(customer)
        db.refresh(another_customer)
        db.refresh(admin)

        # Hold the test identities for dependency overrides.
        identities = {
            "user": customer,
            "another_customer": another_customer,
            "admin": admin,
        }

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        lambda: identities["user"]
    )
    app.dependency_overrides[get_current_admin] = (
        lambda: identities["admin"]
    )

    with TestClient(app) as client:
        yield client, identities

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_sample_ticket(client):
    response = client.post(
        "/api/tickets",
        json={
            "subject": "Refund has not arrived",
            "description": (
                "My refund has not arrived after the expected "
                "processing period. Please investigate."
            ),
            "priority": "medium",
        },
    )
    return response


def test_customer_can_create_ticket(test_environment):
    client, identities = test_environment

    response = create_sample_ticket(client)

    assert response.status_code == 201
    ticket = response.json()
    assert ticket["ticket_number"].startswith("TKT-")
    assert ticket["user_id"] == identities["user"].id
    assert ticket["status"] == "open"
    assert ticket["priority"] == "medium"


def test_customer_can_list_own_tickets(test_environment):
    client, _ = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201

    response = client.get("/api/tickets")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert (
        response.json()["tickets"][0]["ticket_number"]
        == created.json()["ticket_number"]
    )


def test_customer_cannot_access_another_customers_ticket(
    test_environment,
):
    client, identities = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201
    ticket_number = created.json()["ticket_number"]

    # Simulate a different authenticated customer.
    app.dependency_overrides[get_current_user] = (
        lambda: identities["another_customer"]
    )

    response = client.get(f"/api/tickets/{ticket_number}")

    assert response.status_code == 404


def test_customer_cannot_list_another_customers_tickets(
    test_environment,
):
    client, identities = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201

    app.dependency_overrides[get_current_user] = (
        lambda: identities["another_customer"]
    )

    response = client.get("/api/tickets")

    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_admin_can_list_all_tickets(test_environment):
    client, _ = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201

    response = client.get("/api/tickets/admin/all")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_admin_can_update_ticket_status(test_environment):
    client, _ = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201
    ticket_number = created.json()["ticket_number"]

    response = client.patch(
        f"/api/tickets/admin/{ticket_number}",
        json={
            "status": "in_progress",
            "priority": "high",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["priority"] == "high"



def test_customer_cannot_update_ticket(test_environment):
    client, identities = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201
    ticket_number = created.json()["ticket_number"]

    # Remove the admin override so the real authorization
    # dependency checks the logged-in customer's role.
    app.dependency_overrides.pop(get_current_admin, None)

    # The current user is still the ordinary customer.
    app.dependency_overrides[get_current_user] = (
        lambda: identities["user"]
    )

    response = client.patch(
        f"/api/tickets/admin/{ticket_number}",
        json={"status": "resolved"},
    )

    assert response.status_code == 403



def test_invalid_ticket_priority_is_rejected(test_environment):
    client, _ = test_environment

    response = client.post(
        "/api/tickets",
        json={
            "subject": "Refund has not arrived",
            "description": (
                "My refund has not arrived after the expected "
                "processing period. Please investigate."
            ),
            "priority": "urgent",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["status", "priority"])
def test_admin_cannot_set_status_or_priority_to_null(
    test_environment, field
):
    client, _ = test_environment

    created = create_sample_ticket(client)
    assert created.status_code == 201

    ticket_number = created.json()["ticket_number"]

    response = client.patch(
        f"/api/tickets/admin/{ticket_number}",
        json={field: None},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Status and priority cannot be null."
    )

def test_inactive_customer_cannot_access_protected_endpoint(
    test_environment,
):
    client, identities = test_environment
    user_id = identities["user"].id

    # Deactivate the customer in the test database.
    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        user.is_active = False
        db.commit()

    # Use real JWT authentication for this test.
    app.dependency_overrides.pop(get_current_user, None)

    token = create_access_token(user_id)

    response = client.get(
        "/api/tickets",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive account."


def test_customer_can_register(test_environment):
    client, _ = test_environment

    response = client.post(
        "/api/auth/register",
        json={
            "email": "new-customer@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "new-customer@example.com"
    assert response.json()["is_admin"] is False
    assert "hashed_password" not in response.json()


def test_duplicate_registration_is_rejected(test_environment):
    client, _ = test_environment

    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePass123!",
    }

    first_response = client.post("/api/auth/register", json=payload)
    second_response = client.post("/api/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_customer_can_login(test_environment):
    client, _ = test_environment

    registration = client.post(
        "/api/auth/register",
        json={
            "email": "login-customer@example.com",
            "password": "SecurePass123!",
        },
    )
    assert registration.status_code == 201

    response = client.post(
        "/api/auth/login",
        json={
            "email": "login-customer@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert isinstance(response.json()["access_token"], str)
    assert response.json()["expires_in"] > 0


def test_login_rejects_incorrect_password(test_environment):
    client, _ = test_environment

    client.post(
        "/api/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "SecurePass123!",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_profile_rejects_missing_token(test_environment):
    client, _ = test_environment

    # Remove the test fixture's authentication bypass.
    app.dependency_overrides.pop(get_current_user, None)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_profile_rejects_invalid_token(test_environment):
    client, _ = test_environment

    # Use the real JWT validation dependency.
    app.dependency_overrides.pop(get_current_user, None)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_inactive_customer_cannot_login(test_environment):
    client, _ = test_environment

    registration = client.post(
        "/api/auth/register",
        json={
            "email": "inactive-login@example.com",
            "password": "SecurePass123!",
        },
    )
    assert registration.status_code == 201

    user_id = registration.json()["id"]

    # Deactivate the test user in the isolated SQLite database.
    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        user.is_active = False
        db.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "inactive-login@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive account."


def test_authenticated_customer_can_access_profile(test_environment):
    client, identities = test_environment
    user = identities["user"]

    # Use real JWT validation rather than the fixture override.
    app.dependency_overrides.pop(get_current_user, None)

    token = create_access_token(user.id)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == user.id
    assert response.json()["email"] == user.email
    assert response.json()["is_admin"] is False


def test_profile_rejects_expired_token(test_environment):
    client, identities = test_environment
    user_id = identities["user"].id

    app.dependency_overrides.pop(get_current_user, None)

    expired_token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401

def test_chat_creates_conversation_and_saves_messages(
    test_environment, monkeypatch
):
    client, _ = test_environment

    def fake_answer_question(message, chat_history=None):
        return {
            "answer": "You can return eligible products according to our return policy.",
            "sources": ["return_policy.pdf"],
        }

    monkeypatch.setattr(
        "app.api.chat.answer_question",
        fake_answer_question,
    )

    response = client.post(
        "/api/chat",
        json={"message": "What is your return policy?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"].startswith("You can return eligible products")
    assert data["sources"] == ["return_policy.pdf"]
    assert data["conversation_id"]
    assert data["assistant_message_id"] > 0

    history_response = client.get(
        f"/api/history/{data['conversation_id']}"
    )
    assert history_response.status_code == 200

    messages = history_response.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is your return policy?"
    assert messages[1]["role"] == "assistant"


def test_chat_rejects_whitespace_only_message(test_environment):
    client, _ = test_environment

    response = client.post(
        "/api/chat",
        json={"message": "    "},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Message cannot be empty."


def test_chat_cannot_use_another_customers_conversation(
    test_environment,
):
    client, identities = test_environment

    with TestingSessionLocal() as db:
        conversation = Conversation(
            session_id="another-customers-session",
            user_id=identities["another_customer"].id,
        )
        db.add(conversation)
        db.commit()

    response = client.post(
        "/api/chat",
        json={
            "message": "What is my order status?",
            "conversation_id": "another-customers-session",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found."


def test_history_returns_messages_in_order(
    test_environment, monkeypatch
):
    client, _ = test_environment

    monkeypatch.setattr(
        "app.api.chat.answer_question",
        lambda message, chat_history=None: {
            "answer": "Please review our return policy.",
            "sources": ["return_policy.pdf"],
        },
    )

    chat_response = client.post(
        "/api/chat",
        json={"message": "How do returns work?"},
    )
    assert chat_response.status_code == 200

    conversation_id = chat_response.json()["conversation_id"]

    response = client.get(f"/api/history/{conversation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert [message["role"] for message in data["messages"]] == [
        "user",
        "assistant",
    ]


def test_customer_cannot_access_another_customers_history(
    test_environment,
):
    client, identities = test_environment

    with TestingSessionLocal() as db:
        conversation = Conversation(
            session_id="private-history-session",
            user_id=identities["another_customer"].id,
        )
        db.add(conversation)
        db.commit()

    response = client.get("/api/history/private-history-session")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found."


def test_customer_can_submit_feedback_for_assistant_message(
    test_environment, monkeypatch
):
    client, _ = test_environment

    monkeypatch.setattr(
        "app.api.chat.answer_question",
        lambda message, chat_history=None: {
            "answer": "You can track your order from your account.",
            "sources": ["order_tracking.pdf"],
        },
    )

    chat_response = client.post(
        "/api/chat",
        json={"message": "How can I track my order?"},
    )
    assert chat_response.status_code == 200

    assistant_message_id = chat_response.json()["assistant_message_id"]

    response = client.post(
        "/api/feedback",
        json={
            "message_id": assistant_message_id,
            "is_helpful": True,
            "comment": "This answer was useful.",
        },
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Feedback submitted successfully."
    assert response.json()["feedback_id"] > 0


def test_feedback_rejects_customer_message(test_environment):
    client, _ = test_environment

    # Create a conversation and a customer message directly.
    with TestingSessionLocal() as db:
        conversation = Conversation(
            session_id="feedback-test-session",
            user_id=1,
        )
        db.add(conversation)
        db.flush()

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content="Where is my order?",
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        message_id = user_message.id

    response = client.post(
        "/api/feedback",
        json={
            "message_id": message_id,
            "is_helpful": True,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Assistant message not found."


def test_customer_cannot_submit_feedback_for_another_customers_message(
    test_environment,
):
    client, identities = test_environment

    with TestingSessionLocal() as db:
        conversation = Conversation(
            session_id="other-customer-feedback-session",
            user_id=identities["another_customer"].id,
        )
        db.add(conversation)
        db.flush()

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="Your order has shipped.",
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        message_id = assistant_message.id

    response = client.post(
        "/api/feedback",
        json={
            "message_id": message_id,
            "is_helpful": False,
            "comment": "Not my conversation.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Assistant message not found."
