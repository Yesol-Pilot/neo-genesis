#!/bin/bash
# ============================================
# Sora PC Agent 설치 및 실행 (Linux/Mac)
#
# 사용법:
#   bash scripts/install_pc_agent.sh home-pc
#   bash scripts/install_pc_agent.sh work-pc
# ============================================
set -e

ID="${1:?사용법: $0 <pc-id> [server-url]}"
SERVER="${2:-wss://neo.heoyesol.kr/ws/pc-agent}"
TOKEN="${PC_AGENT_TOKEN:-sora-pc-agent-2026-yesol}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo ""
echo "========================================"
echo "  Sora PC Agent Installer"
echo "========================================"
echo "  PC ID:   $ID"
echo "  Server:  $SERVER"
echo ""

# 1. 패키지 설치
echo "[1/2] Python 패키지 설치..."
pip install websockets psutil pyperclip mss Pillow --quiet 2>/dev/null || pip3 install websockets psutil --quiet

# 2. systemd 서비스 생성 (Linux only)
if [ "$(uname)" = "Linux" ] && command -v systemctl &>/dev/null; then
    echo "[2/2] systemd 서비스 등록..."
    sudo tee /etc/systemd/system/sora-pc-agent.service > /dev/null << EOF
[Unit]
Description=Sora PC Agent ($ID)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$(which python3 || which python) $PROJECT_ROOT/scripts/sora_pc_agent.py --id $ID --server $SERVER --token $TOKEN
Restart=always
RestartSec=5
Environment=PC_AGENT_TOKEN=$TOKEN

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable sora-pc-agent
    echo "  -> systemd 서비스 등록 완료 (sudo systemctl start sora-pc-agent)"
else
    echo "[2/2] systemd 없음 — 수동 실행 필요"
fi

echo ""
echo "========================================"
echo "  설치 완료!"
echo "========================================"
echo ""
echo "실행: python $PROJECT_ROOT/scripts/sora_pc_agent.py --id $ID --server $SERVER"
echo ""

# 바로 실행
python3 "$PROJECT_ROOT/scripts/sora_pc_agent.py" --id "$ID" --server "$SERVER" --token "$TOKEN"
