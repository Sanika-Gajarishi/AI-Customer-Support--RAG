
import os

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def create_gemini_client() -> genai.Client:
    """Create a Gemini API client using the environment key."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to the project's .env file."
        )

    return genai.Client(api_key=api_key)

def generate_answer(prompt: str) -> str:
    """Generate an answer using Gemini."""
    client = create_gemini_client()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    answer = response.text

    if not answer:
        raise RuntimeError("Gemini returned an empty response.")

    return answer.strip()
