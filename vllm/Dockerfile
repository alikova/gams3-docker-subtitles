FROM vllm/vllm-openai:latest

EXPOSE 8000

CMD ["cjvt/GaMS3-12B-Instruct", \
     "--enable-lora", \
     "--lora-modules", "subtitles=alenkaz/GaMS3-12B-subtitles-offline", \
     "--max-lora-rank", "64", \
     "--trust-remote-code", \
     "--quantization", "bitsandbytes", \
     "--gpu-memory-utilization", "0.85", \
     "--dtype", "float16", \
     "--port", "8000"]
