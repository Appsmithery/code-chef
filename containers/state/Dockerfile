FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY services/state/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/state/ /app/
COPY configs/state/schema.sql /app/schema.sql

# Expose port
EXPOSE 8008

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8008"]
