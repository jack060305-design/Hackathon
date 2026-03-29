from typing import Literal

from fastapi import APIRouter, HTTPException
from google.api_core import exceptions as google_api_exceptions
from pydantic import BaseModel, Field

from ..services import gemini_chat

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=500_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=128)
    county: str | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    """LLM reply for the Streamlit disaster assistant (Gemini)."""
    raw = [m.model_dump() for m in body.messages]
    try:
        reply = gemini_chat.generate_reply(raw, body.county)
        return ChatResponse(reply=reply)
    except google_api_exceptions.ResourceExhausted as e:
        raise HTTPException(
            status_code=429,
            detail="Gemini API quota or rate limit exceeded. Wait a minute, try another model via GEMINI_MODEL, or check billing at https://ai.google.dev/gemini-api/docs/rate-limits",
        ) from e
    except RuntimeError as e:
        if "GEMINI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail=str(e)) from e
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini error: {e!s}") from e
