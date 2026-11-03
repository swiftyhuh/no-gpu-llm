## Janas test report

- Janas commit: `faae71d`
- Levels: medium
- Model (medium): Qwen3.6-35B-A3B, run as `qwen3.6-35b-a3b-q4km.jns` - Janas's format (JNS), converted here by gguf2jns and jns_planes from `Qwen_Qwen3.6-35B-A3B-Q4_K_M.gguf` of `bartowski/Qwen_Qwen3.6-35B-A3B-GGUF`; the SHA-256 of every file checked against MODELS.md by janas-get
- CPU: Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz (8 threads; avx2)
- Memory: 15.5 GiB
- Disk: SK hynix PC711 HFS512GDE9X073N
- System: Arch Linux, Linux 7.2.11-arch1-1
- Compiler: gcc (GCC) 16.2.1 20260810
- GPU seen by Vulkan: vulkaninfo not installed; Janas built with GPU support
- Power: mains
- Load when it started: 3.76 over 8 threads (the speed lines below say how idle the CPU was before each measurement)

### Results

```
medium answer fingerprint ok (13e2f198c270b826)
medium speed measured with the CPU 99% idle before (load 2.71 over 8 threads; idle)
```

### bench-medium

```
janas-bench v2026.10.30.1, 20261101-010127
system:  Linux 7.2.11-arch1-1 x86_64
CPU:     Intel(R) Core(TM) i7-8650U CPU @ 1.90GHz (4 performance cores, 8 threads on them, 8 usable in all)
memory:  15.5 GiB, 14.4 GiB available; power: mains
GPU:     none usable: turned off by JANAS_GPU=0
NPU:     none usable: no Level Zero loader (libze_loader.so.1)
model:   Qwen3.6 35B A3B (qwen35moe), context 4096 tokens, expert cache 9.3 GiB, up to 8 compute threads, no GPU (turned off by JANAS_GPU=0), drafts from the MTP block, down matrix at 4 bits (memory)
test:    prompt 256 tokens of prose (not repeated), 64 generated tokens, greedy;
         with MTP drafts: a chat reply of as many tokens, greedy and sampled
         as the chat samples (temperature 0.7, top-k 20, top-p 0.8), no reasoning

warming up the expert cache...
measuring 2 configurations, 3 rounds...

configuration               prefill       decode   MTP greedy  MTP sampled     cache
8 threads                  30.9 tok/s    6.0 tok/s   10.0 tok/s    9.5 tok/s     91.7%
4 threads                  30.9 tok/s    6.4 tok/s   10.1 tok/s   10.0 tok/s     90.1%

result:  prefill 30.9 tok/s, decode 6.4 tok/s, with MTP 10.0 tok/s greedy, 9.5 tok/s sampled
         (the configuration the engine chose for each kind of pass, as it runs in a chat)
MTP:     drafts kept 78% greedy, 75% sampled (all configurations)
choices: mode max; one token: 4 threads (153.3 ms/token); 2-16 tokens: 8 threads (65.6 ms/token); 17-63 tokens: 8 threads (39.5 ms/token); blocks: 4 threads (28.7 ms/token)
```
