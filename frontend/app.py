
import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api"
CHAT_URL = f"{API_BASE_URL}/chat"
FEEDBACK_URL = f"{API_BASE_URL}/feedback"

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
                                    timeout=15,
                                )
                                response.raise_for_status()

                                st.session_state[submitted_key] = True
                                st.success("Thank you for your feedback!")
                                st.rerun()

                            except requests.exceptions.RequestException:
                                st.error(
                                    "Could not save feedback. "
                                    "Check that the backend and database "
                                    "are running, then try again."
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

            except requests.exceptions.RequestException:
                st.error(
                    "Unable to contact the backend. "
                    "Check FastAPI, PostgreSQL, and your Gemini configuration."
                )

            except (KeyError, ValueError):
                st.error(
                    "The backend returned an unexpected response. "
                    "Check the FastAPI terminal for errors."
                )
