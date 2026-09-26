"""Regional Vertex AI Gemini adapter for Google ADK.

Allows running `gemini-3.8-live` (in `us-central1`) and `gemini-3.8-flash` (in `global`)
simultaneously inside the same ADK process without environment variable collisions.

Also upgrades ADK's `GeminiLlmConnection.send_realtime` so that `gemini-3.8-live`
routes `image/jpeg` frames via the `video=` realtime field and `audio/pcm` via `audio=`
instead of legacy `mediaChunks`.
"""

from __future__ import annotations

from functools import cached_property
import os
from typing import Any

import google.auth
from google.adk.models.gemini_llm_connection import GeminiLlmConnection, RealtimeInput
from google.adk.models.google_llm import Gemini, GoogleLLMVariant
from google.adk.utils import model_name_utils
from google.genai import Client, types


def _is_gemini_3_live_model(model_string: str | None) -> bool:
    """Enables ADK's Gemini 3.x Live protocol handling for both 3.1-flash-live and 3.8-live."""
    if not model_string:
        return False
    extracted = model_name_utils.extract_model_name(model_string)
    return extracted.startswith("gemini-3.1-flash-live") or extracted.startswith("gemini-3.8-live")


# Patch ADK's model_name_utils so Gemini 3.8 Live uses Gemini 3.x Live tool-call & realtime input semantics
model_name_utils.is_gemini_3_1_flash_live = _is_gemini_3_live_model  # type: ignore[assignment]


def _resolve_project_id() -> str:
    env_proj = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    if env_proj and env_proj != "your-gcp-project-id":
        return env_proj
    try:
        _, default_proj = google.auth.default()
        if default_proj:
            return default_proj
    except Exception:
        pass
    return "your-gcp-project-id"


PROJECT_ID = _resolve_project_id()


async def _send_realtime_v3(self: GeminiLlmConnection, input: RealtimeInput) -> None:
    """Routes `image/*` blobs to `video=` and `audio/*` blobs to `audio=` for Gemini 3.8 Live."""
    if isinstance(input, types.Blob):
        mime = (input.mime_type or "").lower()
        if mime.startswith("audio/"):
            await self._gemini_session.send_realtime_input(audio=input)
        elif mime.startswith("image/") or mime.startswith("video/"):
            await self._gemini_session.send_realtime_input(video=input)
        else:
            await self._gemini_session.send_realtime_input(media=input)
    elif isinstance(input, types.ActivityStart):
        await self._gemini_session.send_realtime_input(activity_start=input)
    elif isinstance(input, types.ActivityEnd):
        await self._gemini_session.send_realtime_input(activity_end=input)
    else:
        raise ValueError(f"Unsupported input type: {type(input)}")


# Patch ADK's GeminiLlmConnection.send_realtime so Gemini 3.8 Live accepts camera/screen JPEG frames
GeminiLlmConnection.send_realtime = _send_realtime_v3  # type: ignore[method-assign]


class RegionalGemini(Gemini):
    """ADK Gemini LLM wrapper pinned to a specific GCP project and Vertex AI location."""

    project_id: str = PROJECT_ID
    location: str = "us-central1"

    @cached_property
    def api_client(self) -> Client:
        base_url, api_version = self._base_url_and_api_version
        kwargs_for_http_options: dict[str, Any] = {
            "headers": self._tracking_headers(),
            "retry_options": self.retry_options,
            "base_url": base_url,
        }
        if api_version:
            kwargs_for_http_options["api_version"] = api_version

        return Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
            http_options=types.HttpOptions(**kwargs_for_http_options),
        )

    @cached_property
    def _api_backend(self) -> GoogleLLMVariant:
        return GoogleLLMVariant.VERTEX_AI

    @cached_property
    def _live_api_client(self) -> Client:
        base_url, _ = self._base_url_and_api_version
        return Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
            http_options=types.HttpOptions(
                headers=self._tracking_headers(),
                api_version=self._live_api_version,
                base_url=base_url,
            ),
        )


def get_genai_client(location: str = "global") -> Client:
    """Returns a configured Vertex AI GenAI client for the given location."""
    return Client(
        vertexai=True,
        project=PROJECT_ID,
        location=location,
    )
