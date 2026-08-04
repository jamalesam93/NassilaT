#!/usr/bin/env bash
# One-shot Nanbeige probe bootstrap for Vast (paste after: ssh -p PORT root@HOST)
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq git 2>/dev/null || true
pip install -q requests 2>/dev/null || pip3 install -q requests

WORKDIR="${WORKDIR:-/workspace/nassila-probe}"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [[ ! -d NassilaT/.git ]]; then
  git clone --depth 1 https://github.com/jamalesam93/NassilaT.git || {
    echo "Clone failed — if repo is private, run vast_nanbeige_sync.ps1 from your PC first." >&2
    exit 1
  }
fi

cd NassilaT/training
git pull --ff-only 2>/dev/null || true
chmod +x scripts/run_nanbeige_vast_probe.sh

# Run in tmux so disconnect is safe
if command -v tmux >/dev/null 2>&1; then
  tmux kill-session -t nanbeige 2>/dev/null || true
  tmux new-session -d -s nanbeige "bash scripts/run_nanbeige_vast_probe.sh 2>&1 | tee outputs/nanbeige_probe.log"
  echo "Started in tmux session 'nanbeige'. Attach: tmux attach -t nanbeige"
  echo "Log: tail -f $PWD/outputs/nanbeige_probe.log"
else
  bash scripts/run_nanbeige_vast_probe.sh 2>&1 | tee outputs/nanbeige_probe.log
fi
