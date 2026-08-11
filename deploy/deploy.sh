#!/usr/bin/env bash
# Sync this repo to the Raspberry Pi and (re)build the container.
# Usage: ./deploy/deploy.sh [user@]host
set -euo pipefail

PI_HOST="${1:-pi@192.168.0.20}"
REMOTE_DIR="~/apps/brandon-torreshq"

echo "==> Syncing files to ${PI_HOST}:${REMOTE_DIR}"
ssh "${PI_HOST}" "mkdir -p ${REMOTE_DIR}"
rsync -avz --delete \
  --exclude ".git" \
  --exclude "deploy" \
  ./ "${PI_HOST}:${REMOTE_DIR}/"

echo "==> Building and starting container on the Pi"
ssh "${PI_HOST}" "cd ${REMOTE_DIR} && docker compose up -d --build"

echo "==> Done. Site is running on 127.0.0.1:8090 on the Pi."
