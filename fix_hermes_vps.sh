#!/bin/sh
sed -i 's|OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-sk-or-v1-dummy-ollama-local}|# OPENROUTER_API_KEY read from ~/.hermes/.env|' /docker/hermes-agent/docker-compose.yml
echo "--- docker-compose.yml (lines 1-25) ---"
head -25 /docker/hermes-agent/docker-compose.yml
