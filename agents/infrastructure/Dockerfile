FROM python:3.11-slim

WORKDIR /app

# Install task runner
RUN apt-get update && apt-get install -y curl && \
    sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ../_shared/ ./agents/_shared/

# Copy agent manifest
COPY ../agents-manifest.json ./agents/agents-manifest.json

COPY src/ ./

EXPOSE 8004

CMD ["python", "main.py"]