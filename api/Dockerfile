FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fastapi_wrapper.py .

# Expose port
EXPOSE 8001

# Run application
CMD ["python", "fastapi_wrapper.py"]