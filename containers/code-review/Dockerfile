FROM python:3.11-slim

WORKDIR /app

# Install task runner
RUN apt-get update && apt-get install -y curl git && \
    sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

COPY agents/code-review/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/code-review/ ./

EXPOSE 8003

CMD ["python", "main.py"]