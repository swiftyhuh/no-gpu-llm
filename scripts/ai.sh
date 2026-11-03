#!/usr/bin/env bash
# Local coding model: uncensored heretic Qwen3.6-35B-A3B on janas. No network access and a 12 GiB memory ceiling; files stay readable and writable.
# ai        fast, thinking off, for daily coding
# ai-think  slower, limited thinking, for hard problems
J="${JANAS_DIR:-$HOME/janas}"
SYSTEM="You are an expert programmer. Reply in plain Markdown. Give complete code in one code block, with every header or import it needs."
export JANAS_GPU=0 JANAS_NPU=0
case "$(basename "$0")" in
    ai-think) THINK="${AI_THINK_TOKENS:-1200}" ;;
    *) THINK=off ;;
esac
exec systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0 \
    bwrap --unshare-net --die-with-parent --dev-bind / / \
    "$J/bin/x86_64-linux/janas-chat" "$J/models/heretic-qwen36-q4km.jns" \
    --cache 5 --think "$THINK" --stats --system "$SYSTEM" "$@"
