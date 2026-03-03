"""
GaMS3 Subtitle Service - FastAPI Server
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
from pathlib import Path
import tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CONFIG ===
VLLM_BASE = os.getenv("VLLM_URL", "http://localhost:8000")
VLLM_URL = f"{VLLM_BASE}/v1/chat/completions"
MODEL_NAME = "subtitles"
DEFAULT_MAX_CHARS = 70

# === FASTAPI APP ===
app = FastAPI(
    title="GaMS3 Subtitle Service",
    version="1.0.0"
)

class TextRequest(BaseModel):
    text: str
    max_chars: int = DEFAULT_MAX_CHARS
    temperature: float = 0.1

class TextResponse(BaseModel):
    original: str
    subtitle: str
    compression_ratio: float
    chars: int

# === HELPERS ===
def format_prompt(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list:
    instruction = (
        f"Pretvori avtomatski prepis govora v profesionalne podnapise. "
        f"Strni vsebino na največ {max_chars} znakov ali manj.\n\n{text}"
    )
    return [{"role": "user", "content": instruction}]

def call_vllm(text: str, max_chars: int = DEFAULT_MAX_CHARS, temperature: float = 0.1) -> str:
    """Direct call to vLLM API"""
    response = requests.post(
        VLLM_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": "cjvt/GaMS3-12B-Instruct",
            "messages": format_prompt(text, max_chars),
            "max_tokens": 150,
            "temperature": temperature,
            "extra_body": {"lora_modules": ["subtitles"]}
        },
        timeout=30
    )
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

def parse_text_file(content: str) -> list:
    lines = content.split('\n')
    segments = []
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('WEBVTT') and '-->' not in line and not line.startswith('#'):
            segments.append({'index': i + 1, 'text': line})
    return segments

# === ENDPOINTS ===

@app.get("/")
def root():
    return {
        "service": "GaMS3 Subtitle Service",
        "status": "running",
        "vllm_server": VLLM_URL,
        "model": MODEL_NAME,
        "endpoints": ["/transform", "/batch", "/process-file", "/health"]
    }

@app.get("/health")
def health():
    try:
        response = requests.get(f"{VLLM_BASE}/health", timeout=2)
        return {"status": "healthy", "vllm_server": "responsive"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"vLLM error: {e}")

@app.post("/transform", response_model=TextResponse)
def transform(req: TextRequest):
    """Transform single ASR text to subtitle"""
    try:
        subtitle = call_vllm(req.text, req.max_chars, req.temperature)
        logger.info(f"✓ '{req.text[:40]}...' → '{subtitle[:40]}...'")
        return TextResponse(
            original=req.text,
            subtitle=subtitle,
            compression_ratio=len(subtitle) / len(req.text) if req.text else 0,
            chars=len(subtitle)
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch")
def batch_transform(items: list[str], max_chars: int = DEFAULT_MAX_CHARS, temperature: float = 0.1):
    """Batch transform multiple texts"""
    try:
        results = []
        for text in items:
            subtitle = call_vllm(text, max_chars, temperature)
            results.append({
                "original": text,
                "subtitle": subtitle,
                "compression_ratio": len(subtitle) / len(text) if text else 0
            })
        logger.info(f"✓ Batch: {len(items)} items")
        return {"total_items": len(items), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-file")
async def process_file(file: UploadFile = File(...), max_chars: int = DEFAULT_MAX_CHARS):
    """Process text file"""
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        segments = parse_text_file(text_content)

        if not segments:
            raise HTTPException(400, "No text found")

        logger.info(f"Processing: {file.filename} ({len(segments)} segments)")

        output_lines = []
        for i, seg in enumerate(segments, 1):
            logger.info(f"[{i}/{len(segments)}] Processing segment...")
            subtitle = call_vllm(seg['text'], max_chars)
            output_lines.append(f"INPUT:  {seg['text']}")
            output_lines.append(f"OUTPUT: {subtitle}")
            output_lines.append("")

        output_content = '\n'.join(output_lines)
        output_path = Path(tempfile.mktemp(suffix='.txt'))
        output_path.write_text(output_content, encoding='utf-8')

        logger.info(f"✓ Done: {len(segments)} segments")

        return FileResponse(
            output_path,
            media_type='text/plain',
            filename=f'subtitles_{file.filename}'
        )
    except Exception as e:
        logger.error(f"File processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
