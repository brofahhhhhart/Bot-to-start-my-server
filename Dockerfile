# ═══════════════════════════════════════════════════════════════════
#  🐳 Dockerfile — Build Docker Image do Terminal Bot
#
#  Uso:
#  $ docker build -t discord-terminal-bot .
#  $ docker run -e DISCORD_TOKEN=xxx discord-terminal-bot
# ═══════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# ─────────────────────────────────────────────────────────────────
#  Metadata
# ─────────────────────────────────────────────────────────────────
LABEL maintainer="Terminal Bot"
LABEL version="3.0.0"
LABEL description="Discord Terminal Bot Premium"

# ─────────────────────────────────────────────────────────────────
#  Working Directory
# ─────────────────────────────────────────────────────────────────
WORKDIR /app

# ─────────────────────────────────────────────────────────────────
#  System Dependencies
# ─────────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    coreutils \
    procps \
    net-tools \
    vim \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────────
#  Python Dependencies
# ─────────────────────────────────────────────────────────────────
COPY requirements_premium.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_premium.txt

# ─────────────────────────────────────────────────────────────────
#  Application Code
# ─────────────────────────────────────────────────────────────────
COPY bot_premium.py .

# ─────────────────────────────────────────────────────────────────
#  Create Workspace Directory
# ─────────────────────────────────────────────────────────────────
RUN mkdir -p /app/terminal_workspace

# ─────────────────────────────────────────────────────────────────
#  Health Check
# ─────────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# ─────────────────────────────────────────────────────────────────
#  Environment Variables (pode ser sobrescrito no run)
# ─────────────────────────────────────────────────────────────────
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ─────────────────────────────────────────────────────────────────
#  Expose Port
# ─────────────────────────────────────────────────────────────────
EXPOSE 8080

# ─────────────────────────────────────────────────────────────────
#  Start Command
# ─────────────────────────────────────────────────────────────────
CMD ["python", "bot_premium.py"]
