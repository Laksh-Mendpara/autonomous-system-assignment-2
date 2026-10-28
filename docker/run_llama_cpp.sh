#!/usr/bin/env bash
# ==============================================================================
# run_llama_cpp.sh — Run llama.cpp OpenAI-Compatible Server in Docker
#
# Optimized for 16GB RAM laptop:
#   - Model: Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf (~4.9 GB)
#   - Context Window: 4096 tokens
#   - Threads: 4 CPU threads
#   - API Endpoint: http://localhost:8080/v1 (OpenAI compatible)
# ==============================================================================

set -e

CONTAINER_NAME="academic-llama-cpp"
PORT="8080"
MODEL_DIR="$(pwd)/docker/models"
MODEL_NAME="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
MODEL_PATH="${MODEL_DIR}/${MODEL_NAME}"
MODEL_URL="https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

echo "======================================================================"
echo "  Starting llama.cpp Server Container for IIT Jodhpur Helpdesk"
echo "  Target GGUF: ${MODEL_NAME} (Q4_K_M Quantized)"
echo "======================================================================"

# 1. Check if Docker daemon is accessible
if ! docker info >/dev/null 2>&1; then
    echo "[-] Error: Docker daemon is not accessible."
    echo "    Please start the Docker service with:"
    echo "      sudo systemctl start docker"
    echo "    Or run dockerd in the background:"
    echo "      sudo dockerd > /tmp/dockerd.log 2>&1 &"
    exit 1
fi

mkdir -p "${MODEL_DIR}"

# 2. Download quantized GGUF if not already present
if [ ! -f "${MODEL_PATH}" ]; then
    echo "[*] Model file not found at ${MODEL_PATH}."
    echo "[*] Downloading ${MODEL_NAME} (~4.9GB)..."
    curl -L -C - --progress-bar -o "${MODEL_PATH}" "${MODEL_URL}"
else
    echo "[+] Found existing GGUF model at ${MODEL_PATH}"
fi

# 3. Stop old container if running
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "[*] Stopping previous ${CONTAINER_NAME} container..."
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

# 4. Start llama.cpp server container
echo "[*] Starting llama.cpp server on port ${PORT}..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    -p "${PORT}:8080" \
    -v "${MODEL_DIR}:/models:ro" \
    --restart unless-stopped \
    --memory="8g" \
    ghcr.io/ggerganov/llama.cpp:server \
    -m "/models/${MODEL_NAME}" \
    --host 0.0.0.0 \
    --port 8080 \
    -c 4096 \
    -t 4

echo "[+] llama.cpp container started."
echo "[*] Waiting for server on http://localhost:${PORT}/v1/models..."
until curl -s "http://localhost:${PORT}/v1/models" >/dev/null 2>&1; do
    sleep 2
done

echo "======================================================================"
echo "  llama.cpp server is ready on http://localhost:${PORT}/v1!"
echo ""
echo "  Configure Academic Helpdesk with:"
echo "    export HELP_DESK_MODEL=\"openai/llama-3.1-8b-instruct\""
echo "    export LLAMA_CPP_API_BASE=\"http://localhost:${PORT}/v1\""
echo "    .venv/bin/python chatbot.py"
echo "======================================================================"

