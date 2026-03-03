"""
GaMS3 Subtitle Service - CLI Tester

Usage:
  On Frida (after sbatch run_app.sbatch):
    python fastapi_wrapper.py

  With Docker (after docker compose up):
    python fastapi_wrapper.py

The script connects to the vLLM server at localhost:8000 by default.
Override with environment variable: VLLM_URL=http://<host>:8000 python fastapi_wrapper.py
"""

import os
import requests

# === CONFIG ===
VLLM_BASE = os.getenv("VLLM_URL", "http://localhost:8000")
VLLM_URL = f"{VLLM_BASE}/v1/chat/completions"
MODEL_NAME = "subtitles"
DEFAULT_MAX_CHARS = 70

# === HELPERS ===
def format_prompt(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    return f"Pretvori avtomatski prepis govora v profesionalne podnapise. Strni vsebino na največ {max_chars} znakov ali manj.\n\n{text}"

def call_vllm(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Call vLLM API directly"""
    prompt = format_prompt(text, max_chars)
    response = requests.post(
        VLLM_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150,
            "temperature": 0.1
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

# === CLI ===
while True:
    print("\n" + "=" * 50)
    print(" GaMS3 Subtitle Service - CLI Tester")
    print("=" * 50)
    print(f" Connected to: {VLLM_BASE}")
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
        print(f"INPUT:  {text}")
        print(f"OUTPUT: {subtitle}")
        print(f"Chars:  {len(subtitle)} / {DEFAULT_MAX_CHARS}")
        print(f"Ratio:  {len(subtitle)/len(text):.1%}")
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
            print(f"[{i}] INPUT:  {text}")
            print(f"     OUTPUT: {subtitle}")
            print(f"     Ratio:  {len(subtitle)/len(text):.1%}\n")

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
            print(f"[{i}/{len(segments)}] INPUT:  {seg['text']}")
            print(f"      OUTPUT: {subtitle}")
            print(f"      Ratio:  {len(subtitle)/len(seg['text']):.1%}\n")

        print("File processing complete.")

    elif choice == "4":
        print("\n--- Health Check ---")
        try:
            response = requests.get(f"{VLLM_BASE}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ vLLM server is responsive at {VLLM_BASE}")
            else:
                print(f"⚠ vLLM responded with status {response.status_code}")
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            print(f"\n  Make sure vLLM is running at {VLLM_BASE}")
            print("  On Frida: sbatch run_app.sbatch, then ssh ana")
            print("  With Docker: docker compose up")

    elif choice == "0":
        print("\nExiting CLI. Goodbye.")
        break

    else:
        print("Invalid choice. Please enter a number between 0 and 4.")
