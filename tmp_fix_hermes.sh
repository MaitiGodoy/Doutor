#!/bin/sh
# Fix Hermes docker-compose.yml to not override OPENROUTER_API_KEY
sed -i 's|OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-sk-or-v1-dummy-ollama-local}|# OPENROUTER_API_KEY is read from ~/.hermes/.env|' /docker/hermes-agent/docker-compose.yml
cat /docker/hermes-agent/docker-compose.yml | head -25
