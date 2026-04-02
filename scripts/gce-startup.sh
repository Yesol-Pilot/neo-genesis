#!/bin/bash
set -e
# Docker 설치
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker $(whoami)
fi
# 데이터 디렉토리
mkdir -p /opt/sora/data /opt/sora/logs /opt/sora/secrets /opt/sora/chroma_db /opt/sora/assistant_memory
