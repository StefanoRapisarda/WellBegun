"""Ollama LLM wrapper — generate, stream, health check."""

from collections.abc import AsyncIterator
import json

import httpx

from wellbegun.config import settings


class OllamaUnavailableError(Exception):
    """Raised when Ollama is not reachable."""


# ---------------------------------------------------------------------------
# Runtime model override (avoids mutating pydantic settings)
# ---------------------------------------------------------------------------

_model_override: str | None = None


def get_active_model() -> str:
    return _model_override or settings.llm_model


def set_active_model(model: str) -> None:
    global _model_override
    _model_override = model


async def list_models() -> list[dict]:
    """Call Ollama GET /api/tags to list available models."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{settings.llm_base_url}/api/tags")
        r.raise_for_status()
        return [
            {"name": m["name"], "size": m.get("size", 0)}
            for m in r.json().get("models", [])
        ]


async def check_health() -> bool:
    """Return True if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.llm_base_url}/api/tags")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


async def generate(prompt: str, system: str = "", temperature: float | None = None) -> str:
    """Single-shot generation. Returns full response text."""
    payload: dict = {
        "model": get_active_model(),
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.llm_base_url}/api/generate",
                json=payload,
            )
            r.raise_for_status()
            return r.json()["response"]
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(f"Ollama request failed: {exc}") from exc


async def stream_generate(prompt: str, system: str = "") -> AsyncIterator[str]:
    """Streaming generation. Yields tokens as they arrive."""
    payload: dict = {
        "model": get_active_model(),
        "prompt": prompt,
        "stream": True,
    }
    if system:
        payload["system"] = system
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(f"Ollama stream failed: {exc}") from exc
