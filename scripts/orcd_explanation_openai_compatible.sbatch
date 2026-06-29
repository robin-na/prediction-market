#!/usr/bin/env bash
# Run explanation-market request JSONL against an OpenAI-compatible vLLM server.
#
# This script is intended to be copied to the ORCD-side Behavioral_Portability
# repo and submitted from there, because it reuses that repo's OpenAI-compatible
# runner and summarizer.

#SBATCH --job-name=pm-explanation-llm
#SBATCH --account=mit_general
#SBATCH --partition=sched_mit_sloan_gpu_r8
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=02:00:00
#SBATCH --output=logs/pm-explanation-llm-%j.out
#SBATCH --error=logs/pm-explanation-llm-%j.err

set -euo pipefail

mkdir -p logs

MODEL_ID="${MODEL_ID:-Qwen/Qwen3-14B}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-${MODEL_ID}}"
REQUEST_ALIAS="${REQUEST_ALIAS:-pm_explanation}"
REQUESTS="${REQUESTS:?Set REQUESTS to a request JSONL path}"
OUTPUT_DIR="${OUTPUT_DIR:?Set OUTPUT_DIR to an output directory}"
OUTPUT_JSONL="${OUTPUT_JSONL:-${OUTPUT_DIR}/${REQUEST_ALIAS}_outputs.jsonl}"
SUMMARY_JSON="${SUMMARY_JSON:-${OUTPUT_DIR}/${REQUEST_ALIAS}_timing_summary.json}"
SUMMARY_CSV="${SUMMARY_CSV:-${OUTPUT_DIR}/${REQUEST_ALIAS}_per_request_timing.csv}"
RUN_METADATA_JSON="${RUN_METADATA_JSON:-${OUTPUT_DIR}/${REQUEST_ALIAS}_run_metadata.json}"

VLLM_ENV_NAME="${VLLM_ENV_NAME:-vllm_gemma4_py312}"
PY_ENV_NAME="${PY_ENV_NAME:-llm_conda}"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
DTYPE="${DTYPE:-auto}"
GENERATION_CONFIG="${GENERATION_CONFIG:-vllm}"
MAX_TOKENS="${MAX_TOKENS:-2048}"
TEMPERATURE="${TEMPERATURE:-0.6}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-3600}"
CONCURRENCY="${CONCURRENCY:-1}"
REQUEST_LIMIT="${REQUEST_LIMIT:-}"
ENDPOINT="${ENDPOINT:-chat}"
COMPLETION_PROMPT_STYLE="${COMPLETION_PROMPT_STYLE:-simple}"
EXTRA_BODY_JSON="${EXTRA_BODY_JSON:-}"
ENABLE_PREFIX_CACHING="${ENABLE_PREFIX_CACHING:-1}"
ENABLE_CHUNKED_PREFILL="${ENABLE_CHUNKED_PREFILL:-0}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-}"
HF_HOME="${HF_HOME:-/orcd/scratch/orcd/003/robinna/hf_home}"
HF_HUB_CACHE="${HF_HUB_CACHE:-${HF_HOME}/hub}"
XDG_CACHE_HOME="${XDG_CACHE_HOME:-/orcd/scratch/orcd/003/robinna/xdg_cache}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HUB_CACHE}}"

if [ ! -f "${REQUESTS}" ]; then
  echo "Missing request file: ${REQUESTS}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}" "${HF_HOME}" "${HF_HUB_CACHE}" "${XDG_CACHE_HOME}"
export HF_HOME HF_HUB_CACHE XDG_CACHE_HOME TRANSFORMERS_CACHE
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

PY_ENV_PREFIX="$(
  conda run --no-capture-output -n "${PY_ENV_NAME}" python -c 'import sys; print(sys.prefix)'
)"
export LD_LIBRARY_PATH="${PY_ENV_PREFIX}/lib:${LD_LIBRARY_PATH:-}"
echo "python_env_prefix=${PY_ENV_PREFIX}"

SERVER_LOG="${OUTPUT_DIR}/vllm_server_${SLURM_JOB_ID:-manual}.log"
BASE_URL="http://${HOST}:${PORT}/v1"

check_server_ready() {
  BASE_URL="${BASE_URL}" conda run --no-capture-output -n "${PY_ENV_NAME}" python -c \
    'import os, urllib.request; urllib.request.urlopen(os.environ["BASE_URL"] + "/models", timeout=5).read()' \
    >/dev/null 2>&1
}

print_server_models() {
  BASE_URL="${BASE_URL}" conda run --no-capture-output -n "${PY_ENV_NAME}" python -c \
    'import os, urllib.request; print(urllib.request.urlopen(os.environ["BASE_URL"] + "/models", timeout=10).read().decode())'
}

cat > "${RUN_METADATA_JSON}" <<EOF
{
  "slurm_job_id": "${SLURM_JOB_ID:-unknown}",
  "hostname": "$(hostname)",
  "model_id": "${MODEL_ID}",
  "served_model_name": "${SERVED_MODEL_NAME}",
  "request_alias": "${REQUEST_ALIAS}",
  "requests": "${REQUESTS}",
  "output_jsonl": "${OUTPUT_JSONL}",
  "summary_json": "${SUMMARY_JSON}",
  "summary_csv": "${SUMMARY_CSV}",
  "base_url": "${BASE_URL}",
  "max_model_len": ${MAX_MODEL_LEN},
  "max_tokens": ${MAX_TOKENS},
  "temperature": ${TEMPERATURE},
  "timeout_seconds": ${TIMEOUT_SECONDS},
  "concurrency": ${CONCURRENCY},
  "request_limit": "${REQUEST_LIMIT}",
  "endpoint": "${ENDPOINT}",
  "completion_prompt_style": "${COMPLETION_PROMPT_STYLE}",
  "extra_body_json": ${EXTRA_BODY_JSON:-{}},
  "hf_home": "${HF_HOME}",
  "hf_hub_cache": "${HF_HUB_CACHE}",
  "server_log": "${SERVER_LOG}"
}
EOF

echo "job_id=${SLURM_JOB_ID:-unknown}"
echo "host=$(hostname)"
echo "request_alias=${REQUEST_ALIAS}"
echo "requests=${REQUESTS}"
echo "output_jsonl=${OUTPUT_JSONL}"
echo "model_id=${MODEL_ID}"
echo "base_url=${BASE_URL}"
echo "endpoint=${ENDPOINT}"
echo "request_limit=${REQUEST_LIMIT:-full}"
echo "hf_home=${HF_HOME}"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
fi

if [ -z "${CUDA_HOME:-}" ]; then
  DETECTED_CUDA_HOME="$(
    conda run --no-capture-output -n "${VLLM_ENV_NAME}" python -c 'from pathlib import Path; import sys
prefix = Path(sys.prefix)
py_tag = f"python{sys.version_info.major}.{sys.version_info.minor}"
preferred = sorted((prefix / "lib" / py_tag / "site-packages" / "nvidia").glob("cu*/bin/nvcc"))
candidates = preferred or sorted(prefix.glob("lib/python*/site-packages/nvidia/cu*/bin/nvcc"))
print(candidates[0].parents[1] if candidates else "")
' 2>/dev/null
  )"
  if [ -n "${DETECTED_CUDA_HOME}" ]; then
    export CUDA_HOME="${DETECTED_CUDA_HOME}"
    export PATH="${CUDA_HOME}/bin:${PATH}"
    echo "detected_cuda_home=${CUDA_HOME}"
  fi
fi

VLLM_ARGS=(
  --model "${MODEL_ID}"
  --served-model-name "${SERVED_MODEL_NAME}"
  --host "${HOST}"
  --port "${PORT}"
  --max-model-len "${MAX_MODEL_LEN}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --dtype "${DTYPE}"
)
if [ -n "${GENERATION_CONFIG}" ]; then
  VLLM_ARGS+=(--generation-config "${GENERATION_CONFIG}")
fi
if [ "${ENABLE_PREFIX_CACHING}" = "1" ]; then
  VLLM_ARGS+=(--enable-prefix-caching)
fi
if [ "${ENABLE_CHUNKED_PREFILL}" = "1" ]; then
  VLLM_ARGS+=(--enable-chunked-prefill)
fi
if [ -n "${MAX_NUM_BATCHED_TOKENS}" ]; then
  VLLM_ARGS+=(--max-num-batched-tokens "${MAX_NUM_BATCHED_TOKENS}")
fi

cleanup() {
  if [ -n "${VLLM_PID:-}" ] && kill -0 "${VLLM_PID}" >/dev/null 2>&1; then
    echo "stopping_vllm_pid=${VLLM_PID}"
    kill "${VLLM_PID}" >/dev/null 2>&1 || true
    wait "${VLLM_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "starting_vllm_server"
conda run --no-capture-output -n "${VLLM_ENV_NAME}" python -m vllm.entrypoints.openai.api_server "${VLLM_ARGS[@]}" \
  >"${SERVER_LOG}" 2>&1 &
VLLM_PID=$!
echo "vllm_pid=${VLLM_PID}"

ready=0
for _ in $(seq 1 240); do
  if check_server_ready; then
    ready=1
    break
  fi
  if ! kill -0 "${VLLM_PID}" >/dev/null 2>&1; then
    echo "vllm server exited before readiness; last log lines:" >&2
    tail -n 120 "${SERVER_LOG}" >&2 || true
    exit 1
  fi
  sleep 10
done

if [ "${ready}" != "1" ]; then
  echo "vllm server did not become ready; last log lines:" >&2
  tail -n 120 "${SERVER_LOG}" >&2 || true
  exit 1
fi

echo "vllm_ready"
print_server_models || true
echo

RUN_ARGS=(
  --requests "${REQUESTS}"
  --output "${OUTPUT_JSONL}"
  --metadata-output "${OUTPUT_JSONL}.run.json"
  --base-url "${BASE_URL}"
  --model "${SERVED_MODEL_NAME}"
  --temperature "${TEMPERATURE}"
  --max-tokens "${MAX_TOKENS}"
  --timeout-seconds "${TIMEOUT_SECONDS}"
  --concurrency "${CONCURRENCY}"
  --endpoint "${ENDPOINT}"
  --completion-prompt-style "${COMPLETION_PROMPT_STYLE}"
)
if [ -n "${REQUEST_LIMIT}" ]; then
  RUN_ARGS+=(--limit "${REQUEST_LIMIT}")
fi
if [ -n "${EXTRA_BODY_JSON}" ]; then
  RUN_ARGS+=(--extra-body-json "${EXTRA_BODY_JSON}")
fi

echo "starting_openai_compatible_client"
conda run --no-capture-output -n "${PY_ENV_NAME}" python scripts/run_twin_openai_compatible.py "${RUN_ARGS[@]}"

echo "summarizing_outputs"
conda run --no-capture-output -n "${PY_ENV_NAME}" python scripts/summarize_openai_compatible_outputs.py \
  --outputs "${OUTPUT_JSONL}" \
  --output-json "${SUMMARY_JSON}" \
  --output-csv "${SUMMARY_CSV}"

echo "explanation_llm_done"
