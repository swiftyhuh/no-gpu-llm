# gguf-parser MAX TPS vs measured speed on MoE models

Reported upstream as [gpustack/gguf-parser-go#67](https://github.com/gpustack/gguf-parser-go/issues/67). The issue lists Qwen3-Coder at 6.3 tok/s (11.5x). The median of its saved runs is 6.5 tok/s, which makes the gap slightly larger (11.9x).

[gguf-parser](https://github.com/gpustack/gguf-parser-go) can estimate a model's maximum tokens per second from its GGUF header, without downloading the weights. I compared that estimate with the speeds measured in this repo, to see whether it could have saved me some downloads.

## Method

- `gguf-parser` v0.28.1, Linux amd64 release binary
- Measured speeds: `llama.cpp` decode, 4 threads, CPU only, from `bench/results/` (Qwen3-Coder from `bench/early/results/`)
- FLOPS: 134.4 GFLOPS, worked out the way the gguf-parser README does it (cores x max frequency x FP32 ops per cycle): 4 x 4.2 GHz x 8 for AVX2. This is a theoretical peak, not a measurement.
- Bandwidth: 19.2 GBps, the spec for single-channel DDR4-2400. I also ran 12 GBps, which is closer to what I observed on this laptop.

```
gguf-parser --hf-repo <repo> --hf-file <file> --estimate --json -c 4096 --ngl 0 --device-metric "134.4GFLOPS;19.2GBps"
```

`python3 scripts/gp_compare.py 19.2GBps 134.4GFLOPS` runs it for every model and prints the table. The measured speeds are typed into the script as the median decode speed of each model's saved runs. The output of both runs is saved in `bench/results/gguf-parser/`.

## Result at 19.2 GBps

| Model | Quant | Type | Estimate (tok/s) | Measured (tok/s) | Measured / estimate |
|:--|:--|:--|--:|--:|--:|
| MiniCPM5-2B | Q4_K_M | dense | 6.44 | 10.3 | 1.6x |
| K2-Horizon-3.7B | Q4_K_M | dense | 2.85 | 5.2 | 1.8x |
| Groot-19B-A3B | Q3_K_M | MoE | 0.92 | 7.5 | 8.1x |
| Qwen3-Coder-30B-A3B | IQ2_XXS | MoE | 0.55 | 6.5 | 11.9x |
| Ling-3.0-tiny | APEX I-Compact | MoE | 2.30 | 16.6 | 7.2x |
| Mellum2.1-12B-A2.5B-Thinking | Q4_K_M | MoE | 1.40 | 8.1 | 5.8x |

At 12 GBps the dense ratios were 1.9-2.3x and the MoE ratios 6.0-12.2x. Groot's estimate moved from 0.91 to 0.92 tok/s between the two bandwidths, while MiniCPM's moved from 5.42 to 6.44.

Two more dense models (Qwen3.5-2B and Qwen2.5-Coder-3B) were left out, because their speeds were measured while a download was running.

## What it shows

At 19.2 GBps, dense estimates are within 2x of the measured speed (at 12 GBps, within 2.3x). MoE estimates are 6-12x too slow, and they barely react to bandwidth, so the formula seems to treat MoE models as compute-bound.

In `file_estimate__llamacpp.go`, the max-TPS block takes bytes per token from `ds[i].Weight.Sum()` and FLOPs from `Parameter.Compute`. Both seem to count every routed expert, though each token only uses `expert_used_count` of `expert_count`. I found this by reading the code. The maintainers haven't confirmed it yet.

## Possible fix

Count the always-active weights in full and scale the routed-expert weights by `expert_used_count / expert_count` for per-token bytes and FLOPs. The memory estimate should still include every expert, since they all stay loaded.

## Limits

- One laptop, CPU only, single-channel memory
- Mostly one run per model
- The FLOPS figure is theoretical
