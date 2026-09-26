"""FastAPI + WebSocket Server for ADK Gemini Live Voicebot Studio.

Supports 3 Live Architectures on Google Cloud Vertex AI:
1. `native_audio`: ADK `Runner.run_live` with `gemini-3.8-live` (us-central1)
   + `gemini-3.8-flash` (global) sub-agent tool.
2. `hybrid_35_38`: ADK `Runner.run_live` with `gemini-3.8-live` (us-central1) for Live ASR
   ➔ ADK `Runner.run_async` with `gemini-3.8-flash` (global) for Reasoning & Tools
   ➔ `gemini-2.5-flash-tts` (us-central1) for 24kHz PCM Neural Audio.
3. `live_transcribe_assist`: `gemini-3.8-live` (us-central1) Live ASR
   + automatic `gemini-3.8-flash` (global) Call Center Agent Assist & Sentiment Card generation.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents import Agent, LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel

from .models_adapter import PROJECT_ID, RegionalGemini, get_genai_client
from .scenarios import ARCHITECTURE_MODES, SCENARIOS
from .tools import ALL_TOOLS, DEMO_STATE, analyze_with_gemini_38_flash

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
DEMO_USER_ACCOUNT = os.getenv("DEMO_USER_ACCOUNT", "demo-user@example.com")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("voicebot_studio")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="ADK Gemini Live Voicebot & Customer Showcase Studio",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class SummaryRequest(BaseModel):
    scenario_id: str = "banking_vip"
    transcript: list[dict[str, Any]] = []


@app.get("/", response_model=None)
async def index(request: Request) -> FileResponse | RedirectResponse:
    host_header = request.headers.get("host", "")
    if host_header.startswith("0.0.0.0"):
        port = host_header.split(":")[1] if ":" in host_header else "8090"
        return RedirectResponse(url=f"http://localhost:{port}/")
    return FileResponse(
        str(STATIC_DIR / "index.html"),
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/api/config")
async def get_config() -> JSONResponse:
    """Returns scenarios, architecture modes, project info, and current live state."""
    return JSONResponse(
        {
            "project_id": PROJECT_ID,
            "account": DEMO_USER_ACCOUNT,
            "models": {
                "native_live": "gemini-3.8-live (us-central1)",
                "transcribe_live": "gemini-3.8-live (us-central1 - Live ASR)",
                "reasoning_flash": "gemini-3.8-flash (global)",
                "tts_flash": "gemini-2.5-flash-tts (us-central1)",
            },
            "architecture_modes": ARCHITECTURE_MODES,
            "scenarios": SCENARIOS,
            "voices": [
                {"id": "Kore", "label": "Kore (Dengeli, Kurumsal & Güven Verici)"},
                {"id": "Aoede", "label": "Aoede (Sıcak, Enerjik & Samimi)"},
                {"id": "Puck", "label": "Puck (Dinamik, Hızlı & Akıcı)"},
                {"id": "Charon", "label": "Charon (Derin, Otoriter & Analitik)"},
                {"id": "Fenrir", "label": "Fenrir (Net, Teknik & Çözüm Odaklı)"},
            ],
            "demo_state": DEMO_STATE,
        }
    )


@app.post("/api/executive-summary")
async def create_executive_summary(req: SummaryRequest) -> JSONResponse:
    """Uses `gemini-3.8-flash` (global) to generate a structured CRM & Executive Call Summary."""
    scenario = SCENARIOS.get(req.scenario_id, SCENARIOS["banking_vip"])
    lines = [f"{item.get('role', 'user').upper()}: {item.get('text', '')}" for item in req.transcript if item.get("text")]
    convo_text = "\n".join(lines) if lines else "Müşteri ile sesli oturum gerçekleştirildi."
    res = await analyze_with_gemini_38_flash(
        analysis_topic=f"{scenario['name']} - Çağrı Sonu Yönetici & CRM Özeti",
        customer_context=convo_text,
        analysis_type="Post-Call CRM & Kalite Özeti",
    )
    return JSONResponse(res)


async def synthesize_pcm_with_gemini_tts(text: str, voice_name: str = "Kore") -> bytes | None:
    """Synthesizes 24kHz 16-bit mono PCM audio using `gemini-2.5-flash-tts`."""
    clean_text = text.strip()
    if not clean_text:
        return None
    client = get_genai_client(location="us-central1")
    for tts_model in ["gemini-2.5-flash-tts"]:
        try:
            res = await client.aio.models.generate_content(
                model=tts_model,
                contents=clean_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    ),
                ),
            )
            for cand in res.candidates or []:
                if cand.content and cand.content.parts:
                    for part in cand.content.parts:
                        if part.inline_data and part.inline_data.data:
                            return part.inline_data.data
        except Exception as exc:
            logger.warning("TTS fallback warning (%s): %s", tts_model, exc)
    return None


def build_native_live_agent(scenario_id: str, voice_name: str) -> Agent:
    """Creates an ADK Agent backed by `gemini-3.8-live` (us-central1)."""
    scenario = SCENARIOS.get(scenario_id, SCENARIOS["banking_vip"])
    llm = RegionalGemini(
        model="gemini-3.8-live",
        location="us-central1",
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
    )
    return Agent(
        name=f"adk_live_{scenario_id}",
        model=llm,
        instruction=scenario["system_instruction"],
        tools=ALL_TOOLS,
    )


def build_transcribe_live_agent() -> Agent:
    """Creates an ADK Agent backed by `gemini-3.8-live` (us-central1) for real-time ASR."""
    llm = RegionalGemini(
        model="gemini-3.8-live",
        location="us-central1",
    )
    return Agent(
        name="adk_transcribe_live_38",
        model=llm,
        instruction="Kullanıcının konuşmasını yüksek doğrulukla gerçek zamanlı dinle.",
    )


def build_gemini_38_flash_agent(scenario_id: str, assist_mode: bool = False) -> Agent:
    """Creates a low-latency ADK Agent backed by `gemini-3.8-flash` (global) with all scenario tools."""
    scenario = SCENARIOS.get(scenario_id, SCENARIOS["banking_vip"])
    extra = ""
    if assist_mode:
        extra = (
            "\nÖNEMLİ: Sen aynı zamanda Çağrı Merkezi Agent Assist modundasın. "
            "Her müşteri cümlesinde mutlaka `analyze_with_gemini_38_flash` aracını veya ilgili iş aracını çağırarak "
            "ekrana canlı kart bas ve müşteriye/temsilciye kısa, net bir yanıt ver."
        )
    llm = RegionalGemini(
        model="gemini-3.8-flash",
        location="global",
    )
    return Agent(
        name=f"adk_flash38_{scenario_id}",
        model=llm,
        instruction=scenario["system_instruction"] + extra,
        tools=ALL_TOOLS,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )


@app.websocket("/ws/live")
async def websocket_live_endpoint(
    websocket: WebSocket,
    scenario_id: str = "banking_vip",
    mode: str = "native_audio",
    voice: str = "Kore",
) -> None:
    """Bidirectional WebSocket endpoint bridging Browser Audio/Vision/Text with Google ADK."""
    await websocket.accept()
    user_id = f"cust_{uuid.uuid4().hex[:6]}"
    scenario = SCENARIOS.get(scenario_id, SCENARIOS["banking_vip"])
    arch = ARCHITECTURE_MODES.get(mode, ARCHITECTURE_MODES["native_audio"])

    await websocket.send_json(
        {
            "type": "session_ready",
            "scenario": scenario,
            "architecture": arch,
            "voice": voice,
            "project_id": PROJECT_ID,
        }
    )

    if mode in ("hybrid_35_38", "live_transcribe_assist"):
        await _handle_hybrid_or_assist_session(websocket, user_id, scenario_id, mode, voice)
    else:
        await _handle_native_audio_session(websocket, user_id, scenario_id, voice)


async def _handle_native_audio_session(
    websocket: WebSocket,
    user_id: str,
    scenario_id: str,
    voice: str,
) -> None:
    """Mode 1: Full-duplex Native Audio via ADK `Runner.run_live` + `gemini-3.8-flash` tool delegation."""
    agent = build_native_live_agent(scenario_id, voice)
    runner = InMemoryRunner(agent=agent, app_name="voicebot_studio_native")
    session = await runner.session_service.create_session(app_name="voicebot_studio_native", user_id=user_id)

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
    )
    live_queue = LiveRequestQueue()

    async def upstream_loop() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                mtype = msg.get("type")

                if mtype == "audio":
                    pcm_bytes = base64.b64decode(msg["data"])
                    live_queue.send_realtime(types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000"))
                elif mtype == "image":
                    img_bytes = base64.b64decode(msg["data"])
                    mime = msg.get("mime_type", "image/jpeg")
                    live_queue.send_realtime(types.Blob(data=img_bytes, mime_type=mime))
                elif mtype == "text":
                    text_val = msg.get("text", "").strip()
                    if text_val:
                        live_queue.send_content(
                            types.Content(role="user", parts=[types.Part.from_text(text=text_val)])
                        )
                elif mtype == "ping":
                    await websocket.send_json({"type": "pong", "ts": msg.get("ts")})
        except WebSocketDisconnect:
            logger.info("Client disconnected from Native Audio session (%s)", user_id)
        except Exception as exc:
            logger.warning("Upstream loop ended: %s", exc)
        finally:
            live_queue.close()

    async def downstream_loop() -> None:
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session.id,
                live_request_queue=live_queue,
                run_config=run_config,
            ):
                if getattr(event, "interrupted", False):
                    await websocket.send_json({"type": "interrupted"})

                in_tr = getattr(event, "input_transcription", None)
                if in_tr and getattr(in_tr, "text", None):
                    await websocket.send_json(
                        {
                            "type": "input_transcription",
                            "text": in_tr.text,
                            "finished": bool(getattr(in_tr, "finished", False)),
                            "model": "gemini-3.8-live",
                        }
                    )

                out_tr = getattr(event, "output_transcription", None)
                if out_tr and getattr(out_tr, "text", None):
                    await websocket.send_json(
                        {
                            "type": "output_transcription",
                            "text": out_tr.text,
                            "finished": bool(getattr(out_tr, "finished", False)),
                            "model": "gemini-3.8-live",
                        }
                    )

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data and part.inline_data.data:
                            mime = part.inline_data.mime_type or ""
                            if "audio" in mime:
                                b64 = base64.b64encode(part.inline_data.data).decode("ascii")
                                await websocket.send_json(
                                    {
                                        "type": "audio",
                                        "data": b64,
                                        "sample_rate": 24000,
                                        "model": "gemini-3.8-live",
                                    }
                                )
                        if part.function_call:
                            await websocket.send_json(
                                {
                                    "type": "tool_call",
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args or {}),
                                    "model": "ADK Live Router",
                                }
                            )
                        if part.function_response:
                            resp_dict = dict(part.function_response.response or {})
                            await websocket.send_json(
                                {
                                    "type": "tool_result",
                                    "name": part.function_response.name,
                                    "response": resp_dict,
                                }
                            )
                            if "ui_widget" in resp_dict:
                                await websocket.send_json(
                                    {
                                        "type": "ui_widget",
                                        "widget": resp_dict["ui_widget"],
                                    }
                                )

                if getattr(event, "turn_complete", False):
                    await websocket.send_json({"type": "turn_complete"})
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Downstream Native Live error: %s", exc)
            try:
                await websocket.send_json({"type": "error", "message": f"Live API Bağlantı Uyarısı: {exc}"})
            except Exception:
                pass

    up_task = asyncio.create_task(upstream_loop())
    down_task = asyncio.create_task(downstream_loop())
    done, pending = await asyncio.wait([up_task, down_task], return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()


async def _handle_hybrid_or_assist_session(
    websocket: WebSocket,
    user_id: str,
    scenario_id: str,
    mode: str,
    voice: str,
) -> None:
    """Modes 2 & 3:
    - Live streaming ASR via ADK `Runner.run_live` using `gemini-3.8-live` (us-central1)
    - Deep Reasoning & Tool execution via ADK `Runner.run_async` using `gemini-3.8-flash` (global)
    - Neural 24kHz PCM Voice synthesis via `gemini-2.5-flash-tts` (us-central1)
    """
    asr_agent = build_transcribe_live_agent()
    asr_runner = InMemoryRunner(agent=asr_agent, app_name="voicebot_studio_asr38")
    asr_session = await asr_runner.session_service.create_session(app_name="voicebot_studio_asr38", user_id=user_id)

    is_assist = mode == "live_transcribe_assist"
    flash38_agent = build_gemini_38_flash_agent(scenario_id, assist_mode=is_assist)
    flash38_runner = InMemoryRunner(agent=flash38_agent, app_name="voicebot_studio_flash38")
    flash38_session = await flash38_runner.session_service.create_session(
        app_name="voicebot_studio_flash38", user_id=user_id
    )

    asr_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
    )
    asr_queue = LiveRequestQueue()
    latest_image_blob: dict[str, Any] = {"data": None, "mime": "image/jpeg"}
    utterance_buffer: list[str] = []

    async def process_with_gemini_38_flash(user_text: str) -> None:
        """Runs `gemini-3.8-flash` ADK agent on the transcribed or typed user message."""
        clean = user_text.strip()
        if not clean:
            return
        t0 = time.perf_counter()
        parts = [types.Part.from_text(text=clean)]
        if latest_image_blob["data"]:
            parts.append(
                types.Part.from_bytes(
                    data=latest_image_blob["data"],
                    mime_type=latest_image_blob["mime"],
                )
            )

        final_text_chunks: list[str] = []
        try:
            async for ev in flash38_runner.run_async(
                user_id=user_id,
                session_id=flash38_session.id,
                new_message=types.Content(role="user", parts=parts),
            ):
                if ev.content and ev.content.parts:
                    for part in ev.content.parts:
                        if part.function_call:
                            await websocket.send_json(
                                {
                                    "type": "tool_call",
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args or {}),
                                    "model": "gemini-3.8-flash",
                                }
                            )
                        if part.function_response:
                            resp_dict = dict(part.function_response.response or {})
                            await websocket.send_json(
                                {
                                    "type": "tool_result",
                                    "name": part.function_response.name,
                                    "response": resp_dict,
                                }
                            )
                            if "ui_widget" in resp_dict:
                                await websocket.send_json(
                                    {
                                        "type": "ui_widget",
                                        "widget": resp_dict["ui_widget"],
                                    }
                                )
                        if part.text:
                            final_text_chunks.append(part.text)
                            await websocket.send_json(
                                {
                                    "type": "output_transcription",
                                    "text": part.text,
                                    "finished": False,
                                    "model": "gemini-3.8-flash",
                                }
                            )

            full_reply = "".join(final_text_chunks).strip()
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if full_reply:
                await websocket.send_json(
                    {
                        "type": "output_transcription",
                        "text": full_reply,
                        "finished": True,
                        "model": f"gemini-3.8-flash ({latency_ms}ms)",
                    }
                )
                pcm_audio = await synthesize_pcm_with_gemini_tts(full_reply, voice_name=voice)
                if pcm_audio:
                    chunk_size = 48000  # 1 second of 24kHz 16-bit mono PCM (~64KB base64 per frame)
                    for offset in range(0, len(pcm_audio), chunk_size):
                        slice_bytes = pcm_audio[offset : offset + chunk_size]
                        b64_audio = base64.b64encode(slice_bytes).decode("ascii")
                        await websocket.send_json(
                            {
                                "type": "audio",
                                "data": b64_audio,
                                "sample_rate": 24000,
                                "model": "gemini-2.5-flash-tts",
                            }
                        )
            await websocket.send_json({"type": "turn_complete"})
        except Exception as exc:
            logger.error("Gemini 3.8 Flash execution error: %s", exc)
            await websocket.send_json({"type": "error", "message": f"Gemini 3.8 Flash Hatası: {exc}"})

    async def upstream_loop() -> None:
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                mtype = msg.get("type")

                if mtype == "audio":
                    pcm_bytes = base64.b64decode(msg["data"])
                    asr_queue.send_realtime(types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000"))
                elif mtype == "image":
                    latest_image_blob["data"] = base64.b64decode(msg["data"])
                    latest_image_blob["mime"] = msg.get("mime_type", "image/jpeg")
                elif mtype == "text":
                    text_val = msg.get("text", "").strip()
                    if text_val:
                        await websocket.send_json(
                            {
                                "type": "input_transcription",
                                "text": text_val,
                                "finished": True,
                                "model": "Kullanıcı Girişi",
                            }
                        )
                        asyncio.create_task(process_with_gemini_38_flash(text_val))
                elif mtype == "ping":
                    await websocket.send_json({"type": "pong", "ts": msg.get("ts")})
        except WebSocketDisconnect:
            logger.info("Client disconnected from Hybrid/AgentAssist session (%s)", user_id)
        except Exception as exc:
            logger.warning("Hybrid upstream loop ended: %s", exc)
        finally:
            asr_queue.close()

    async def downstream_asr_loop() -> None:
        try:
            async for event in asr_runner.run_live(
                user_id=user_id,
                session_id=asr_session.id,
                live_request_queue=asr_queue,
                run_config=asr_config,
            ):
                in_tr = getattr(event, "input_transcription", None)
                if in_tr and getattr(in_tr, "text", None):
                    chunk = in_tr.text
                    is_fin = bool(getattr(in_tr, "finished", False))
                    utterance_buffer.append(chunk)
                    await websocket.send_json(
                        {
                            "type": "input_transcription",
                            "text": chunk,
                            "finished": is_fin,
                            "model": "gemini-3.8-live (ASR)",
                        }
                    )
                    if is_fin:
                        full_user_spoken = " ".join(utterance_buffer).strip()
                        utterance_buffer.clear()
                        if full_user_spoken:
                            asyncio.create_task(process_with_gemini_38_flash(full_user_spoken))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("ASR 3.8 Live error: %s", exc)
            try:
                await websocket.send_json(
                    {"type": "error", "message": f"Gemini 3.8 Live ASR Uyarısı: {exc}"}
                )
            except Exception:
                pass

    up_task = asyncio.create_task(upstream_loop())
    down_task = asyncio.create_task(downstream_asr_loop())
    done, pending = await asyncio.wait([up_task, down_task], return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
