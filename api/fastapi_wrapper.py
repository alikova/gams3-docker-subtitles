"""
FastAPI Complete - All endpoints
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
VLLM_BASE = os.getenv("VLLM_URL", "http://vllm:8000")  
VLLM_URL = f"{VLLM_BASE}/v1/chat/completions"
MODEL_NAME = "subtitles"
DEFAULT_MAX_CHARS = 70

# === FASTAPI APP ===
app = FastAPI(
    title="GaMS3 Subtitle Service - Complete",
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
def format_prompt(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    return f"Pretvori avtomatski prepis govora v profesionalne podnapise. Strni vsebino na največ {max_chars} znakov ali manj.\n\n{text}"

def call_vllm(text: str, max_chars: int = DEFAULT_MAX_CHARS, temperature: float = 0.1) -> str:
    """Direct call to vLLM API"""
    
    prompt = format_prompt(text, max_chars)
    
    response = requests.post(
        VLLM_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": temperature
        },
        timeout=30
    )
    
    result = response.json()
    subtitle = result['choices'][0]['message']['content'].strip()
    
    return subtitle

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

while True:
    print("\n" + "=" * 50)
    print(" GaMS3 Subtitle Service - CLI Tester")
    print("=" * 50)
    print("This tool lets you test the subtitle model locally.\n")
    
    print("Please choose an option:")
    print("  1  → Transform a single text")
    print("  2  → Transform multiple texts (batch mode)")
    print("  3  → Process a subtitle file (.txt or .vtt)")
    print("  4  → Check vLLM server health")
    print("  0  → Exit")
    
    choice = input("\nEnter your choice (0–4): ").strip()

    if choice == "1":
        print("\n--- Single Text Transformation ---")
        print("Enter the text you want to compress into subtitle format.")
        text = input("\nText: ").strip()

        if not text:
            print("No text entered.")
            continue

        print("\nProcessing...\n")
        subtitle = call_vllm(text)

        print("Result:")
        print("-" * 40)
        print(subtitle)
        print("-" * 40)

    elif choice == "2":
        print("\n--- Batch Mode ---")
        print("Enter multiple lines of text.")
        print("Press ENTER on an empty line to start processing.\n")

        items = []
        while True:
            line = input("> ").strip()
            if not line:
                break
            items.append(line)

        if not items:
            print("No input provided.")
            continue

        print(f"\nProcessing {len(items)} items...\n")

        for i, text in enumerate(items, 1):
            subtitle = call_vllm(text)
            print(f"[{i}] INPUT : {text}")
            print(f"    OUTPUT: {subtitle}\n")

    elif choice == "3":
        print("\n--- File Processing ---")
        print("Supported formats: .txt or .vtt")
        file_path = input("Enter full file path: ").strip()

        if not os.path.exists(file_path):
            print("File not found.")
            continue

        print("\nReading file...\n")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        segments = parse_text_file(content)

        if not segments:
            print("No valid text segments found.")
            continue

        print(f"Found {len(segments)} segments.")
        print("Processing...\n")

        for i, seg in enumerate(segments, 1):
            subtitle = call_vllm(seg["text"])
            print(f"[{i}] INPUT : {seg['text']}")
            print(f"    OUTPUT: {subtitle}\n")

        print("File processing complete.")

    elif choice == "4":
        print("\n--- Health Check ---")
        try:
            response = requests.get(f"{VLLM_BASE}/health", timeout=2)
            print("vLLM server is responsive.")
        except Exception as e:
            print(f"Health check failed: {e}")

    elif choice == "0":
        print("\nExiting CLI. Goodbye.")
        break

    else:
        print("Invalid choice. Please enter a number between 0 and 4.")
            compression_ratio: float
    chars: int

# === HELPERS ===
def format_prompt(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    return f"Pretvori avtomatski prepis govora v profesionalne podnapise. Strni vsebino na največ {max_chars} znakov ali manj.\n\n{text}"

def call_vllm(text: str, max_chars: int = DEFAULT_MAX_CHARS, temperature: float = 0.1) -> str:
    """Direct call to vLLM API"""
    
    prompt = format_prompt(text, max_chars)
    
    response = requests.post(
        VLLM_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": temperature,
        },
        timeout=30
    )
    
    result = response.json()
    subtitle = result['choices'][0]['message']['content'].strip()
    
    return subtitle

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

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting GaMS3 Subtitle Service...")
    logger.info(f"vLLM Server: {VLLM_URL}")
    logger.info(f"Model: {MODEL_NAME}")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
