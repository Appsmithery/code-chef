FROM python:3.11-slim

WORKDIR /app

COPY ../../agents/code-review/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt not found yet"

COPY ../../agents/code-review/ ./

EXPOSE 8003

CMD ["python", "main.py"]