# GaMS3 Subtitle Service


A subtitle compression service powered by vLLM and FastAPI. Takes raw spoken text and transforms it into subtitle-ready format.

## Prerequisites
Before starting, make sure you have the following installed:

- Docker (Docker Engine or Docker Desktop)
- NVIDIA Container Toolkit — required for GPU access inside containers
- An NVIDIA GPU with at least 16 GB VRAM (e.g. RTX 3090, RTX 4090, A100)

You are going to use:
- Base model: cjvt/GaMS3-12B-Instruct
- LoRA adapters which:
    - have masking that prevents leaking of instruction, also does not add puntuation and capitalization: alenkaz/GaMS3-12b-Subtitle-Generator-SI  
    - have no masking, therefore adds punctuation and capitalization, sometimes leaks chat-reponses: alenkaz/GaMS3-12B-subtitles-offline   
- Loaded with bfloat16 — requires from ~32 GB VRAM

### Verify Docker can see your GPU before proceeding:
bash docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
If this prints your GPU info, you are ready to go.

Ports
The following ports must be free on your machine before running:
PortService8000vLLM server8001FastAPI (subtitle API)
If either port is already in use, edit docker-compose.yml and change the left side of the port mapping (e.g. "8002:8001").

## Setup & Launch

1. Clone the repository:
bash git clone <repository-url>
cd gams3-docker-deployment

2. Build and start all services:
bash docker compose up --build
This builds both Docker images and starts the vllm and api containers.

-- Note: On first run, both the base model (cjvt/GaMS3-12B-Instruct) and the LoRA
adapter (alenkaz/GaMS3-12B-subtitles-offline) will be downloaded from HuggingFace
automatically. This can take 10–30 minutes depending on your connection. Subsequent
starts are fast because both are cached in a Docker volume (huggingface_cache).

3. Wait until both services are healthy.
You will see logs from both containers in the terminal. Wait until you see something like:
gams3-vllm-subs-offline  | INFO:     Application startup complete.
gams3-api                | INFO:     Application startup complete.

5. Verify both services are running:
bash# vLLM server — should return {"status":"ok"}
curl http://localhost:8000/health

Subtitle API — should return {"status":"ok"}
curl http://localhost:8001/health

## Testing
Once both containers are healthy, open a new terminal and run the CLI tester:
bash python api/fastapi_wrapper.py

Important: docker compose up must already be running in another terminal before
you launch this script. The script connects to the API at localhost:8001 — if the
containers are not running, it will fail with a connection error.

Choose option 1 to test a single text, or 4 to check vLLM server health.
You can also call the API directly:
bash curl -X POST http://localhost:8001/transform \
  -H "Content-Type: application/json" \
  -d '{"text": "um ja res je že prav pomladno danes le veter je še kar hladen}'

## Stopping the Service
bash docker compose down
To also delete the downloaded model cache (frees disk space, but next start will re-download):
bash docker compose down -v

### Repository Structure

```text
gams3-docker-deployment/
├── api/
│   ├── Dockerfile
│   ├── fastapi_wrapper.py     # CLI tester + FastAPI server
│   └── requirements.txt
├── vllm/
│   └── Dockerfile             # vLLM server with the subtitle model
├── docker-compose.yml
└── README.md
```

### Troubleshooting

- Connection error: host 'vllm' not found
This happens when fastapi_wrapper.py is run without the Docker stack running first.
Always start with docker compose up before running the CLI tester.

- Port already in use
If port 8000 or 8001 is occupied, edit docker-compose.yml:
yamlports:
  - "8002:8000"   # change left side only

- Container crashes on startup / model fails to load
Check available VRAM with nvidia-smi. If VRAM is insufficient, the vLLM container will exit.
Inspect the logs with:
bash docker logs gams3-vllm-subs-offline

- Slow first startup
The model is downloaded on first run and cached. This is normal — subsequent starts will be fast.
