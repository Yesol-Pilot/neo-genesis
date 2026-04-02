# ============================================
# Sora v2.0 — Cloud Deployment
# GCE e2-medium (2 vCPU, 4GB RAM)
# Architecture: Gateway + Brain Worker + Redis
# ============================================
FROM python:3.12-slim AS base

# 시스템 패키지 (Redis 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    supervisor \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Cloudflare Tunnel
RUN curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

WORKDIR /app

# 의존성 설치
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# 소스 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p /app/src/core/data/rag/chroma_db \
    /app/src/core/data/assistant_memory \
    /app/src/core/data/vision_temp \
    /app/data \
    /app/logs \
    /app/secrets

# supervisord 설정
COPY supervisord.conf /etc/supervisor/conf.d/sora.conf

# 엔트리포인트
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 환경변수
ENV SORA_CLOUD_MODE=true
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 7700

# 헬스체크: pc-agents 엔드포인트 (SoraEngine 무관, 항상 빠르게 응답)
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD curl -f http://127.0.0.1:7700/api/pc-agents || exit 1

ENTRYPOINT ["/entrypoint.sh"]
