FROM python:3.11-slim

WORKDIR /app

# Install task runner
RUN apt-get update && apt-get install -y curl && \
    sh -c "$(curl -fsSL https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ../shared/lib/ ./lib/

# Copy agent manifest
COPY ../shared/lib/agents-manifest.json ./agents-manifest.json

# Copy agent source code
COPY . ./

EXPOSE 8002

CMD ["python", "main.py"]