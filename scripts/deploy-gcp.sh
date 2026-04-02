#!/bin/bash
# ============================================
# Sora AI Assistant — GCP 배포 자동화 스크립트
# 사용법: bash scripts/deploy-gcp.sh [setup|build|deploy|data|tunnel|status|ssh]
# ============================================
set -e

# ── 설정 ──
PROJECT_ID="ethereal-cache-487709-s3"
REGION="asia-northeast3"
ZONE="${REGION}-a"
VM_NAME="sora-vm"
MACHINE_TYPE="e2-small"
DISK_NAME="sora-data"
DISK_SIZE="20GB"
IMAGE_NAME="sora-app"
REPO_NAME="sora"
FULL_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}"

# ── 색상 ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[Sora]${NC} $1"; }
warn() { echo -e "${YELLOW}[경고]${NC} $1"; }
err() { echo -e "${RED}[에러]${NC} $1"; }

# ============================================
# setup: GCP 인프라 초기 설정 (1회만 실행)
# ============================================
cmd_setup() {
    log "=== GCP 인프라 초기 설정 ==="

    # 프로젝트 설정
    log "1/7. 프로젝트 설정..."
    gcloud config set project $PROJECT_ID

    # API 활성화
    log "2/7. API 활성화..."
    gcloud services enable \
        compute.googleapis.com \
        secretmanager.googleapis.com \
        artifactregistry.googleapis.com

    # Artifact Registry 생성
    log "3/7. Artifact Registry 생성..."
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Sora AI system images" \
        2>/dev/null || warn "이미 존재함"

    # Secret Manager에 .env 등록
    log "4/7. Secret Manager에 시크릿 등록..."
    if gcloud secrets describe sora-env --project=$PROJECT_ID &>/dev/null; then
        gcloud secrets versions add sora-env --data-file=.env
        log "  -> sora-env 업데이트 완료"
    else
        gcloud secrets create sora-env --data-file=.env
        log "  -> sora-env 생성 완료"
    fi

    # Persistent Disk 생성
    log "5/7. Persistent Disk 생성..."
    gcloud compute disks create $DISK_NAME \
        --size=$DISK_SIZE \
        --type=pd-standard \
        --zone=$ZONE \
        2>/dev/null || warn "이미 존재함"

    # 방화벽 규칙
    log "6/7. 방화벽 규칙 설정..."
    gcloud compute firewall-rules create sora-allow-web \
        --allow=tcp:443,tcp:80,tcp:7700 \
        --target-tags=sora-vm \
        --description="Sora 대시보드 접근 허용" \
        2>/dev/null || warn "이미 존재함"

    # VM 생성
    log "7/7. GCE VM 생성..."
    gcloud compute instances create $VM_NAME \
        --zone=$ZONE \
        --machine-type=$MACHINE_TYPE \
        --image-family=ubuntu-2404-lts-amd64 \
        --image-project=ubuntu-os-cloud \
        --boot-disk-size=30GB \
        --disk="name=${DISK_NAME},device-name=${DISK_NAME},mode=rw,auto-delete=no" \
        --tags=sora-vm \
        --scopes=cloud-platform \
        --metadata=startup-script='#!/bin/bash
# Docker 설치
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $USER
fi

# Persistent Disk 포맷 및 마운트
DEVICE="/dev/disk/by-id/google-sora-data"
MOUNT="/mnt/sora-data"
if [ ! -d "$MOUNT" ]; then
    mkdir -p $MOUNT
    if ! blkid $DEVICE; then
        mkfs.ext4 -F $DEVICE
    fi
    mount $DEVICE $MOUNT
    echo "$DEVICE $MOUNT ext4 defaults,nofail 0 2" >> /etc/fstab
fi

# 데이터 디렉토리 초기화
mkdir -p $MOUNT/{chroma_db,assistant_memory,logs,data,secrets}
'

    log "=== 초기 설정 완료! ==="
    log "다음 단계: bash scripts/deploy-gcp.sh build"
}

# ============================================
# build: Docker 이미지 빌드 + 푸시
# ============================================
cmd_build() {
    log "=== Docker 이미지 빌드 ==="

    # Docker 인증
    gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

    # 빌드
    TAG=$(date +%Y%m%d-%H%M)
    log "빌드 시작: ${FULL_IMAGE}:${TAG}"
    docker build -t ${FULL_IMAGE}:${TAG} -t ${FULL_IMAGE}:latest .

    # 푸시
    log "이미지 푸시 중..."
    docker push ${FULL_IMAGE}:${TAG}
    docker push ${FULL_IMAGE}:latest

    log "=== 빌드 완료: ${FULL_IMAGE}:${TAG} ==="
    log "다음 단계: bash scripts/deploy-gcp.sh deploy"
}

# ============================================
# deploy: VM에서 컨테이너 실행/업데이트
# ============================================
cmd_deploy() {
    log "=== 컨테이너 배포 ==="

    gcloud compute ssh $VM_NAME --zone=$ZONE --command="
        # Docker 인증
        gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet 2>/dev/null

        # 최신 이미지 풀
        docker pull ${FULL_IMAGE}:latest

        # 기존 컨테이너 중지
        docker stop sora 2>/dev/null || true
        docker rm sora 2>/dev/null || true

        # 시크릿에서 .env 파일 생성
        gcloud secrets versions access latest --secret=sora-env > /mnt/sora-data/secrets/.env

        # 컨테이너 실행
        docker run -d \
            --name sora \
            --restart=unless-stopped \
            --env-file=/mnt/sora-data/secrets/.env \
            -e SORA_CLOUD_MODE=true \
            -e GCP_PROJECT_ID=${PROJECT_ID} \
            -v /mnt/sora-data/chroma_db:/app/src/core/data/rag/chroma_db \
            -v /mnt/sora-data/assistant_memory:/app/src/core/data/assistant_memory \
            -v /mnt/sora-data/logs:/app/logs \
            -v /mnt/sora-data/data:/app/data \
            -v /mnt/sora-data/secrets:/app/secrets \
            -p 7700:7700 \
            -p 443:443 \
            -p 80:80 \
            ${FULL_IMAGE}:latest

        echo '컨테이너 시작됨'
        docker ps --filter name=sora
    "

    log "=== 배포 완료! ==="
    log "확인: bash scripts/deploy-gcp.sh status"
}

# ============================================
# data: 로컬 데이터를 GCE로 전송
# ============================================
cmd_data() {
    log "=== 데이터 전송 (로컬 → GCE) ==="

    # ChromaDB
    if [ -d "src/core/data/rag/chroma_db" ]; then
        log "ChromaDB 전송 중..."
        gcloud compute scp --recurse \
            src/core/data/rag/chroma_db/ \
            ${VM_NAME}:/mnt/sora-data/chroma_db/ \
            --zone=$ZONE
        log "  -> ChromaDB 전송 완료"
    fi

    # Assistant Memory
    if [ -f "src/core/data/assistant_memory/memory.json" ]; then
        log "메모리 파일 전송 중..."
        gcloud compute scp \
            src/core/data/assistant_memory/memory.json \
            ${VM_NAME}:/mnt/sora-data/assistant_memory/ \
            --zone=$ZONE
        log "  -> 메모리 전송 완료"
    fi

    # Goals & Schedules
    if [ -d "data" ]; then
        log "데이터 파일 전송 중..."
        gcloud compute scp --recurse \
            data/ \
            ${VM_NAME}:/mnt/sora-data/data/ \
            --zone=$ZONE
        log "  -> 데이터 전송 완료"
    fi

    log "=== 데이터 전송 완료! ==="
}

# ============================================
# tunnel: Cloudflare Tunnel 설정
# ============================================
cmd_tunnel() {
    log "=== Cloudflare Tunnel 설정 ==="
    warn "VM에 SSH 접속 후 수동으로 실행하세요:"
    echo ""
    echo "  1. cloudflared tunnel login"
    echo "  2. cloudflared tunnel create neo-genesis"
    echo "  3. cloudflared tunnel route dns neo-genesis neo.heoyesol.kr"
    echo ""
    echo "  설정 파일 생성:"
    echo "  cat > /mnt/sora-data/secrets/cloudflared-config.yml << EOF"
    echo "  tunnel: <TUNNEL_ID>"
    echo "  credentials-file: /app/secrets/<TUNNEL_ID>.json"
    echo "  ingress:"
    echo "    - hostname: neo.heoyesol.kr"
    echo "      service: http://localhost:7700"
    echo "    - service: http_status:404"
    echo "  EOF"
    echo ""
    echo "  4. 인증 파일을 /mnt/sora-data/secrets/로 복사"
    echo "  5. docker restart sora"
}

# ============================================
# status: VM 및 컨테이너 상태 확인
# ============================================
cmd_status() {
    log "=== 시스템 상태 ==="

    # VM 상태
    gcloud compute instances describe $VM_NAME --zone=$ZONE \
        --format="table(name, status, networkInterfaces[0].accessConfigs[0].natIP, machineType.basename())"

    echo ""

    # 컨테이너 상태
    gcloud compute ssh $VM_NAME --zone=$ZONE --command="
        echo '--- Docker 컨테이너 ---'
        docker ps --filter name=sora --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
        echo ''
        echo '--- 최근 로그 (10줄) ---'
        docker logs sora --tail 10 2>&1
        echo ''
        echo '--- 디스크 사용량 ---'
        df -h /mnt/sora-data
        echo ''
        echo '--- 메모리 ---'
        free -h
    "
}

# ============================================
# ssh: VM SSH 접속
# ============================================
cmd_ssh() {
    gcloud compute ssh $VM_NAME --zone=$ZONE
}

# ============================================
# logs: 컨테이너 로그 실시간 보기
# ============================================
cmd_logs() {
    gcloud compute ssh $VM_NAME --zone=$ZONE --command="docker logs sora -f --tail 50"
}

# ── 메인 ──
case "${1:-help}" in
    setup)  cmd_setup ;;
    build)  cmd_build ;;
    deploy) cmd_deploy ;;
    data)   cmd_data ;;
    tunnel) cmd_tunnel ;;
    status) cmd_status ;;
    ssh)    cmd_ssh ;;
    logs)   cmd_logs ;;
    *)
        echo "사용법: $0 {setup|build|deploy|data|tunnel|status|ssh|logs}"
        echo ""
        echo "  setup   - GCP 인프라 초기 설정 (1회)"
        echo "  build   - Docker 이미지 빌드 & 푸시"
        echo "  deploy  - VM에 컨테이너 배포/업데이트"
        echo "  data    - 로컬 데이터 → GCE 전송"
        echo "  tunnel  - Cloudflare Tunnel 설정 가이드"
        echo "  status  - 시스템 상태 확인"
        echo "  ssh     - VM SSH 접속"
        echo "  logs    - 컨테이너 로그 실시간"
        ;;
esac
