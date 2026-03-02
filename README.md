# gams3-docker-subtitles
Docker deployment setup for GaMS3-12B subtitle generation service. 


Includes vLLM inference with LoRA adapter and FastAPI wrapper for transforming ASR transcripts into professional subtitles.


# -

First step: save the files


Second step: command "docker compose up vllm" in terminal to create the docker file


Third step: run "python fastapi_wrapper.py" through terminal, and upload .txt or .vtt files, insert an individual written example, or check the health of vLLM server connection. 

