FROM python:3.11-slim

WORKDIR /app

# Install task runner
RUN apt-get update && apt-get install -y curl && \
    sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

COPY agents/documentation/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/documentation/ ./

EXPOSE 8006

CMD ["python", "main.py"]