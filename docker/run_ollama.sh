#!/usr/bin/env bash
# ==============================================================================
# run_ollama.sh — Start Ollama in Docker and Pull Quantized 8B Chat Model
#
# Optimized for 16GB RAM laptop:
#   - Model: llama3.1:8b (4-bit Q4_K_M quantization ~4.7 GB)
#   - Alternative: qwen2.5:7b (4-bit Q4_K_M quantization ~4.4 GB)
#   - RAM Footprint: ~5.2 GB active RAM, leaves >10 GB for system & vector search
# ==============================================================================

set -e

MODEL_NAME="${1:-llama3.1:8b}"
CONTAINER_NAME="academic-ollama"
PORT="11434"

echo "======================================================================"
echo "  Starting Ollama Docker Container for IIT Jodhpur Helpdesk"
echo "  Target Model: ${MODEL_NAME} (Quantized 8B / 4-bit)"
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

# 2. Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "[*] Existing container '${CONTAINER_NAME}' found."
    if ! docker ps --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
        echo "[*] Starting existing container..."
        docker start "${CONTAINER_NAME}"
    else
        echo "[+] Container '${CONTAINER_NAME}' is already running."
    fi
else
    echo "[*] Creating and starting '${CONTAINER_NAME}' container..."
    docker run -d \
        --name "${CONTAINER_NAME}" \
        -p "${PORT}:11434" \
        -v academic_ollama_models:/root/.ollama \
        --restart unless-stopped \
        --memory="8g" \
        ollama/ollama:latest
fi

# 3. Wait for Ollama service to become healthy
echo "[*] Waiting for Ollama API to respond on http://localhost:${PORT}..."
MAX_RETRIES=20
COUNT=0
until curl -s "http://localhost:${PORT}/api/tags" >/dev/null 2>&1; do
    sleep 2
    COUNT=$((COUNT + 1))
    if [ ${COUNT} -ge ${MAX_RETRIES} ]; then
        echo "[-] Timeout waiting for Ollama container."
        docker logs --tail 30 "${CONTAINER_NAME}"
        exit 1
    fi
done
echo "[+] Ollama API is active and reachable!"

# 4. Pull the quantized 8B model if not present
echo "[*] Checking if model '${MODEL_NAME}' is installed..."
if curl -s "http://localhost:${PORT}/api/tags" | grep -q "\"${MODEL_NAME}\""; then
    echo "[+] Model '${MODEL_NAME}' is already cached and available."
else
    echo "[*] Pulling model '${MODEL_NAME}' (4-bit quantized, ~4.7GB)..."
    docker exec -it "${CONTAINER_NAME}" ollama pull "${MODEL_NAME}"
fi

# 5. Quick verification inference
echo "[*] Verifying model response..."
TEST_RESP=$(curl -s "http://localhost:${PORT}/api/generate" -d "{
    \"model\": \"${MODEL_NAME}\",
    \"prompt\": \"Respond with 'READY' if you are online.\",
    \"stream\": false
}" | grep -o '"response":"[^"]*"' || true)

echo "[+] Verification output: ${TEST_RESP}"
echo "======================================================================"
echo "  Ollama 8B model is ready on http://localhost:${PORT}!"
echo ""
echo "  To test with the Academic Helpdesk terminal chatbot:"
echo "    .venv/bin/python chatbot.py"
echo "======================================================================"

