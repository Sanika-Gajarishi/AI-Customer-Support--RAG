import os
import requests
import streamlit as st
import streamlit.components.v1 as components

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_ROOT = f"{API_BASE_URL}/api"
AUTH_URL = f"{API_ROOT}/auth"

SUGGESTED_QUESTIONS = [
    "Can I return a product after 20 days?",
    "How long does a refund take?",
    "What are the shipping options?",
    "Can I cancel my order?",
    "Is my product covered by warranty?",
]

st.set_page_config(page_title="ShopEase AI Support", page_icon="💬", layout="wide")

DEFAULTS = {
    "access_token": None, "current_user": None, "conversation_id": None,
    "messages": [], "page": "Customer Chat", "auth_mode": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def auth_headers():
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(method, endpoint, *, authenticated=True, **kwargs):
    headers = kwargs.pop("headers", {})
    if authenticated:
        headers.update(auth_headers())
    try:
        return requests.request(
            method, f"{API_ROOT}{endpoint}", headers=headers, timeout=120, **kwargs
        )
    except requests.RequestException:
        st.error("Cannot connect to the backend. Check that FastAPI is running.")
        return None


def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def scroll_to_top_after_login():
    if st.session_state.pop("scroll_to_top_on_login", False):
        components.html(
            """
            <script>
            const scrollToTop = () => {
                const main = window.parent.document.querySelector(
                    'section[data-testid="stMain"], section.main'
                );
                if (main) {
                    main.scrollTop = 0;
                    main.scrollTo(0, 0);
                }
                window.parent.scrollTo(0, 0);
            };
            requestAnimationFrame(scrollToTop);
            setTimeout(scrollToTop, 150);
            setTimeout(scrollToTop, 400);
            </script>
            """,
            height=0,
        )


def start_new_chat():
    st.session_state.conversation_id = None
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hello! I'm the ShopEase support assistant. How can I help you today?",
        "sources": [],
    }]


def render_suggested_questions(*, admin_dashboard=False):
    """Show clickable sample questions in both customer and administrator views."""
    st.markdown("### How can we help you?")
    st.caption("Choose a sample question or type your own message below.")
    columns = st.columns(2)
    for index, question in enumerate(SUGGESTED_QUESTIONS):
        with columns[index % 2]:
            if st.button(
                f"💬 {question}",
                key=f"{'admin' if admin_dashboard else 'customer'}_suggestion_{index}",
                use_container_width=True,
            ):
                st.session_state["suggested_prompt"] = question
                if admin_dashboard:
                    st.session_state["main_navigation"] = "Customer Chat"
                st.rerun()


def show_authentication():
    # Welcome page with three clear paths: customer login, registration, admin portal.
    st.title("🛍️ ShopEase")
    st.subheader("AI-powered customer support")
    st.write(
        "Get help with returns, refunds, shipping, cancellations, and product policies."
    )

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = None

    if st.session_state.auth_mode is None:
        st.write("")
        # Keep the three welcome cards visually aligned and use the same primary
        # button style for every entry point.
        st.markdown(
            """
            <style>
            .welcome-card-description {
                min-height: 76px;
                display: flex;
                align-items: flex-start;
                line-height: 1.55;
                padding-top: 2px;
            }
            div[data-testid="stHorizontalBlock"] div[data-testid="column"] {
                min-width: 0;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3, gap="large")

        with col1:
            st.subheader("💬 Customer Login")
            st.markdown(
                '<div class="welcome-card-description">Already have an account? '
                'Sign in and chat with our AI assistant.</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Customer Login", use_container_width=True, type="primary",
                key="welcome_customer_login",
            ):
                st.session_state.auth_mode = "Customer Login"
                st.rerun()

        with col2:
            st.subheader("👤 New Customer")
            st.markdown(
                '<div class="welcome-card-description">Create an account to '
                'start using ShopEase support.</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Create Account", use_container_width=True, type="primary",
                key="welcome_create_account",
            ):
                st.session_state.auth_mode = "Register"
                st.rerun()

        with col3:
            st.subheader("🛡️ Admin Portal")
            st.markdown(
                '<div class="welcome-card-description">Authorized administrators '
                'can manage policies and monitor activity.</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Admin Login", use_container_width=True, type="primary",
                key="welcome_admin_login",
            ):
                st.session_state.auth_mode = "Admin Login"
                st.rerun()

        st.divider()
        st.caption("ShopEase Support · Secure account access · AI-powered assistance")
        return

    auth_mode = st.session_state.auth_mode
    if auth_mode == "Register":
        st.title("Create a Customer Account")
        st.caption("Register with your email address and a strong password.")
    elif auth_mode == "Admin Login":
        st.title("🛡️ Administrator Login")
        st.caption("This portal is restricted to authorized administrator accounts.")
    else:
        st.title("💬 Customer Login")
        st.caption("Sign in to continue to ShopEase AI Support.")

    with st.form("authentication_form"):
        email = st.text_input("Email address").strip().lower()
        password = st.text_input("Password", type="password")
        if auth_mode == "Register":
            st.caption("Use a password between 8 and 128 characters.")
        submitted = st.form_submit_button(
            "Create Account" if auth_mode == "Register" else "Log In",
            type="primary",
            use_container_width=True,
        )

    if st.button("← Back to welcome page"):
        st.session_state.auth_mode = None
        st.rerun()

    if not submitted:
        return
    if not email or not password:
        st.error("Enter your email address and password.")
        return

    if auth_mode == "Register":
        response = api_request(
            "POST", "/auth/register", authenticated=False,
            json={"email": email, "password": password},
        )
        if response is None:
            return
        if response.status_code in (200, 201):
            st.success("Account created. Return to the welcome page and choose Customer Login.")
            st.session_state.auth_mode = None
        else:
            try:
                st.error(response.json().get("detail", "Registration failed."))
            except ValueError:
                st.error("Registration failed.")
        return

    response = api_request(
        "POST", "/auth/login", authenticated=False,
        json={"email": email, "password": password},
    )
    if response is None:
        return
    if not response.ok:
        try:
            st.error(response.json().get("detail", "Login failed."))
        except ValueError:
            st.error("Login failed.")
        return

    try:
        token = response.json()["access_token"]
        profile_response = requests.get(
            f"{AUTH_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
    except (requests.RequestException, KeyError, ValueError):
        st.error("Login succeeded, but the account profile could not be verified.")
        return

    # Use the role returned by FastAPI, not the page the user selected.
    is_admin = profile.get("is_admin") is True

    if auth_mode == "Admin Login" and not is_admin:
        st.error("Access denied. This account is not an administrator.")
        return

    if auth_mode == "Customer Login" and is_admin:
        st.error("This is an administrator account. Please use Admin Login.")
        return

    # Normalize the role to a strict boolean before storing it in the UI session.
    profile["is_admin"] = is_admin

    st.session_state.access_token = token
    st.session_state.current_user = profile
    st.session_state.conversation_id = None
    st.session_state.messages = []
    st.session_state.auth_mode = None
    st.session_state.scroll_to_top_on_login = True
    st.rerun()


def render_customer_chat():
    st.title("🛍️ ShopEase Support")
    st.caption(
        "Ask questions about returns, refunds, shipping, cancellations, and warranties."
    )
    render_suggested_questions()
    if not st.session_state.messages:
        start_new_chat()

    with st.sidebar:
        st.subheader("Account")
        st.caption(st.session_state.current_user["email"])
        if st.session_state.current_user.get("is_admin"):
            st.success("Administrator account")
        if st.button("Log out", key="customer_logout", use_container_width=True):
            logout()
            st.rerun()
        st.divider()
        st.subheader("Conversation")
        if st.session_state.conversation_id:
            st.caption(f"ID: {st.session_state.conversation_id}")
        if st.button("Start new chat", use_container_width=True):
            start_new_chat()
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("View sources"):
                    for source in message["sources"]:
                        st.write(f"📄 {source}")
            message_id = message.get("assistant_message_id")
            if message["role"] == "assistant" and message_id:
                submitted_key = f"feedback_submitted_{message_id}"
                if st.session_state.get(submitted_key, False):
                    st.caption("✓ Feedback submitted. Thank you!")
                else:
                    with st.expander("Was this answer helpful?"):
                        choice = st.selectbox(
                            "Rate this answer",
                            ["Select a rating", "Helpful", "Not helpful"],
                            key=f"feedback_choice_{message_id}",
                        )
                        comment = st.text_input(
                            "Optional comment", max_chars=1000,
                            key=f"feedback_comment_{message_id}",
                        )
                        if st.button(
                            "Submit feedback", key=f"submit_feedback_{message_id}"
                        ):
                            if choice == "Select a rating":
                                st.warning("Please select a rating first.")
                            else:
                                feedback_response = api_request(
                                    "POST", "/feedback",
                                    json={
                                        "message_id": message_id,
                                        "is_helpful": choice == "Helpful",
                                        "comment": comment,
                                    },
                                )
                                if feedback_response is not None:
                                    if feedback_response.ok:
                                        st.session_state[submitted_key] = True
                                        st.success("Thank you for your feedback!")
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Feedback failed "
                                            f"({feedback_response.status_code}): "
                                            f"{feedback_response.text[:300]}"
                                        )

    prompt = st.chat_input("Ask your question...")
    suggested_prompt = st.session_state.pop("suggested_prompt", None)
    if suggested_prompt:
        prompt = suggested_prompt
    if prompt:
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "sources": []}
        )
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Searching ShopEase policies..."):
                payload = {"message": prompt}
                if st.session_state.conversation_id:
                    payload["conversation_id"] = st.session_state.conversation_id
                response = api_request("POST", "/chat", json=payload)
                if response is None:
                    st.error("Could not reach the backend.")
                elif not response.ok:
                    st.error(
                        f"Backend error ({response.status_code}): "
                        f"{response.text[:500]}"
                    )
                else:
                    try:
                        result = response.json()
                        answer = result["answer"]
                        sources = result.get("sources", [])
                        st.session_state.conversation_id = result["conversation_id"]
                        st.markdown(answer)
                        if sources:
                            with st.expander("View sources"):
                                for source in sources:
                                    st.write(f"📄 {source}")
                        st.session_state.messages.append({
                            "role": "assistant", "content": answer,
                            "sources": sources,
                            "assistant_message_id": result.get("assistant_message_id"),
                        })
                        st.rerun()
                    except (KeyError, ValueError):
                        st.error(
                            "Unexpected backend response. Check the FastAPI terminal."
                        )


def render_admin_dashboard():
    user = st.session_state.current_user
    if not isinstance(user, dict) or user.get("is_admin") is not True:
        st.error("Access denied. This page is only available to administrators.")
        return

    st.title("🛍️ ShopEase Admin Dashboard")
    st.caption("Manage customer-support policies and monitor system activity.")
    with st.sidebar:
        st.subheader("Administrator")
        st.write(user["email"])
        if st.button("Log out", key="admin_logout", use_container_width=True):
            logout()
            st.rerun()

    st.header("System Overview")
    summary_response = api_request("GET", "/admin/summary")
    if summary_response is not None:
        if summary_response.status_code == 200:
            summary = summary_response.json()
            cols = st.columns(3)
            cols[0].metric("Users", summary.get("total_users", 0))
            cols[1].metric("Conversations", summary.get("total_conversations", 0))
            cols[2].metric("Messages", summary.get("total_messages", 0))
            cols = st.columns(3)
            cols[0].metric("Feedback", summary.get("total_feedback", 0))
            cols[1].metric("Helpful", summary.get("helpful_feedback", 0))
            cols[2].metric("Unhelpful", summary.get("unhelpful_feedback", 0))
        elif summary_response.status_code in (401, 403):
            st.error("Your session is invalid or lacks admin access.")
        else:
            st.error(f"Could not load summary: {summary_response.status_code}")

    st.divider()
    st.header("Policy Document Management")
    st.write("Supported formats: TXT and PDF. Maximum upload size: 10 MB.")
    uploaded_file = st.file_uploader(
        "Upload a policy document", type=["txt", "pdf"], key="admin_upload"
    )
    if uploaded_file is not None and st.button(
        "Upload document", type="primary", key="admin_upload_button"
    ):
        response = api_request(
            "POST", "/admin/documents/upload",
            files={"file": (
                uploaded_file.name, uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )},
        )
        if response is not None:
            if response.status_code == 201:
                st.success("Document uploaded successfully.")
                st.rerun()
            else:
                st.error(f"Upload failed ({response.status_code}): {response.text[:300]}")

    documents_response = api_request("GET", "/admin/documents")
    if documents_response is not None:
        if documents_response.status_code == 200:
            documents = documents_response.json().get("documents", [])
            st.subheader(f"Available policy documents ({len(documents)})")
            if not documents:
                st.info("No policy documents found.")
            for document in documents:
                filename = document["filename"]
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{filename}**")
                        st.caption(
                            f"Format: {document.get('extension', '')} · "
                            f"Size: {document.get('size_bytes', 0):,} bytes"
                        )
                    with col2:
                        confirm_key = f"confirm_delete_{filename}"
                        if st.button("Delete", key=f"delete_{filename}"):
                            st.session_state[confirm_key] = True
                        if st.session_state.get(confirm_key, False):
                            st.warning(
                                f"Delete {filename}? Rebuild the knowledge base "
                                "after changing documents."
                            )
                            if st.button(
                                "Confirm deletion", key=f"confirm_{filename}",
                                type="primary",
                            ):
                                delete_response = api_request(
                                    "DELETE", "/admin/documents/"
                                    + requests.utils.quote(filename, safe=""),
                                )
                                if delete_response is not None:
                                    if delete_response.status_code == 200:
                                        st.success("Document deleted.")
                                        st.session_state.pop(confirm_key, None)
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"Delete failed: {delete_response.text[:300]}"
                                        )
                            if st.button("Cancel", key=f"cancel_{filename}"):
                                st.session_state.pop(confirm_key, None)
                                st.rerun()
        elif documents_response.status_code in (401, 403):
            st.error("Admin authorization failed.")
        else:
            st.error(f"Could not load documents: {documents_response.status_code}")

    st.divider()
    st.header("Knowledge Base")
    st.write(
        "Rebuild the FAISS index after uploading or deleting policy documents. "
        "Rebuilding processes all available documents."
    )
    st.warning("Check that policy documents are complete and correct before rebuilding.")
    if st.button("Rebuild Knowledge Base", type="primary"):
        with st.spinner("Rebuilding the knowledge base. This may take a while..."):
            response = api_request("POST", "/admin/rebuild-knowledge-base")
        if response is not None:
            if response.status_code == 200:
                result = response.json()
                st.success(result.get("message", "Rebuild completed."))
                st.metric("Indexed chunks", result.get("indexed_chunks", 0))
            elif response.status_code in (401, 403):
                st.error("Admin authorization failed.")
            else:
                st.error(
                    f"Rebuild failed ({response.status_code}). "
                    "Check the backend terminal for details."
                )


if not st.session_state.access_token or not st.session_state.current_user:
    show_authentication()
    st.stop()

# Strict role-based navigation: ordinary customers never receive an admin menu.
current_user = st.session_state.current_user
is_admin = isinstance(current_user, dict) and current_user.get("is_admin") is True

if is_admin:
    # Administrators see only administration tools; the customer chatbot is a
    # separate customer-facing experience and is not available in this session.
    st.session_state.pop("main_navigation", None)
    render_admin_dashboard()
else:
    # Customers see only the chatbot, never administration tools.
    st.session_state.pop("main_navigation", None)
    render_customer_chat()

scroll_to_top_after_login()
