FROM python:3.11-slim

WORKDIR /app

COPY ../../mcp/gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt not found yet"

COPY ../../mcp/gateway/ ./

EXPOSE 8000

CMD ["python", "gateway.py"]