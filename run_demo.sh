#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load local .env if present (gitignored)
if [ -f ".env" ]; then
  set -a
  source ".env"
  set +a
fi

export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-TRUE}"
if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-gcp-project-id" ]; then
  DETECTED_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  export GOOGLE_CLOUD_PROJECT="${DETECTED_PROJECT:-your-gcp-project-id}"
fi
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif [ -x "../env-genai/bin/python" ]; then
  PYTHON_BIN="../env-genai/bin/python"
else
  PYTHON_BIN="python3"
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8090}"
echo "=================================================================="
echo "✦ Google ADK × Gemini Live Voicebot Studio Başlatılıyor..."
echo "  Proje    : $GOOGLE_CLOUD_PROJECT"
echo "  Tarayıcı : http://localhost:$PORT"
echo "=================================================================="

exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
