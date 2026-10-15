
import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api"
CHAT_URL = f"{API_BASE_URL}/chat"
FEEDBACK_URL = f"{API_BASE_URL}/feedback"


AUTH_URL = f"{API_BASE_URL}/auth"

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "current_user" not in st.session_state:
    st.session_state.current_user = None


def auth_headers():
    token = st.session_state.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


if not st.session_state.access_token:
    st.title("💬 ShopEase AI Support")
    st.subheader("Welcome")
    st.caption("Log in or create an account to continue.")

    auth_mode = st.radio(
        "Choose an option",
        ["Login", "Register"],
        horizontal=True,
    )

    with st.form("authentication_form"):
        email = st.text_input("Email").strip().lower()
        password = st.text_input(
            "Password",
            type="password",
        )

        if auth_mode == "Register":
            st.caption("Use a password between 8 and 128 characters.")

        submitted = st.form_submit_button(
            auth_mode,
            use_container_width=True,
        )

    if submitted:
        if not email or not password:
            st.error("Enter your email and password.")
        else:
            try:
                if auth_mode == "Register":
                    response = requests.post(
                        f"{AUTH_URL}/register",
                        json={
                            "email": email,
                            "password": password,
                        },
                        timeout=15,
                    )

                    if response.status_code == 201:
                        st.success(
                            "Account created! Switch to Login to continue."
                        )
                    else:
                        st.error(
                            response.json().get(
                                "detail",
                                "Registration failed.",
                            )
                        )

                else:
                    response = requests.post(
                        f"{AUTH_URL}/login",
                        json={
                            "email": email,
                            "password": password,
                        },
                        timeout=15,
                    )

                    if response.ok:
                        token_data = response.json()
                        token = token_data["access_token"]

                        profile_response = requests.get(
                            f"{AUTH_URL}/me",
                            headers={
                                "Authorization": f"Bearer {token}"
                            },
                            timeout=15,
                        )
                        profile_response.raise_for_status()

                        st.session_state.access_token = token
                        st.session_state.current_user = (
                            profile_response.json()
                        )
                        st.session_state.conversation_id = None
                        st.session_state.messages = []
                        st.rerun()
                    else:
                        st.error(
                            response.json().get(
                                "detail",
                                "Login failed.",
                            )
                        )

            except requests.exceptions.RequestException:
                st.error(
                    "Cannot reach the backend. Check that FastAPI is running."
                )

    st.stop()

st.set_page_config(
    page_title="ShopEase AI Support",
    page_icon="💬",
    layout="centered",
)

st.title("💬 ShopEase AI Support")
st.caption("Ask questions about returns, refunds, shipping, and more.")


def start_new_chat():
    st.session_state.conversation_id = None
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I'm the ShopEase support assistant. "
                "How can I help you today?"
            ),
            "sources": [],
        }
    ]


if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "messages" not in st.session_state:
    start_new_chat()


with st.sidebar:
    
    user = st.session_state.current_user

    st.caption(f"Signed in as: {user['email']}")

    if user.get("is_admin"):
        st.success("Administrator account")

    if st.button("Log out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.current_user = None
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("Conversation")

    if st.session_state.conversation_id:
        st.caption(f"ID: {st.session_state.conversation_id}")

    if st.button("Start new chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.caption("ShopEase demo customer-support assistant")


# Display existing messages and feedback controls.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        sources = message.get("sources", [])
        if sources:
            with st.expander("View sources"):
                for source in sources:
                    st.write(f"📄 {source}")

        message_id = message.get("assistant_message_id")

        # Feedback is available for persisted assistant answers.
        if message["role"] == "assistant" and message_id:
            submitted_key = f"feedback_submitted_{message_id}"

            if st.session_state.get(submitted_key, False):
                st.caption("✓ Feedback submitted. Thank you!")
            else:
                with st.expander("Was this answer helpful?"):
                    choice = st.selectbox(
                        "Rate this answer",
                        options=[
                            "Select a rating",
                            "Helpful",
                            "Not helpful",
                        ],
                        key=f"feedback_choice_{message_id}",
                    )

                    comment = st.text_input(
                        "Optional comment",
                        max_chars=1000,
                        key=f"feedback_comment_{message_id}",
                    )

                    if st.button(
                        "Submit feedback",
                        key=f"submit_feedback_{message_id}",
                    ):
                        if choice == "Select a rating":
                            st.warning("Please select a rating first.")
                        else:
                            payload = {
                                "message_id": message_id,
                                "is_helpful": choice == "Helpful",
                                "comment": comment,
                            }

                            try:
                                response = requests.post(
                                    FEEDBACK_URL,
                                    json=payload,
                                    headers=auth_headers(),
                                    timeout=15,
                                )
                                response.raise_for_status()

                                st.session_state[submitted_key] = True
                                st.success("Thank you for your feedback!")
                                st.rerun()

                            except requests.exceptions.HTTPError as exc:
                                detail = (
                                    exc.response.text
                                    if exc.response is not None
                                    else str(exc)
                                )
                                st.error(
                                    f"Feedback API error: {detail}"
                                )

                            except requests.exceptions.RequestException as exc:
                                st.error(
                                    f"Could not connect to feedback API: {exc}"
                                )


# Accept a new question.
prompt = st.chat_input("Ask your question...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching ShopEase policies..."):
            try:
                payload = {"message": prompt}

                if st.session_state.conversation_id:
                    payload["conversation_id"] = (
                        st.session_state.conversation_id
                    )

                response = requests.post(
                    CHAT_URL,
                    json=payload,
                    headers=auth_headers(),
                    timeout=120,
                )
                response.raise_for_status()
                result = response.json()

                answer = result["answer"]
                sources = result.get("sources", [])
                assistant_message_id = result["assistant_message_id"]

                st.session_state.conversation_id = (
                    result["conversation_id"]
                )

                st.markdown(answer)

                if sources:
                    with st.expander("View sources"):
                        for source in sources:
                            st.write(f"📄 {source}")

                st.session_state.messages.extend(
                    [
                        {
                            "role": "user",
                            "content": prompt,
                            "sources": [],
                        },
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "assistant_message_id": assistant_message_id,
                        },
                    ]
                )

                st.rerun()

            except requests.exceptions.HTTPError as exc:
                response = exc.response
                detail = (
                    response.text
                    if response is not None
                    else str(exc)
                )
                st.error(f"Backend HTTP error: {detail}")

            except requests.exceptions.RequestException as exc:
                st.error(f"Connection error: {exc}")

                    

            except (KeyError, ValueError):
                st.error(
                    "The backend returned an unexpected response. "
                    "Check the FastAPI terminal for errors."
                )
