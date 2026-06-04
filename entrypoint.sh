#!/bin/bash
set -e

echo "=== Sora AI Assistant — Cloud Entrypoint ==="
echo "Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Cloud Mode: $SORA_CLOUD_MODE"

# ── 1. GCP Secret Manager에서 .env 로드 (gcloud 사용 가능 시) ──
if command -v gcloud &>/dev/null && [ -n "$GCP_PROJECT_ID" ]; then
    echo "[Init] GCP Secret Manager에서 시크릿 로드..."
    gcloud secrets versions access latest --secret="sora-env" --project="$GCP_PROJECT_ID" > /app/.env 2>/dev/null || true

    # GA4 서비스 계정 키
    if [ -n "$GA4_SECRET_NAME" ]; then
        gcloud secrets versions access latest --secret="$GA4_SECRET_NAME" --project="$GCP_PROJECT_ID" > /app/secrets/ga4-service-account.json 2>/dev/null || true
        export GA4_SERVICE_ACCOUNT_PATH=/app/secrets/ga4-service-account.json
    fi
else
    echo "[Init] GCP 없음 — 로컬 .env 사용"
fi

# ── 2. Persistent Disk 심링크 (/mnt/sora-data 마운트 시) ──
if [ -d "/mnt/sora-data" ]; then
    echo "[Init] Persistent Disk 감지 — 데이터 디렉토리 연결..."

    # ChromaDB
    if [ -d "/mnt/sora-data/chroma_db" ]; then
        rm -rf /app/src/core/data/rag/chroma_db
        ln -sf /mnt/sora-data/chroma_db /app/src/core/data/rag/chroma_db
        echo "  -> chroma_db 연결 완료"
    fi

    # Assistant Memory
    if [ -d "/mnt/sora-data/assistant_memory" ]; then
        rm -rf /app/src/core/data/assistant_memory
        ln -sf /mnt/sora-data/assistant_memory /app/src/core/data/assistant_memory
        echo "  -> assistant_memory 연결 완료"
    fi

    # Logs
    mkdir -p /mnt/sora-data/logs
    rm -rf /app/logs
    ln -sf /mnt/sora-data/logs /app/logs
    echo "  -> logs 연결 완료"

    # Data (goals, schedules, etc.)
    if [ -d "/mnt/sora-data/data" ]; then
        rm -rf /app/data
        ln -sf /mnt/sora-data/data /app/data
        echo "  -> data 연결 완료"
    fi
else
    echo "[Init] Persistent Disk 없음 — 컨테이너 내부 스토리지 사용"
fi

# ── 3. Cloudflare Tunnel 인증 정보 확인 ──
export CF_TUNNEL_ENABLED=false
if [ -f "/app/secrets/cloudflared-token.txt" ] || [ -f "/app/secrets/cloudflared-config.yml" ]; then
    export CF_TUNNEL_ENABLED=true
    echo "[Init] Cloudflare Tunnel 설정 감지 — 터널 활성화"
else
    echo "[Init] Cloudflare Tunnel 설정 없음 — 터널 비활성화 (직접 접근 모드)"
fi

# ── 4. 로그 디렉토리 확보 ──
mkdir -p /app/logs

echo "=== 소라 시스템 시작 (supervisord) ==="
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/sora.conf
