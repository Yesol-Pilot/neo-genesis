#!/bin/bash
# Linux/macOS installer for Sora PC Agent.
# Token handling rule: keep PC_AGENT_TOKEN in the environment or an
# EnvironmentFile, never in ExecStart or process arguments.
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <pc-id> [server-url]" >&2
  exit 1
fi

ID="$1"
SERVER="${2:-${SORA_PC_AGENT_SERVER:-}}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -z "$SERVER" ]; then
  echo "ERROR: SORA_PC_AGENT_SERVER is not set and no server URL was provided." >&2
  exit 1
fi

if [ -z "${PC_AGENT_TOKEN:-}" ]; then
  echo "ERROR: PC_AGENT_TOKEN is not set." >&2
  exit 1
fi

PYTHON_BIN="$(command -v python3 || command -v python)"
if [ -z "$PYTHON_BIN" ]; then
  echo "ERROR: python3/python not found." >&2
  exit 1
fi

echo ""
echo "========================================"
echo "  Sora PC Agent Installer"
echo "========================================"
echo "  PC ID:   $ID"
echo "  Server:  $SERVER"
echo "  Token:   present (not printed)"
echo ""

echo "[1/2] Installing Python packages..."
pip install websockets psutil pyperclip mss Pillow --quiet 2>/dev/null || pip3 install websockets psutil --quiet

if [ "$(uname)" = "Linux" ] && command -v systemctl >/dev/null 2>&1; then
  echo "[2/2] Registering systemd service..."
  sudo mkdir -p /etc/neo-genesis
  sudo tee /etc/neo-genesis/sora-pc-agent.env >/dev/null <<EOF
PC_AGENT_TOKEN=$PC_AGENT_TOKEN
SORA_PC_AGENT_SERVER=$SERVER
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
EOF
  sudo chmod 600 /etc/neo-genesis/sora-pc-agent.env
  sudo tee /etc/systemd/system/sora-pc-agent.service >/dev/null <<EOF
[Unit]
Description=Sora PC Agent ($ID)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
EnvironmentFile=/etc/neo-genesis/sora-pc-agent.env
ExecStart=$PYTHON_BIN $PROJECT_ROOT/scripts/sora_pc_agent.py --id $ID --server $SERVER
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable sora-pc-agent
  echo "  -> systemd service registered: sudo systemctl start sora-pc-agent"
else
  echo "[2/2] systemd unavailable. Run manually when needed."
fi

echo ""
echo "========================================"
echo "  Install complete"
echo "========================================"
echo ""
echo "Run:"
echo "  python \"$PROJECT_ROOT/scripts/sora_pc_agent.py\" --id \"$ID\" --server \"$SERVER\""
echo ""

python3 "$PROJECT_ROOT/scripts/sora_pc_agent.py" --id "$ID" --server "$SERVER"
