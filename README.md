# no-gpu-llm

A 35B coding model on a 2018 laptop with 16 GB of RAM and no GPU, at about 10 tok/s. This repo has the method and the benchmark I used to pick the model, with the raw results of every benchmark run.

The laptop is an i7-8650U with one 16 GB RAM stick. The model I ended up with is a 22 GB mixture-of-experts model that doesn't fit in RAM. It passed all 9 of my main coding tasks, ran about as fast as a 2B model, and used 8 GiB of memory. On 4 unseen tasks written after I'd picked it, it passed 2. Small dense models scored 1/9 and 2/9 on the main tasks.

This is a practical comparison of a few setups on one laptop, not a ranking of model quality. The details of how the setups differ are below the table.

What this repo adds is the benchmark harness, the GGUF header check, the measurements and the write-up. The expert streaming and MTP come from [`janas`](https://github.com/prabanta-dev/janas), and the other models ran on [llama.cpp](https://github.com/ggml-org/llama.cpp). I designed the experiment and made the decisions; an AI assistant (Claude) did most of the implementation and writing.

## Results

| Setup | Main (9) | Unseen (4) | Speed | Peak RAM |
|---|---|---|---|---|
| Heretic Qwen3.6-35B-A3B, `janas`, 5 GiB cache | 9/9 | 2/4 | 10.6 tok/s | 8.0 GiB |
| Qwen3.6-35B-A3B, `janas`, 5 GiB cache | 9/9 | 2/4 | 10.2 tok/s | 8.0 GiB |
| CyberTiel, `janas`, Sharp system prompt | 5/9 | 2/4 | 8.0 tok/s | 8.9 GiB |
| Groot-19B-A3B `Q3_K_M`, `llama.cpp` | 5/9 | 0/4 (with `--no-repack`) | 7.5 tok/s | 12.7 GiB |
| Ling-3.0-tiny, 1,200-token thinking limit | 4/9 | not run | 15.7 tok/s | 6.1 GiB |
| Mellum 2.1, thinking | 4/9 | not run | 8.1 tok/s | 11.5 GiB |
| K2-Horizon-3.7B | 2/9 | not run | 5.2 tok/s | 6.7 GiB |
| MiniCPM5-2B, thinking off | 1/9 | not run | 10.3 tok/s | 3.0 GiB |

Speed is the median writing speed over the 9 main tasks. Reading the prompt is slower: about 25 tok/s in the long-context bench (`bench/results/long-ctx/`), so pasting a 2,000-token file adds about 80 seconds before the answer starts. The benchmark prompts are short, so the table doesn't show that cost. Peak RAM is the peak resident memory (VmHWM) of the model server alone.

Every setup I tried, including the ones that failed to load, is in [docs/full-record.md](docs/full-record.md).

### How the comparison was set up

- The 9 main tasks are C++ (3), Python (3), Java, SQL and JavaScript. Each has tests the model never sees; it only gets the prompt. I used these tasks while choosing the setup, so they favor the setup I chose.
- The 4 unseen tasks (C, Prolog, Java, C++) were written after the choice. The final model passed 2 of them, which is the better guide to how it does on new work.
- A task passes only if the code compiles and its tests pass in a sandbox. C and C++ run with AddressSanitizer and UndefinedBehaviorSanitizer, and the thread-safe LRU cache task also runs under ThreadSanitizer.
- Budgets differ. The thinking-off `llama.cpp` presets for K2, MiniCPM and Ling got 1,500 tokens and 300 seconds per task. The Qwen3.6, CyberTiel and Groot presets got 3,000 tokens and 600 seconds, and most thinking presets 2,500 tokens and 600 seconds (the Qwen3.6 and CyberTiel thinking runs got more). MiniCPM with thinking hit its token limit on all 9 tasks and Mellum on 6, so their scores only show what fits in these budgets.
- Runtimes differ. The `llama.cpp` presets ran with 8,192 tokens of context and 4 threads. `janas` used its own defaults: 16,384 tokens of context and up to 8 threads. Each preset has its own sampling settings, listed in `bench/suite.py`.
- Most setups ran once. The speed difference between the final model (10.6 tok/s) and MiniCPM5-2B (10.3) is too small to call an advantage without repeated runs.

## The laptop

- Dell Latitude 7490, i7-8650U: 4 cores, 8 threads, AVX2, about 22 W sustained
- 16 GB DDR4-2400 in one stick, so single channel
- PCIe 3 NVMe SSD
- Arch Linux, CPU only

## How to do it

### 1. Know your memory bandwidth

On a CPU, generating a token means reading the model's active weights from RAM, so memory bandwidth usually sets the speed limit. The spec is transfer rate x 8 bytes x channels: DDR4-2400 in one channel gives 19.2 GB/s. I saw about 12 GB/s in practice on this laptop, but that measurement isn't saved in this repo.

### 2. Pick a mixture-of-experts model

An MoE model only uses part of its weights for each token. Qwen3.6-35B-A3B has 35B parameters but only about 3B active per token, so it reads far fewer bytes per token than a 7B dense model. Together with MTP (step 4), that was enough to match the 2B model's speed and double the 3.7B model's.

Speed alone doesn't pick the model, though. Ling-3.0-tiny ran at 16 tok/s and still failed most of the main tasks.

### 3. Stream the experts from the SSD

The model is 22 GB and the laptop has 16 GB. [`janas`](https://github.com/prabanta-dev/janas) keeps the most used experts in RAM and reads the rest from the SSD when a token needs them.

You need about 45 GB of free disk space during the conversion, because two copies of the model exist at once.

```
git clone https://github.com/prabanta-dev/janas ~/janas
cd ~/janas
git checkout faae71d
JANAS_CFLAGS="-Wno-error" ./build.sh release test
```

GCC 16 needs `-Wno-error` for one warning. Commit `faae71d` is the build every `janas` result here came from.

Get the model and check it, still inside `~/janas`:

```
curl -L -o model.gguf https://huggingface.co/llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-GGUF/resolve/main/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-Q4_K_M.gguf
sha256sum model.gguf
# fc89d92377b27fe0f80eb683a5105d0921234c24f7c1d70ecc2356ddf994d781
```

Convert it to the `janas` format. Each file is deleted only after the next step succeeds:

```
mkdir -p models
bin/x86_64-linux/gguf2jns model.gguf flat.jns && rm model.gguf
bin/x86_64-linux/jns_planes flat.jns models/heretic-qwen36-q4km.jns && rm flat.jns
```

SSD wear comes mostly from writes, so I watched those. During a benchmark run, `janas` read 700-970 MB/s and wrote about 0.1 MB/s. It also saves conversations to disk by default (`--keep-disk`, up to 8 GiB, about 146 MB each), and the benchmark turns that off with `--keep-disk 0`.

### 4. Use a model with native MTP

Multi-token prediction lets the model draft several tokens per step. In the long-context bench in `bench/results/long-ctx/`, writing went from 5.0 tok/s without MTP to 9.4 tok/s with it. The file above keeps the model's MTP layer, which is what "Native-MTP-Preserved" in its name means.

### 5. Turn thinking off

On a slow CPU, thinking costs minutes per answer. With thinking off, the final model started writing code after about 7 seconds and still passed 9/9. The Qwen3.6 thinking run took about 200 seconds per task, so I stopped it after two tasks.

Thinking did help some smaller models. Ling went from 2/9 to 4/9 with a 1,200-token thinking limit, but each task took 117 seconds instead of 28.

### 6. Cap the expert cache

`--cache 5` limits the expert cache to 5 GiB. Peak memory went from 10.8 to 8.0 GiB, for about 15% less speed (12.1 to 10.2 tok/s on Qwen3.6).

### 7. Run it without network access

[`scripts/ai.sh`](scripts/ai.sh) starts the chat with no network and a 12 GiB memory ceiling. This only isolates the network. The model can still read and write your files.

```
JANAS_GPU=0 JANAS_NPU=0 systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0 \
  bwrap --unshare-net --die-with-parent --dev-bind / / \
  ~/janas/bin/x86_64-linux/janas-chat ~/janas/models/heretic-qwen36-q4km.jns --cache 5 --think off --stats
```

It needs a systemd user session (for `systemd-run --user`). Install it from this repo's folder:

```
mkdir -p ~/.local/bin
cp scripts/ai.sh ~/.local/bin/ai
chmod +x ~/.local/bin/ai
ln -s ai ~/.local/bin/ai-think
```

`~/.local/bin` has to be on your `PATH`. `ai-think` turns on thinking with a 1,200-token limit (`AI_THINK_TOKENS` changes it).

On my setup, `IPAddressDeny` in a user `systemd-run` scope didn't block anything and gave no error, which is why the script uses `bwrap --unshare-net`. Also, `janas-chat` starts the network tools it finds next to it (`janas-weather`, `janas-wiki`, `janas-git` and others), so I deleted them from `bin/x86_64-linux`.

### 8. Test with your own tasks

Public benchmark scores didn't predict much here. Mellum's 82 on LiveCodeBench and MiniCPM5's 69 didn't carry over to this laptop within a usable token budget. Write tasks that look like your own work, with tests the model never sees. The suite in `bench/` does this. See [Running the benchmark](#running-the-benchmark).

## Check a model before downloading it

[`scripts/gguf_gate.py`](scripts/gguf_gate.py) reads a remote GGUF header and prints the type of each router tensor, without downloading the file. `janas` refuses some types: it wouldn't load the Huihui Qwen3.6 build because its MTP router was `F16`. Checking first would have saved me that 22 GB download.

```
python3 scripts/gguf_gate.py "https://huggingface.co/mradermacher/Groot-19B-A3B-261023-i1-GGUF/resolve/main/Groot-19B-A3B-261023.i1-Q3_K_M.gguf"
# blocks 41, nextn_predict_layers 1, gate types ['F32'], last gate F32
```

I also tried [gguf-parser](https://github.com/gpustack/gguf-parser-go)'s speed estimate. At 19.2 GB/s it was within 2x for dense models but 6-12x too slow for MoE models. I reported it as [gguf-parser-go#67](https://github.com/gpustack/gguf-parser-go/issues/67), and the details are in [docs/gguf-parser-moe-check.md](docs/gguf-parser-moe-check.md).

## What I learned

- Speed depends on bytes read per token, so a bigger MoE model can beat a small dense one.
- Abliteration didn't hurt here. The heretic build tied the original Qwen3.6 on these tasks.
- Groot's APEX build scored 6/9 on one seed and 4/9 on the next, so one run isn't proof.
- Check the tests too. The `py_bugfix` test had a check stricter than its prompt asked for. I removed it and re-scored every model, but I didn't keep the removed check or the scores from before the change.
- Single-channel memory holds the speed back. A second RAM stick looks like the biggest upgrade, but I haven't tested that.

## Limits

- One laptop, 13 small tasks, mostly one run per setup
- The main tasks were used to choose the setup. Only the 4 unseen tasks are a fair test of the final model, and it passed 2.
- Fresh prompts only, not long sessions or multi-file projects
- Some tests check less than their prompts ask for. The C pipe test passes code that adds the numbers without a child process, the Java test doesn't check that streams are used, and the Prolog test doesn't check the library restriction. The LRU prompt never says what capacity 0 should do and the test never tries it; the winning answer calls `back()` on an empty list there, which is undefined behavior.
- Refusals weren't tested. "Uncensored" is the model publisher's label, not something I checked.
- `janas` is young and experimental. I scanned its source and watched its connections for 3 minutes, but that isn't a full code review.
- The CPU sat at 87-88°C with the fan at maximum under nonstop load. Temperatures, SSD health and bandwidth were observed during the runs but not logged here.

## Running the benchmark

You need a systemd user session, `bwrap` with user namespaces enabled, GCC with the sanitizers above, Python 3, Node.js, a JDK (tested with OpenJDK 21) and SWI-Prolog. For the `llama.cpp` presets you also need `llama-server` (tested at commit `5047748`). The sandbox maps `/lib` to `/usr/lib`, which matches Arch. Other distributions may need that line changed in `bench/suite.py`.

```
python3 bench/suite.py --validate             # every test passes its reference answer and rejects an unrelated one
python3 bench/suite.py heretic-off            # the 9 main tasks
python3 bench/suite.py heretic-off --fresh    # the 4 unseen tasks
python3 bench/suite.py heretic-off --seed 2   # another seed
python3 bench/report.py bench/my-results      # table of your runs
python3 bench/report.py                       # table of the archived runs in bench/results/
```

Each test program runs in `bwrap` with no network, inside a cgroup capped at 2 GiB of memory and 128 processes, with no file over 64 MiB. The suite checks for the tools it needs before starting, stops if the model server never comes up, and records failed requests as errors instead of failed answers.

New runs go to `bench/my-results/`, so they don't overwrite the archived results. They also save the preset's settings and a hash of the task files. `--validate` only proves each test accepts a correct answer and rejects unrelated code. It doesn't prove the tests catch every realistic bug.

Presets are defined at the top of `bench/suite.py`. They look for models in these places, which you can change with environment variables:

| Variable | Default | Used for |
|---|---|---|
| `JANAS_DIR` | `~/janas` | `janas-server` and `.jns` models |
| `MODELS_DIR` | `models/` in this repo | GGUF files for `llama.cpp` |
| `LLAMA_SERVER` | `llama-server` on `PATH` | `llama.cpp` presets |
| `RESULTS_DIR` | `bench/my-results/` | where new runs are saved |

`report.py` prints the main and unseen suites as separate tables, pools the seeds of each preset, and marks runs that didn't cover every task as partial.

## What's in the repo

- `bench/`: the suite (`tasks.py`, `fresh_tasks.py`, `suite.py`), the report script, and the archived results with server logs
- `bench/early/`: the first 4-task Python suite and its results
- `bench/results/gguf-parser/`: the saved gguf-parser comparison output
- `scripts/`: the `ai` launcher, the GGUF header check, the long-context bench and the gguf-parser comparison
- `docs/full-record.md`: every setup tested, the models that didn't work, and the safety checks
- `docs/gguf-parser-moe-check.md`: the gguf-parser comparison

## Sources

- janas: https://github.com/prabanta-dev/janas
- Qwen3.6-35B-A3B: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- Heretic build used here: https://huggingface.co/llmfan46/Qwen3.6-35B-A3B-uncensored-heretic-Native-MTP-Preserved-GGUF
- llama.cpp: https://github.com/ggml-org/llama.cpp
- gguf-parser: https://github.com/gpustack/gguf-parser-go
