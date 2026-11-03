# Full research record

Everything tested, 31 Oct to 3 Nov 2026, with the numbers behind the README. Raw data is in `bench/results/` and `bench/early/results/`.

## The machine

- Dell Latitude 7490, Intel i7-8650U (4 cores, 8 threads, AVX2, no AVX-VNNI), about 22 W sustained power limit
- 16 GB DDR4-2400 in one stick, so single channel, with one SO-DIMM slot empty
- No usable GPU (UHD 620), no NPU
- SK hynix PC711 NVMe (PCIe 3)
- Arch Linux with Hyprland, swap on `zram`

Goal: one local model for coding (C++, C, Java, Prolog, SQL), above 4 tok/s, usable offline, uncensored if possible.

## Final setup

**Heretic uncensored Qwen3.6-35B-A3B `Q4_K_M` on `janas`, thinking off, 5 GiB expert cache.**

- File: `llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-GGUF`, `Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-Q4_K_M.gguf`, converted to `heretic-qwen36-q4km.jns`
- SHA-256 of the GGUF: `fc89d92377b27fe0f80eb683a5105d0921234c24f7c1d70ecc2356ddf994d781`
- 9/9 main tasks, 2/4 unseen tasks, 10.9 tok/s, 55s per task, 8.0 GiB peak RAM
- Refusal behaviour was never tested on this machine. "Uncensored" is the publisher's label.

Commands, both from `scripts/ai.sh` (copy it to `~/.local/bin/ai` and link `ai-think` to it):

- `ai`: thinking off, for daily coding. Tested once on heretic: C string-reverse answer in 9.9 seconds at 11.2 tok/s, 7.5 GiB peak (transcript not saved).
- `ai-think`: thinking on with a 1,200-token limit (`AI_THINK_TOKENS` changes it). Slower. Thinking helped Ling (2/9 to 4/9) but took about 4x as long per task, and the Qwen3.6 thinking run was stopped after two tasks. Tested once on a one-line prompt: worked, 42.8 seconds, 7.5 GiB peak (transcript not saved).

Both run `janas-chat` inside `bwrap --unshare-net` with a 12 GiB `systemd-run` memory limit. In the chat: `Ctrl-C` stops a reply, `Ctrl-D` leaves, `/think 1200` turns thinking on, `/reset` starts over, `/context` shows context use.

Giving it files: `wl-copy < main.cpp`, then paste. Several files: `tail -n +1 a.cpp b.h | wl-copy`.

## All results

"Main" is the 9-task suite, "Unseen" the 4 tasks written later. Thinking off unless noted, one seed unless noted. Speeds for the two `janas` 5 GiB cache rows are means over the 9 tasks; the other rows are medians. The README uses medians throughout (heretic 10.6, Qwen3.6 10.2). Peak RAM is the server's VmHWM, in GiB. Passes need hidden tests to pass. C and C++ run with AddressSanitizer and UndefinedBehaviorSanitizer, and the LRU cache task also with ThreadSanitizer.

| Setup | Main | Unseen | Speed | Time per task | Peak RAM |
|---|---|---|---|---|---|
| **Heretic Qwen3.6, `janas`, 5 GiB cache** | **9/9** | **2/4** | **10.9 tok/s** | **55s** | **8.0 GiB** |
| Qwen3.6, `janas`, 5 GiB cache | 9/9 | 2/4 | 10.1 tok/s | 59s | 8.0 GiB |
| Qwen3.6, `janas`, 8 GiB cache, 2 seeds | 17/18 | 2/4 | 12 tok/s | 50s | 10.8 GiB |
| CyberTiel, `janas`, Sharp system prompt | 5/9 | 2/4 | 8.0 tok/s | 64s | 8.9 GiB |
| CyberTiel, `janas`, thinking off | 5/9 | 1/4 | 7.5 tok/s | 74s | 8.8 GiB |
| CyberTiel, thinking with 4,000-token cap | 1/4 | Not run | 7-8 tok/s | Up to 15 min | 8.4 GiB |
| Groot `Q3_K_M`, `llama.cpp` | 5/9 | 0/4 (no repack) | 7.5 tok/s | 71s | 12.7 GiB, 9.3 no repack |
| Groot APEX MiniPlus, 2 seeds | 10/18 | Not run | 6.4 tok/s | 107s | 9.3 GiB |
| Ling Compact, 1,200-token thinking limit | 4/9 | Not run | 15.7 tok/s | 117s | 6.1 GiB |
| Mellum 2.1 thinking | 4/9 | Not run | 8.1 tok/s | 269s | 11.5 GiB |
| Ling Compact, 800-token limit | 3/9 | Not run | 16.7 tok/s | 85s | 6.2 GiB |
| Ling Compact, thinking off | 2/9 | Not run | 16.6 tok/s | 28s | 6.1 GiB |
| Ling Compact, thinking on | 2/9 | Not run | 15.9 tok/s | 142s | 6.2 GiB |
| K2-Horizon-3.7B `low` | 2/9 | Not run | 5.2 tok/s | 101s | 6.7 GiB |
| MiniCPM5-2B thinking on | 2/9 | Not run | 8.9 tok/s | 287s | 3.7 GiB |
| MiniCPM5-2B thinking off | 1/9 | Not run | 10.3 tok/s | 60s | 3.0 GiB |
| Groot, thinking on | 1/4, stopped | Not run | 6 tok/s | 424s | Not recorded |
| Qwen3.6 thinking, 1,200-token limit | 1/2, stopped | Not run | 10 tok/s | About 200s | Not recorded |

Early 4-task Python suite: Ling Compact 9/12, Qwen3-Coder-30B IQ2_XXS 7/12, Ling heretic Q4_K_M 6/12, Ling Balanced 8/12, Qwen2.5-Coder-3B 1/4, Qwen3.5-2B 0/4, VibeThinker 1/4.

Qwen3.6 long-context bench (`--ctx 500000` clamps to the trained 262,144, `--cache 6`): 1,024-token prompt read at 26.7 tok/s, writing 5.0 tok/s without MTP and 9.4 tok/s with it, 9.66 GiB; 8,192-token prompt read at 24.5 tok/s, writing 4.5 tok/s without MTP and 10.0 tok/s with it (greedy; 9.7 sampled), 10.99 GiB. The prompts are repeated prose, and only 64 tokens were generated. Code quality at large context was not tested.

## Models that did not work

- **Huihui Qwen3.6 MTP `Q4_K`:** converted, then refused at load: `tensor blk.40.ffn_gate_inp.weight missing or unexpected`. Its MTP layer's router is `F16`, and `janas` requires `F32` or `BF16`.
- **North Mini Code:** `cohere2moe` architecture, not supported by `janas`.
- **Sharp Spark X2.5 4B:** `spark2_5` architecture, not supported.
- **Ling on `janas`:** `bailingmoe3`, not supported.
- **Qwen2.5-Coder-7B, Qwen3.5-9B, Gemma 4 E4B:** ruled out by estimate at about 2-3 tok/s.
- **Qwen3-Coder-Next and Qwen3-Next-80B:** 48 GB, and they prefer 32 GB of RAM. Possible, but not tried.
- **DeepSeek-Coder-V2-Lite:** older, and 10.4 GB would leave too little RAM.
- **Nanbeige4.2-3B:** two loops per token, so about 2.7 tok/s by estimate.
- **Colibri:** 2.1 tok/s on Qwen3.6 on an i7-1355U in its own table, so not worth trying.

## The test suite

`bench/` holds the suite:

- `tasks.py`: 9 tasks with hidden tests and reference answers (3 C++, 3 Python, Java, SQL, JavaScript)
- `fresh_tasks.py`: 4 unseen tasks (C `fork`/`pipe`, Prolog, Java streams, C++ inheritance)
- `suite.py`: runs a preset, starts the server, sandboxes answers with `bwrap`, records speed, first code and peak RAM. `--validate` proves each test passes a correct answer and fails a wrong one.
- `report.py`: prints the results table
- `scripts/gguf_gate.py`: reads a remote GGUF header to check `janas` compatibility before downloading
- `scripts/long_ctx.sh`: long-context bench with a memory ceiling
- `results/`: raw answers, timings and logs
- `early/`: the first 4-task Python suite and its results

## Safety checks

These were observed during the runs. Only the network watch is saved, in `bench/results/janas-network-watch.txt`.

- SSD: 2% `Percentage Used`, 55.7 TB written, 100% spare, 29,679 power-on hours
- During `janas`: 700-970 MB/s read, about 0.1 MB/s written, about 58°C
- CPU 87-88°C under load, fan at about 7,000 RPM (its maximum), no throttling in a 30-second sample, many brief throttle events across the night
- Battery health 57%, charge limits 50-90%
- `janas` source scan: no prebuilt binaries, hidden blobs, telemetry, persistence or `sudo`. Live check: only localhost connections over 3 minutes. Not a full code review.
- `IPAddressDeny` in a user `systemd-run` scope silently fails. `bwrap --unshare-net` works.
- `--keep-disk` defaults to 8 GiB, and writes about 146 MB per saved conversation.
- `janas-chat` auto-starts network tools if found beside it, so they were removed.

## Rebuilding this setup

1. `git clone https://github.com/prabanta-dev/janas ~/janas`, `cd ~/janas`, `git checkout faae71d`, then build with `JANAS_CFLAGS="-Wno-error" ./build.sh release test`. All `janas` binaries used here came from one build of `faae71d`. GCC 16 needs that flag for one warning.
2. Download the GGUF above and verify its SHA-256.
3. `mkdir -p models`, then `bin/x86_64-linux/gguf2jns model.gguf flat.jns && rm model.gguf`, then `bin/x86_64-linux/jns_planes flat.jns models/heretic-qwen36-q4km.jns && rm flat.jns`. This needs about 45 GB free.
4. Remove `janas-flights`, `janas-git`, `janas-github`, `janas-maps`, `janas-prices`, `janas-quakes`, `janas-system`, `janas-weather` and `janas-wiki` from `bin/x86_64-linux`.
5. Copy `scripts/ai.sh` to `~/.local/bin/ai`, and link `ai-think` to it. Set `JANAS_DIR` if `janas` isn't in `~/janas`.

## Not finished

- Refusal testing
- Fix-loop tests, where errors go back to the model
- Pi agent on a real project
- `--quality high`, `--top-p 0.95` and the Sharp prompt on the final model
- Long sessions and real multi-file work
- A second seed on heretic

## Sources

- janas: https://github.com/prabanta-dev/janas
- janas reports: https://github.com/prabanta-dev/janas/blob/main/docs/reports.md
- Colibri: https://github.com/JustVugg/colibri
- gguf-parser: https://github.com/gpustack/gguf-parser-go
- CyberTiel: https://huggingface.co/peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP
- Sharp templates: https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates
- Harness benchmark: https://neuralnoise.com/2026/harness-bench-wip/?bare
- REAP pruning: https://www.cerebras.ai/blog/reap
- Qwen3.6-35B-A3B: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- Groot-19B-A3B: https://huggingface.co/GrootTeam/Groot-19B-A3B-261023
- Mellum 2.1: https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking
- MiniCPM5-2B: https://huggingface.co/openbmb/MiniCPM5-2B
- Ling-3.0-tiny: https://huggingface.co/inclusionAI/Ling-3.0-tiny
