# gams3-docker-subtitles
Docker deployment setup for GaMS3-12B subtitle generation service. 


Includes vLLM inference with LoRA adapter and FastAPI wrapper for transforming ASR transcripts into professional subtitles.


# -

1) First step: save the files


2) Second step: command "docker compose up vllm" in terminal to create the docker file


3) Third step: run "python fastapi_wrapper.py" through terminal, and upload .txt or .vtt files, insert an individual written example, or check the health of vLLM server connection. 

