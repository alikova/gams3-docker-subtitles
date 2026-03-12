"""
GaMS3 Subtitle Service - CLI Tester
"""

import os
import requests
from datetime import datetime
from datetime import datetime

# === CONFIG ===
VLLM_BASE = os.getenv("VLLM_URL", "http://localhost:8000")
VLLM_URL = f"{VLLM_BASE}/v1/chat/completions"
MODEL_NAME = "subtitles"
DEFAULT_MAX_CHARS = 70

# === HELPERS ===
def format_prompt(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list:
    instruction = (
        f"Pretvori avtomatski prepis govora v profesionalne podnapise. "
        f"Strni vsebino na največ {max_chars} znakov ali manj.\n\n{text}"
    )
    return [{"role": "user", "content": instruction}]

def call_vllm(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    response = requests.post(
        VLLM_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": MODEL_NAME,        
            "messages": format_prompt(text, max_chars),
            "max_tokens": 150,
            "temperature": 0.1          
        },
        timeout=30
    )
    result = response.json()
    return result['choices'][0]['message']['content'].strip()

def save_results(results: list, source: str = "cli"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"subtitles_{source}_{timestamp}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"INPUT:  {r['input']}\n")
            f.write(f"OUTPUT: {r['output']}\n")
            f.write(f"Ratio:  {len(r['output'])/len(r['input']):.1%}\n")
            f.write("\n")
    print(f"\n Rezultati shranjeni v: {output_file}")

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
        if input("\nShrani rezultate? (y/n): ").strip().lower() == "y":
            save_results([{"input": text, "output": subtitle}], "single")

    elif choice == "2":
        print("\n--- Batch Mode ---")
        print("Enter multiple lines of text. Press ENTER on empty line to start.\n")
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
        results = []
        for i, text in enumerate(items, 1):
            subtitle = call_vllm(text)
            results.append({"input": text, "output": subtitle})
            print(f"[{i}] INPUT:  {text}")
            print(f"     OUTPUT: {subtitle}")
            print(f"     Ratio:  {len(subtitle)/len(text):.1%}\n")
        if input("\nShrani rezultate? (y/n): ").strip().lower() == "y":
            save_results(results, "batch")

    elif choice == "3":
        print("\n--- File Processing ---")
        file_path = input("Enter full file path: ").strip()
        if not os.path.exists(file_path):
            print("File not found.")
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        segments = parse_text_file(content)
        if not segments:
            print("No valid text segments found.")
            continue
        print(f"\nFound {len(segments)} segments. Processing...\n")
        results = []
        for i, seg in enumerate(segments, 1):
            subtitle = call_vllm(seg["text"])
            results.append({"input": seg["text"], "output": subtitle})
            print(f"[{i}/{len(segments)}] INPUT:  {seg['text']}")
            print(f"      OUTPUT: {subtitle}")
            print(f"      Ratio:  {len(subtitle)/len(seg['text']):.1%}\n")
        print("File processing complete.")
        if input("\nShrani rezultate? (y/n): ").strip().lower() == "y":
            save_results(results, os.path.splitext(os.path.basename(file_path))[0])

    elif choice == "4":
        print("\n--- Health Check ---")
        try:
            response = requests.get(f"{VLLM_BASE}/health", timeout=2)
            if response.status_code == 200:
                print(f" vLLM server is responsive at {VLLM_BASE}")
            else:
                print(f" vLLM responded with status {response.status_code}")
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            print(f"\n  Make sure vLLM is running at {VLLM_BASE}")

    elif choice == "0":
        print("\nExiting CLI. Goodbye.")
        break

    else:
        print("Invalid choice. Please enter a number between 0 and 4.")
