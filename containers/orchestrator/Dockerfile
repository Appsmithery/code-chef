FROM python:3.11-slim

WORKDIR /app

COPY agents/orchestrator/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/orchestrator/ ./

EXPOSE 8001

CMD ["python", "main.py"]