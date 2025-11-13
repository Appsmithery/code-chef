FROM python:3.11-slim

WORKDIR /app

COPY ../../agents/feature-dev/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt not found yet"

COPY ../../agents/feature-dev/ ./

EXPOSE 8002

CMD ["python", "main.py"]