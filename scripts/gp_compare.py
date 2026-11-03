"""Compare gguf-parser's MAX TPS with what this laptop measured under llama.cpp (4 threads, CPU only)."""
import json, os, subprocess, sys

PARSER = os.environ.get('GGUF_PARSER', 'gguf-parser')
BW = sys.argv[1] if len(sys.argv) > 1 else '12GBps'
FL = sys.argv[2] if len(sys.argv) > 2 else '134.4GFLOPS'
MODELS = [
    # name, kind, repo, file, measured tok/s (median decode speed from bench/results or bench/early/results), note
    ('MiniCPM5-2B Q4_K_M', 'dense', 'openbmb/MiniCPM5-2B-GGUF', 'MiniCPM5-2B-Q4_K_M.gguf', 10.3, ''),
    ('K2-Horizon-3.7B Q4_K_M', 'dense', 'IFM/K2-Horizon-3.7B-GGUF', 'K2-Horizon-4B-Q4_K_M.gguf', 5.2, ''),
    ('Qwen3.5-2B Heretic Q4_K_M', 'dense', 'darrellbest/Qwen3.5-2B-Heretic-GGUF', 'Qwen3.5-2B-Heretic-Q4_K_M.gguf', 8.6, 'during a download'),
    ('Qwen2.5-Coder-3B Q4_K_M', 'dense', 'mradermacher/Qwen2.5-Coder-3B-Instruct-abliterated-GGUF', 'Qwen2.5-Coder-3B-Instruct-abliterated.Q4_K_M.gguf', 6.6, 'during a download'),
    ('Groot-19B-A3B Q3_K_M', 'MoE', 'mradermacher/Groot-19B-A3B-261023-i1-GGUF', 'Groot-19B-A3B-261023.i1-Q3_K_M.gguf', 7.5, ''),
    ('Qwen3-Coder-30B-A3B IQ2_XXS', 'MoE', 'mradermacher/Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated-i1-GGUF', 'Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated.i1-IQ2_XXS.gguf', 6.5, ''),
    ('Ling-3.0-tiny Compact', 'MoE', 'SC117/Ling-3.0-tiny-abliterated-APEX-GGUF', 'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf', 16.6, ''),
    ('Mellum2.1 Thinking Q4_K_M', 'MoE', 'JetBrains/Mellum2.1-12B-A2.5B-Thinking-GGUF', 'Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf', 8.1, ''),
]


def find(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                return v
            r = find(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find(v, key)
            if r is not None:
                return r
    return None


print(f'bandwidth {BW}, CPU {FL}, -c 4096, no GPU layers')
print(f"{'model':30}{'kind':7}{'predicted':>10}{'measured':>10}{'measured/predicted':>20}  note")
for name, kind, repo, f, meas, note in MODELS:
    p = subprocess.run([PARSER, '--hf-repo', repo, '--hf-file', f, '--estimate', '--json', '-c', '4096',
                        '--ngl', '0', '--device-metric', f'{FL};{BW}'],
                       capture_output=True, text=True, timeout=240)
    try:
        tps = find(json.loads(p.stdout), 'maximumTokensPerSecond')
        tps = float(tps)
        print(f"{name:30}{kind:7}{tps:>10.2f}{meas:>10.1f}{meas / tps:>19.1f}x  {note}")
    except (ValueError, TypeError):  # no JSON, or no maximumTokensPerSecond in it
        print(f"{name:30}{kind:7}{'error':>10}{meas:>10.1f}{'':>20}  {(p.stderr or p.stdout)[-110:].strip()}")
