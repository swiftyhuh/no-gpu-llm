#!/usr/bin/env python3
"""Run the realistic coding suite against one model preset, or validate the tests.

  python3 suite.py --validate            prove every test passes a correct answer and fails a wrong one
  python3 suite.py <preset> [--seed N]   run a preset and save bench/my-results/<preset>-s<seed>.json
"""
import hashlib, json, os, pathlib, re, resource, shutil, subprocess, sys, tempfile, time, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tasks import TASKS
from fresh_tasks import FRESH_TASKS

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(os.environ.get('RESULTS_DIR', ROOT / 'bench/my-results'))  # bench/results holds the archived runs
SERVER = os.environ.get('LLAMA_SERVER', 'llama-server')             # llama.cpp server binary
JANAS = pathlib.Path(os.environ.get('JANAS_DIR', pathlib.Path.home() / 'janas'))  # janas build folder, with models/ inside
PORT = 18767
M = os.environ.get('MODELS_DIR', str(ROOT / 'models')) + '/'         # GGUF files for the llama.cpp presets
K2 = M + 'K2-Horizon-4B-Q4_K_M.gguf'
FAST = dict(ctx=8192, max_tokens=1500, limit=300)   # thinking off
THINK = dict(ctx=8192, max_tokens=2500, limit=600)  # about 7 minutes at 6 tok/s; longer is unusable day to day
ON = dict(temperature=1.0, top_p=0.95, top_k=0, min_p=0.0)
PRECISE = dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0)
QWEN_OFF = dict(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0)
JNS = str(JANAS / 'models/qwen3.6-35b-a3b-q4km.jns')
HUIHUI = str(JANAS / 'models/huihui-qwen36-q4k.jns')
HERETIC = str(JANAS / 'models/heretic-qwen36-q4km.jns')
CYBER = str(JANAS / 'models/cybertiel-q4kxl.jns')
SHARP_CORE = "Never: open with preamble or pleasantries; restate the question; add filler transitions; hedge with niceties; or repeat a point you've already made.\nAlways: keep essential steps, caveats, uncertainties, and specifics — never drop correctness or a needed warning for brevity. Keep the final answer lean. Use the least structure that conveys it (plain prose when short; lists or code only when they earn their place). If genuinely uncertain, say so and explain why — never omit uncertainty for the sake of brevity.\nIf a user request is genuinely ambiguous, ask a sharp question, don't guess."
SHARP_OFF = 'Answer directly and concisely. Give the answer with only what it needs to be correct and usable.\n' + SHARP_CORE
SHARP_ON = 'Answer directly, after thinking. Lead with the answer, then only what it needs to be correct and usable.\n' + SHARP_CORE
JANAS_SERVER = str(JANAS / 'bin/x86_64-linux/janas-server')
SYSTEM = ('You are an expert programmer. Reply in plain Markdown, never JSON. Think briefly, then give the final answer '
          'as exactly one complete code block in the requested language. Include every header or import the code needs.')
PRESETS = {
    'ling': dict(model=M + 'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf', think=False, sampling=dict(temperature=0.7, top_p=0.8, top_k=20, min_p=0.0), **FAST),
    'ling-think': dict(model=M + 'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf', think=True, sampling=dict(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0), **THINK),
    'ling-budget': dict(model=M + 'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf', think=True, budget=800, sampling=dict(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0), **THINK),
    'ling-1200': dict(model=M + 'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf', think=True, budget=1200, sampling=dict(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0), **THINK),
    'groot-q3-nr': dict(model=M + 'Groot-19B-A3B-261023.i1-Q3_K_M.gguf', think=False, no_repack=True, sampling=PRECISE, ctx=8192, max_tokens=3000, limit=600),
    'groot-q3-sys': dict(model=M + 'Groot-19B-A3B-261023.i1-Q3_K_M.gguf', think=False, system=SYSTEM, sampling=PRECISE, ctx=8192, max_tokens=3000, limit=600),
    'qwen36-off': dict(janas=True, model=JNS, think=False, cache=8, sampling=QWEN_OFF, ctx=8192, max_tokens=3000, limit=600),
    'qwen36-c5': dict(janas=True, model=JNS, think=False, cache=5, sampling=QWEN_OFF, ctx=8192, max_tokens=3000, limit=600),
    'qwen36-think': dict(janas=True, model=JNS, think=True, budget=1200, cache=5, sampling=dict(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0), ctx=8192, max_tokens=3500, limit=900),
    'cybertiel-off': dict(janas=True, model=CYBER, think=False, cache=5, sampling=PRECISE, ctx=8192, max_tokens=3000, limit=600),
    'cybertiel-think': dict(janas=True, model=CYBER, think=True, cache=5, system=SHARP_ON, sampling=PRECISE, ctx=8192, max_tokens=4000, limit=900),
    'cybertiel-sharp': dict(janas=True, model=CYBER, think=False, cache=5, system=SHARP_OFF, sampling=PRECISE, ctx=8192, max_tokens=3000, limit=600),
    'huihui-off': dict(janas=True, model=HUIHUI, think=False, cache=5, sampling=QWEN_OFF, ctx=8192, max_tokens=3000, limit=600),
    'heretic-off': dict(janas=True, model=HERETIC, think=False, cache=5, sampling=QWEN_OFF, ctx=8192, max_tokens=3000, limit=600),
    'k2-low': dict(model=K2, effort='low', sampling=ON, **FAST),
    'minicpm-q4-think': dict(model=M + 'MiniCPM5-2B-Q4_K_M.gguf', think=True, sampling=ON, **THINK),
    'minicpm-q4-off': dict(model=M + 'MiniCPM5-2B-Q4_K_M.gguf', think=False, sampling=ON, **FAST),
    'mellum-think': dict(model=M + 'Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf', think=True, sampling=dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0), **THINK),
    'groot-off': dict(model=M + 'Groot-19B-A3B-261023.APEX-I-MiniPlus-V2.1.gguf', think=False, sampling=dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0), ctx=8192, max_tokens=3000, limit=600),
    'groot-q3': dict(model=M + 'Groot-19B-A3B-261023.i1-Q3_K_M.gguf', think=False, sampling=dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0), ctx=8192, max_tokens=3000, limit=600),
    'groot-think': dict(model=M + 'Groot-19B-A3B-261023.APEX-I-MiniPlus-V2.1.gguf', think=True, sampling=dict(temperature=0.6, top_p=0.95, top_k=20, min_p=0.0), **THINK),
}


TOOLS = ['systemd-run', 'bwrap', 'gcc', 'g++', 'python3', 'node', 'javac', 'java', 'swipl']
TASKS_SHA = hashlib.sha256(b''.join(pathlib.Path(__file__).with_name(f).read_bytes() for f in ('tasks.py', 'fresh_tasks.py'))).hexdigest()


def preflight():
    missing = [t for t in TOOLS if not shutil.which(t)]
    if missing:
        sys.exit('missing tools, nothing was run: ' + ', '.join(missing))


def limit_files():
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))  # no file over 64 MiB, the output log included


def sandbox(cmd, cwd, timeout=30):
    # A cgroup caps memory and processes. ulimit -v would break AddressSanitizer, which reserves huge virtual memory.
    box = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=2G', '-p', 'MemorySwapMax=0', '-p', 'TasksMax=128',
           'bwrap', '--unshare-all', '--die-with-parent', '--ro-bind', '/usr', '/usr', '--ro-bind', '/etc', '/etc',
           '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib', '/lib64', '--symlink', 'usr/bin', '/bin',
           '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--bind', cwd, '/w', '--chdir', '/w',
           '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/bin']
    with tempfile.TemporaryFile() as out:
        try:
            p = subprocess.run(box + cmd, stdout=out, stderr=subprocess.STDOUT, timeout=timeout, preexec_fn=limit_files)
        except subprocess.TimeoutExpired:
            return 124, f'timed out after {timeout}s (hang or deadlock)'
        out.seek(max(out.seek(0, 2) - 900, 0))
        return p.returncode, out.read().decode(errors='replace')


def check_cpp(task, code, d):
    pathlib.Path(d, 'sol.hpp').write_text(code)
    pathlib.Path(d, 'test.cpp').write_text('#define main model_main\n#include "sol.hpp"\n#undef main\n' + task['test'])
    base = ['g++', '-std=c++17', '-g', '-pthread', 'test.cpp']
    rc, out = sandbox(base + ['-fsanitize=address,undefined', '-fno-sanitize-recover=undefined', '-o', 'asan'], d, 120)
    if rc:
        return False, 'compile: ' + next((l for l in out.splitlines() if 'error' in l), out)[-220:]
    rc, out = sandbox(['./asan'], d)
    if rc or 'OK' not in out:
        return False, 'run: ' + out[-260:]
    if task.get('tsan'):
        rc, out = sandbox(base + ['-fsanitize=thread', '-o', 'tsan'], d, 120)
        if rc:
            return False, 'tsan compile: ' + out[-220:]
        rc, out = sandbox(['./tsan'], d, 60)
        if rc or 'OK' not in out or 'data race' in out:
            return False, 'tsan: ' + out[-260:]
    return True, ''


def check_c(task, code, d):
    pathlib.Path(d, 'sol.h').write_text(code)
    pathlib.Path(d, 'test.c').write_text('#define main model_main\n#include "sol.h"\n#undef main\n' + task['test'])
    rc, out = sandbox(['gcc', '-std=gnu11', '-g', '-fsanitize=address,undefined', '-fno-sanitize-recover=undefined', 'test.c', '-o', 'asan'], d, 120)
    if rc:
        return False, 'compile: ' + next((l for l in out.splitlines() if 'error' in l), out)[-220:]
    rc, out = sandbox(['./asan'], d)
    return (rc == 0 and 'OK' in out), ('' if rc == 0 and 'OK' in out else 'run: ' + out[-260:])


def check_generic(task, code, d):
    lang = task['lang']
    if lang == 'pl':
        pathlib.Path(d, 'sol.pl').write_text(code)
        pathlib.Path(d, 'test.pl').write_text(':- consult(sol).\n' + task['test'])
        rc, out = sandbox(['swipl', '-q', 'test.pl'], d)
        return (rc == 0 and 'OK' in out), ('' if rc == 0 and 'OK' in out else out[-280:])
    if lang == 'py':
        pathlib.Path(d, 'sol.py').write_text(code)
        pathlib.Path(d, 'test.py').write_text(task['test'])
        cmd = ['python3', 'test.py']
    elif lang == 'sql':
        pathlib.Path(d, 'sol.sql').write_text(code)
        pathlib.Path(d, 'test.py').write_text(task['test'])
        cmd = ['python3', 'test.py']
    elif lang == 'js':
        pathlib.Path(d, 'sol.js').write_text(code)
        pathlib.Path(d, 'test.js').write_text(task['test'])
        cmd = ['node', 'test.js']
    else:
        fname = task.get('file', 'Library.java')
        pathlib.Path(d, fname).write_text(code)
        pathlib.Path(d, 'Test.java').write_text(task['test'])
        rc, out = sandbox(['javac', fname, 'Test.java'], d, 120)
        if rc:
            return False, 'compile: ' + next((l for l in out.splitlines() if 'error' in l), out)[-220:]
        cmd = ['java', 'Test']
    rc, out = sandbox(cmd, d)
    return (rc == 0 and 'OK' in out), ('' if rc == 0 and 'OK' in out else out[-280:])


def check(task, code):
    d = tempfile.mkdtemp(prefix='bench-')
    try:
        if task['lang'] == 'cpp':
            return check_cpp(task, code, d)
        return check_c(task, code, d) if task['lang'] == 'c' else check_generic(task, code, d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def extract(text):
    blocks = re.findall(r'```[\w+#-]*[ \t]*\n(.*?)```', text, re.S)
    return blocks[-1] if blocks else None


def validate():
    preflight()
    wrong = {'cpp': 'int unrelated;\n', 'py': 'x = 1\n', 'java': 'public class Library {}\n',
             'sql': 'SELECT 1;', 'js': 'module.exports = {};\n', 'c': 'int unrelated;\n', 'pl': 'x.\n'}
    bad = 0
    for t in TASKS + FRESH_TASKS:
        good, why = check(t, t['ref'])
        reject, _ = check(t, wrong[t['lang']])
        fair = good and not reject
        bad += not fair
        print(f"{t['id']:13} reference {'PASS' if good else 'FAIL'}  wrong-answer {'rejected' if not reject else 'ACCEPTED'}  {why[:200]}", flush=True)
    print('ALL TESTS VALID' if not bad else f'{bad} TESTS BROKEN')
    return bad


def post(body, limit):
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}/v1/chat/completions', json.dumps(body).encode(),
                                 {'Content-Type': 'application/json'})
    return urllib.request.urlopen(req, timeout=limit)


def ask(task, p, seed):
    messages = [{'role': 'system', 'content': p['system']}] if p.get('system') else []
    messages.append({'role': 'user', 'content': task['prompt']})
    body = {'messages': messages, 'seed': seed, 'max_tokens': p['max_tokens'],
            'stream': True, 'stream_options': {'include_usage': True}, 'cache_prompt': False, **p['sampling']}
    if p.get('think') is False:
        if p.get('janas'):
            body['reasoning_effort'] = 'none'
        else:
            body['chat_template_kwargs'] = {'enable_thinking': False}
    start = time.monotonic()
    first_code = first_token = None; content = reasoning = ''; timings = {}; usage = {}; finish = None
    with post(body, p['limit']) as r:
        for line in r:
            if time.monotonic() - start > p['limit']:
                finish = 'time_limit'
                break
            if not line.startswith(b'data: '):
                continue
            data = line[6:].strip()
            if data == b'[DONE]':
                break
            chunk = json.loads(data)
            timings = chunk.get('timings') or timings
            usage = chunk.get('usage') or usage
            for c in chunk.get('choices', []):
                delta = c.get('delta', {})
                reasoning += delta.get('reasoning_content') or ''
                content += delta.get('content') or ''
                if first_token is None and (content or reasoning):
                    first_token = time.monotonic() - start
                if first_code is None and '```' in content:
                    first_code = time.monotonic() - start
                finish = c.get('finish_reason') or finish
    seconds = time.monotonic() - start
    text = content if '```' in content else (content + reasoning)
    code = extract(text) or content.strip() or None
    passed, why = (False, 'no answer') if code is None else check(task, code)
    return dict(task=task['id'], passed=passed, why=why, seconds=round(seconds, 1),
                first_code=None if first_code is None else round(first_code, 1), finish=finish,
                tokens=usage.get('completion_tokens') or timings.get('predicted_n'),
                tok_s=round(timings.get('predicted_per_second') or (usage.get('completion_tokens') or 0) / max(seconds - (first_token or 0), 0.1), 2), reasoning_chars=len(reasoning),
                content=content, reasoning=reasoning)


def run(name, seed):
    p = PRESETS[name]
    preflight()
    OUT.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in p.items() if k not in ('model', 'system')} | dict(
        model=os.path.basename(p['model']), system_sha256=hashlib.sha256(p.get('system', '').encode()).hexdigest()[:16],
        tasks_sha256=TASKS_SHA[:16], server=os.path.basename(JANAS_SERVER if p.get('janas') else SERVER))
    tag = f"{name}{'-fresh' if '--fresh' in sys.argv else ''}-s{seed}"
    args = [SERVER, '-m', p['model'], '-ngl', '0', '-t', '4', '-tb', '4', '-c', str(p['ctx']), '-np', '1',
            '--host', '127.0.0.1', '--port', str(PORT), '--no-webui']
    if p.get('think') is False:
        args += ['--reasoning', 'off']
    if p.get('effort'):
        args += ['--reasoning-effort', p['effort']]
    if p.get('budget'):
        args += ['--reasoning-budget', str(p['budget'])]
    if p.get('no_repack'):
        args += ['--no-repack']
    env = None
    if p.get('janas'):
        args = [JANAS_SERVER, p['model'], '--port', str(PORT), '--cache', str(p['cache']), '--think', 'on' if p.get('think') else 'off', '--no-web', '--no-mcp', '--keep-disk', '0'] + (['--reasoning-budget', str(p['budget'])] if p.get('budget') else [])
        env = dict(os.environ, JANAS_GPU='0', JANAS_NPU='0')
    results = []
    with open(OUT / f'{tag}.server.log', 'w') as log:
        server = subprocess.Popen(args, stdout=log, stderr=log, env=env)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError('server exited, see log')
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/{'v1/models' if p.get('janas') else 'health'}", timeout=3)
                    break
                except OSError:  # not listening yet
                    time.sleep(1)
            else:
                raise RuntimeError('server never became ready in 300 s, nothing was scored; see the server log')
            only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
            for task in (FRESH_TASKS if '--fresh' in sys.argv else TASKS):
                if only and task['id'] not in only:
                    continue
                start = time.monotonic()
                try:
                    r = ask(task, p, seed)
                except (OSError, ValueError) as e:  # the request never completed: an error row, not a failed answer
                    r = dict(task=task['id'], passed=False, why=f'request failed: {e}', seconds=round(time.monotonic() - start, 1),
                             first_code=None, finish='error', tokens=0, tok_s=0, reasoning_chars=0, content='', reasoning='')
                results.append(r)
                (OUT / f'{tag}.json').write_text(json.dumps({'preset': name, 'seed': seed, 'config': config, 'results': results}, indent=1))
                print(f"{tag} {r['task']:13} {'PASS' if r['passed'] else 'fail'} {r['seconds']:6.1f}s {r['tok_s']:5.1f} t/s {str(r['finish']):10} {r['why'][:80]!r}", flush=True)
            try:
                hwm = next(l for l in open(f'/proc/{server.pid}/status') if l.startswith('VmHWM'))
                peak = round(int(hwm.split()[1]) / 1024 / 1024, 2)
            except (OSError, StopIteration):
                peak = None
            (OUT / f'{tag}.json').write_text(json.dumps({'preset': name, 'seed': seed, 'config': config, 'peak_gb': peak, 'results': results}, indent=1))
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()


if __name__ == '__main__':
    if sys.argv[1] == '--validate':
        sys.exit(1 if validate() else 0)
    run(sys.argv[1], int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1)
