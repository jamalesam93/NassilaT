#!/usr/bin/env bash
# Restart S12 without --skip-chat-parsing (fixes <unused49> loops).
set -euo pipefail
cd /workspace/nassila-s14/training

pkill -x llama-server 2>/dev/null || true
ps -eo pid,cmd | awk '/run_l3_eval_batch.py.*s12_vast|bash scripts\/run_s12_contrastive_vast\.sh/ {print $1}' | while read -r pid; do
  kill "$pid" 2>/dev/null || true
done
sleep 2

mv -f reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.jsonl \
  reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.bad_unused49.jsonl 2>/dev/null || true

GGUF=/workspace/models/s12/nassila-sanad-e4b-q6_k.gguf
SERVER=/workspace/llama.cpp/build/bin/llama-server
PORT=8081
LOG=outputs/s12_llama_server.log
PIDF=outputs/s12_llama.pid

nohup "$SERVER" \
  -m "$GGUF" -ngl 99 -c 4096 \
  --host 127.0.0.1 --port "$PORT" \
  --jinja --reasoning-format none \
  >"$LOG" 2>&1 &
echo $! >"$PIDF"
echo "server_pid=$(cat "$PIDF")"

for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 \
    || curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "server ready"
    break
  fi
  sleep 2
done

echo "=== smoke ==="
curl -sf "http://127.0.0.1:${PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"nassila-sanad-e4b","messages":[{"role":"user","content":"Reply with the single word: ok"}],"temperature":0.2,"max_tokens":32}' \
  | head -c 500
echo

PYTHONUNBUFFERED=1 nohup python3 scripts/run_l3_eval_batch.py \
  --base-url "http://127.0.0.1:${PORT}" \
  --api-key ollama \
  --model nassila-sanad-e4b \
  --data data/eval_holdout_body_contrastive_frozen_v2.jsonl \
  --retry 1 --repair --temperature 0.2 --timeout 300 --sleep 0.1 \
  --out reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.jsonl \
  > outputs/s12_contrastive_run.log 2>&1 < /dev/null &
echo "batch_pid=$!"
sleep 20
tail -n 15 outputs/s12_contrastive_run.log
python3 -c "
import json
from collections import Counter
p='reports/tier3_body_contrastive_frozen_v2_predictions_s12_vast.jsonl'
try:
  rows=[json.loads(l) for l in open(p)]
except FileNotFoundError:
  rows=[]
c=Counter()
for r in rows:
  s=r.get('status','')
  c['ok' if s=='ok' or s.startswith('ok') else 'err']+=1
print('early', len(rows), dict(c))
if rows:
  print('sample', rows[0].get('id'), rows[0].get('status')[:80], (rows[0].get('raw_output') or '')[:80])
"
