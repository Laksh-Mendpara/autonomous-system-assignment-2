# Docker Setup for Local Quantized 8B Models

This directory provides production-ready Docker deployment options for hosting quantized 8B open-weights chat models on a **16GB RAM laptop**.

---

## 🚀 Quick Start: Option 1 (Recommended — Ollama in Docker)

Ollama is the easiest way to run quantized models with dynamic memory management.

### Method A: Single Command via Bash Script
```bash
# Starts the Ollama container and pulls llama3.1:8b (4-bit Q4_K_M ~4.7GB)
./docker/run_ollama.sh

# Or run Qwen 2.5 7B instead:
./docker/run_ollama.sh qwen2.5:7b
```

### Method B: Via Docker Compose
```bash
# Launches both Ollama and the automated model puller:
docker compose -f docker/docker-compose.yml up -d
```

### Verification
Check that Ollama is serving the model on port 11434:
```bash
curl http://localhost:11434/api/tags
```

---

## ⚡ Option 2: llama.cpp OpenAI-Compatible Server in Docker

If you prefer pure GGUF execution with llama.cpp:

```bash
# Downloads Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf and starts port 8080:
./docker/run_llama_cpp.sh
```

---

## 💬 Connecting with Academic Helpdesk

Once either container is running, the Academic Helpdesk automatically connects via LiteLLM:

```bash
# 1. With Ollama (Port 11434):
export HELP_DESK_MODEL="ollama/llama3.1:8b"
export OLLAMA_API_BASE="http://localhost:11434"

.venv/bin/python chatbot.py
```

The chatbot startup banner will immediately show:
```text
● LLM Backend: Connected to Ollama (ollama/llama3.1:8b) @ http://localhost:11434
```

---

## 📊 RAM Consumption Profile (16GB RAM Target)

| Model Name | Quantization | Disk / VRAM Size | Active RAM Consumption | System Headroom Remaining |
| :--- | :--- | :--- | :--- | :--- |
| **Llama 3.1 8B Instruct** | 4-bit (`Q4_K_M`) | 4.7 GB | $\approx$5.2 GB | $\approx$10.8 GB (Safe) |
| **Qwen 2.5 7B Instruct** | 4-bit (`Q4_K_M`) | 4.4 GB | $\approx$4.8 GB | $\approx$11.2 GB (Safe) |
| **Vector DB (ChromaDB)** | N/A | 14 MB (SQLite) | $\approx$0.2 GB | N/A |
| **Embedder (all-MiniLM)**| FP32 | 80 MB | $\approx$0.3 GB | N/A |

