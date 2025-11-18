FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu

ARG DOCTL_VERSION=1.147.0

# Install common development tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    python3 \
    python3-pip \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install doctl CLI (DigitalOcean)
RUN curl -fsSL "https://github.com/digitalocean/doctl/releases/download/v${DOCTL_VERSION}/doctl-${DOCTL_VERSION}-linux-amd64.tar.gz" -o /tmp/doctl.tar.gz \
    && tar -xzf /tmp/doctl.tar.gz -C /tmp \
    && mv /tmp/doctl /usr/local/bin/doctl \
    && chmod +x /usr/local/bin/doctl \
    && rm -rf /tmp/doctl /tmp/doctl.tar.gz

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

# Set up workspace
WORKDIR /workspace

CMD ["sleep", "infinity"]