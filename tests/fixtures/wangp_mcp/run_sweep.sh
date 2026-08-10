#!/usr/bin/env bash
# Co-residency sweep: LTX-2 2.3 render while vLLM (12-13 GiB) stays resident.
# Usage: run_sweep.sh <model_type> <fixture_prefix>
set -u
cd "$(dirname "$0")"
B=http://172.24.16.1:8899/mcp/
H1="Content-Type: application/json"
H2="Accept: application/json, text/event-stream"
MT="${1:-ltx2_22B_distilled_gguf_q4_k_m}"
P="${2:-gguf_q4}"
OUT="${P}_generate.json"

echo "=== SWEEP $P: model_type=$MT (baseline 13182 MiB) $(date +%H:%M:%S) ==="
curl -s -m 20 -X POST "$B" -H "$H1" -H "$H2" -d "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"wangp_generate\",\"arguments\":{\"source\":{\"model_type\":\"$MT\",\"prompt\":\"A red apple on a wooden table, soft daylight, static camera.\",\"resolution\":\"512x320\",\"video_length\":9,\"num_inference_steps\":8}}}}" > "$OUT"

JOB=$(python3 - "$OUT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
r = d.get("result", {})
if r.get("isError"):
    print("ERROR: " + (r.get("content") or [{}])[0].get("text", "?")[:400])
    sys.exit(0)
sc = r.get("structuredContent") or {}
if sc.get("job_id"):
    print(sc["job_id"]); sys.exit(0)
print(json.loads(r["content"][0]["text"]).get("job_id", "NONE"))
PY
)
echo "generate: $(head -c 500 "$OUT")"
echo "JOB=$JOB"
if [[ "$JOB" == ERROR:* || "$JOB" == "NONE" || -z "$JOB" ]]; then
  echo "No job started — generate rejected (validation/load). Peak check skipped."
  exit 0
fi

echo "sampling VRAM every 4s..."
PEAK=0
: > "${P}_vram_samples.txt"
for i in $(seq 1 60); do
  V=$(nvidia-smi.exe --query-gpu=memory.used --format=csv,noheader 2>/dev/null | tr -dc '0-9')
  echo "$V" >> "${P}_vram_samples.txt"
  [[ -n "$V" && "$V" -gt "$PEAK" ]] && PEAK=$V
  if (( i % 5 == 0 )); then
    curl -s -m 10 -X POST "$B" -H "$H1" -H "$H2" -d "{\"jsonrpc\":\"2.0\",\"id\":8,\"method\":\"tools/call\",\"params\":{\"name\":\"wangp_get_job\",\"arguments\":{\"job_id\":\"$JOB\"}}}" > "${P}_job_poll.json"
    STATE=$(python3 -c "import json; d=json.load(open('${P}_job_poll.json')); r=d.get('result',{}); sc=r.get('structuredContent') or {}; print(sc.get('status', sc.get('state', json.dumps(sc)[:100])))" 2>/dev/null)
    echo "  t=$((i*4))s state=$STATE"
    case "$STATE" in
      *complete*|*Completed*|*COMPLETED*|*error*|*Error*|*fail*|*Fail*) break ;;
    esac
  fi
  sleep 4
done
echo "PEAK_VRAM_MiB=$PEAK"
echo "--- final get_job ---"
curl -s -m 10 -X POST "$B" -H "$H1" -H "$H2" -d "{\"jsonrpc\":\"2.0\",\"id\":9,\"method\":\"tools/call\",\"params\":{\"name\":\"wangp_get_job\",\"arguments\":{\"job_id\":\"$JOB\"}}}" > "${P}_job_final.json"
python3 -c "import json; d=json.load(open('${P}_job_final.json')); r=d.get('result',{}); print('isError:', r.get('isError')); sc=r.get('structuredContent') or {}; print(json.dumps(sc, indent=1)[:1500] if sc else (r.get('content') or [{}])[0].get('text','')[:800])"
echo "=== SWEEP $P DONE $(date +%H:%M:%S) ==="
