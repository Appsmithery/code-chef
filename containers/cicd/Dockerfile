FROM python:3.11-slim

WORKDIR /app

COPY ../../agents/cicd/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "requirements.txt not found yet"

COPY ../../agents/cicd/ ./

EXPOSE 8005

CMD ["python", "main.py"]