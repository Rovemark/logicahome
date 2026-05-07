# LogicaHome — small image for running the MCP server (HTTP/SSE) headless.
#
# Build:    docker build -t logicahome .
# Run:      docker run -d --name logicahome --network host \
#               -v $HOME/.config/logicahome:/root/.config/logicahome \
#               logicahome logicahome mcp serve --http --host 0.0.0.0
#
# We use --network host because adapters speak local LAN protocols (Tuya
# UDP broadcast, mDNS for Hue/Matter, Shelly REST). Bridge-mode networking
# would require careful broadcast forwarding.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --upgrade pip && pip install -e ".[all]"

EXPOSE 8765

# Default to HTTP/SSE so the container exposes a useful surface out of the box.
CMD ["logicahome", "mcp", "serve", "--http", "--host", "0.0.0.0", "--port", "8765"]
