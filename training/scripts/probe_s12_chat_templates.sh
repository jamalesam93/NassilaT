#!/usr/bin/env bash
set -euo pipefail
SERVER=/workspace/llama.cpp/build/bin/llama-server
GGUF=/workspace/models/s12/nassila-sanad-e4b-q6_k.gguf
PORT=8081

pkill -x llama-server 2>/dev/null || true
pkill -f 'run_l3_eval_batch.py.*s12_vast' 2>/dev/null || true
sleep 2

smoke() {
  python3 - <<'PY'
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:8081/v1/chat/completions",
    data=json.dumps({
        "model": "t",
        "messages": [{"role": "user", "content": "Reply with exactly one word: ok"}],
        "temperature": 0,
        "max_tokens": 24,
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        o = json.load(r)
    content = o["choices"][0]["message"].get("content") or ""
    print(repr(content[:160]))
except Exception as e:
    print("FAIL", e)
PY
}

for tmpl in "" gemma gemma2 gemma3 chatml; do
  echo "=== TRY template='${tmpl:-default}' ==="
  pkill -x llama-server 2>/dev/null || true
  sleep 1
  args=(-m "$GGUF" -ngl 99 -c 2048 --host 127.0.0.1 --port "$PORT" --jinja --reasoning-format none)
  if [[ -n "$tmpl" ]]; then
    args+=(--chat-template "$tmpl")
  fi
  nohup "$SERVER" "${args[@]}" >/tmp/s12_tmpl.log 2>&1 &
  for i in $(seq 1 40); do
    if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 \
      || curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  smoke
  # also show if server died
  if ! kill -0 "$(pgrep -x llama-server | head -1)" 2>/dev/null; then
    echo "server died:"; tail -n 15 /tmp/s12_tmpl.log
  fi
done
