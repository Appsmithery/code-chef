FROM python:3.11-slim

WORKDIR /app

COPY ../../agents/orchestrator/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt not found yet"

COPY ../../agents/orchestrator/ ./

EXPOSE 8001

CMD ["python", "main.py"]