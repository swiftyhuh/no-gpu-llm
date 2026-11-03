#!/usr/bin/env bash
# Long-context janas run with a hard memory ceiling, so a huge context cannot freeze the laptop.
# Usage: long_ctx.sh <ctx> <cache GiB> <prompt tokens> <gen tokens> <tag>
set -u
J="${JANAS_DIR:-$HOME/janas}"
OUT="${RESULTS_DIR:-$(dirname "$0")/../bench/my-results}/long-ctx"  # bench/results/long-ctx holds the archived runs
mkdir -p "$OUT"
export JANAS_GPU=0 JANAS_NPU=0
ctx=$1 cache=$2 prompt=$3 gen=$4 tag=$5
systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0 bash -c '
  cg=/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup)
  echo "== '"$tag"': ctx='"$ctx"' cache='"$cache"' prompt='"$prompt"' gen='"$gen"' start $(date +%H:%M:%S)"
  timeout 2400 '"$J"'/bin/x86_64-linux/janas-bench '"$J"'/models/qwen3.6-35b-a3b-q4km.jns \
    --ctx '"$ctx"' --cache '"$cache"' --prompt '"$prompt"' --gen '"$gen"' --rounds 1 --no-npu 2>&1 | tr "\r" "\n" | cut -c1-150
  echo "exit=${PIPESTATUS[0]} end $(date +%H:%M:%S)"
  echo "peak memory: $(awk "{printf \"%.2f GB\", \$1/1073741824}" "$cg/memory.peak" 2>/dev/null)"
' 2>&1 | tee -a "$OUT/$tag.txt"
