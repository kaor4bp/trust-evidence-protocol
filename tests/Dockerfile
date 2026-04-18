ARG NODE_VERSION=22-bookworm-slim
FROM node:${NODE_VERSION}

ARG CODEX_VERSION=latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates python3 \
    && npm install -g @openai/codex@${CODEX_VERSION} \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
