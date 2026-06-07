#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Doutor 6.0 Headless Deployment Script
# Executar na VPS (Ubuntu 24.04) como root
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

# ─── Config ───
INSTALL_DIR="/opt/doutor6"
HERMES_PORT=8642
MCP_PORT=8765
OLLAMA_PORT=11434
PG_PORT=5433
REDIS_PORT=6379
DOMAIN="${DOMAIN:-doutor.maitigodoy.com.br}"
OPENROUTER_KEY="${OPENROUTER_API_KEY:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Sh48151623}"

echo "🚀 Doutor 6.0 Headless — Instalação em $(hostname)"
echo "════════════════════════════════════════════════════════"

# ─── 1. Dependências ───
echo "[1/6] Instalando dependências..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-v2 nginx curl jq netcat-openbsd
systemctl enable --now docker

# ─── 2. Criar diretórios ───
echo "[2/6] Criando diretórios..."
mkdir -p "${INSTALL_DIR}"/data/{doutor6,postgres,redis,ollama}
mkdir -p "${INSTALL_DIR}"/doutor6_data

# ─── 3. Baixar arquivos de configuração ───
echo "[3/6] Baixando arquivos de configuração..."
cd "${INSTALL_DIR}"

# Os arquivos devem ser copiados do repositório local para o VPS via scp
# Ou usar GitHub raw:
BASE_URL="https://raw.githubusercontent.com/MaitiGodoy/Doutor/main"
for f in doutor6_docker-compose.yml doutor6_data/USER.md doutor6_data/MEMORY.md doutor6_data/config.yaml; do
    curl -sfL "${BASE_URL}/${f}" -o "${f}" || echo "⚠️  Não foi possível baixar ${f}, copie manualmente"
done

# ─── 4. Docker Compose ───
echo "[4/6] Subindo containers..."
export OPENROUTER_API_KEY="${OPENROUTER_KEY}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD}"

docker compose -f doutor6_docker-compose.yml pull
docker compose -f doutor6_docker-compose.yml up -d

# ─── 5. Systemd Service ───
echo "[5/6] Criando serviço systemd..."
cat > /etc/systemd/system/doutor6.service << 'SERVICE'
[Unit]
Description=Doutor 6.0 - Headless AI Core
Documentation=https://github.com/MaitiGodoy/Doutor
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/docker compose -f /opt/doutor6/doutor6_docker-compose.yml up -d
ExecStop=/usr/bin/docker compose -f /opt/doutor6/doutor6_docker-compose.yml down
WorkingDirectory=/opt/doutor6
TimeoutStartSec=120
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable doutor6.service

# ─── 6. Nginx Reverse Proxy ───
echo "[6/6] Configurando Nginx..."
cat > /etc/nginx/sites-available/doutor6 << 'NGINX'
server {
    listen 80;
    server_name doutor.maitigodoy.com.br;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name doutor.maitigodoy.com.br;

    ssl_certificate /etc/letsencrypt/live/doutor.maitigodoy.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/doutor.maitigodoy.com.br/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Hermes API (núcleo central)
    location /api/hermes/ {
        proxy_pass http://127.0.0.1:8642/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    # MCP Server (tools)
    location /api/mcp/ {
        proxy_pass http://127.0.0.1:8765/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    # Health check
    location /health {
        return 200 "Doutor 6.0 - OK\n";
        add_header Content-Type text/plain;
    }

    # Deny all other routes
    location / {
        return 404;
    }
}
NGINX

# Se for usar sem SSL (internal only), usar este config:
cat > /etc/nginx/sites-available/doutor6-internal << 'NGINX_INTERNAL'
server {
    listen 8765;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8642;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }
}
NGINX_INTERNAL

# Se o domínio existir com SSL, ativar:
# ln -sf /etc/nginx/sites-available/doutor6 /etc/nginx/sites-enabled/
# Senão, usar internal:
# ln -sf /etc/nginx/sites-available/doutor6-internal /etc/nginx/sites-enabled/

nginx -t && systemctl reload nginx || echo "⚠️  Nginx config precisa de ajustes (domínio SSL)"

# ─── Final ───
echo ""
echo "✅ Doutor 6.0 Headless instalado!"
echo "   Hermes API:  http://127.0.0.1:${HERMES_PORT}"
echo "   MCP Server:  http://127.0.0.1:${MCP_PORT}"
echo "   Ollama:      http://127.0.0.1:${OLLAMA_PORT}"
echo "   PostgreSQL:  127.0.0.1:${PG_PORT}"
echo "   Redis:       127.0.0.1:${REDIS_PORT}"
echo ""
echo "📁 Dados em: ${INSTALL_DIR}/data/"
echo "📝 Logs: journalctl -u doutor6.service -f"
echo ""
echo "⚠️  Para expor via domínio, configure SSL:"
echo "   certbot --nginx -d doutor.maitigodoy.com.br"
echo ""
