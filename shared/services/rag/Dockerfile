FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY shared/services/rag/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY shared/services/rag/ /app/

# Expose port
EXPOSE 8007

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
