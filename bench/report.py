#!/usr/bin/env python3
"""Print the suite results, one table per suite, best pass rate first, faster first on ties.

  python3 report.py [results folder]   default: bench/results, the archived runs

The main and unseen suites are reported separately, because their tasks differ.
Seeds of the same preset are pooled. Runs that didn't cover every task of their suite are marked as partial,
and rows that errored (the request never completed) are counted apart, not as failed tasks.
"""
import glob, json, pathlib, statistics, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tasks import TASKS
from fresh_tasks import FRESH_TASKS

SUITES = {'main': [t['id'] for t in TASKS], 'unseen': [t['id'] for t in FRESH_TASKS]}
folder = sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent / 'results'
rows = {}
for f in sorted(glob.glob(str(pathlib.Path(folder) / '*.json'))):
    d = json.load(open(f))
    suite = 'unseen' if all(r['task'] in SUITES['unseen'] for r in d['results']) else 'main'
    a = rows.setdefault((suite, d['preset']), dict(res=[], peak=None, runs=0, partial=False))
    a['res'] += d['results']
    a['runs'] += 1
    a['partial'] |= {r['task'] for r in d['results']} != set(SUITES[suite])
    a['peak'] = max(filter(None, [d.get('peak_gb'), a['peak']]), default=None)

for suite, ids in SUITES.items():
    out = []
    for (s, name), a in rows.items():
        if s != suite:
            continue
        done = [r for r in a['res'] if r['finish'] != 'error']
        errors = len(a['res']) - len(done)
        speeds = [r['tok_s'] for r in done if r['tok_s']]
        codes = [r['first_code'] for r in done if r['first_code'] is not None]
        rate = sum(r['passed'] for r in done) / max(len(done), 1)
        sec = sum(r['seconds'] for r in done) / max(len(done), 1)
        out.append((rate, sec, name, a, done, errors, speeds, codes))
    out.sort(key=lambda x: (x[3]['partial'], -x[0], x[1]))  # partial runs last
    print(f"== {suite} suite ({len(ids)} tasks)")
    print(f"{'preset':19}{'passed':>8}{'runs':>5}{'tok/s':>7}{'1st code':>9}{'s/task':>8}{'cut off':>8}{'errors':>7}{'RAM GiB':>8}")
    for rate, sec, name, a, done, errors, speeds, codes in out:
        flag = '  partial' if a['partial'] else ''
        print(f"{name:19}{sum(r['passed'] for r in done):>4}/{len(done):<3}{a['runs']:>5}"
              f"{statistics.median(speeds) if speeds else 0:>7.1f}{statistics.median(codes) if codes else 0:>8.0f}s{sec:>8.0f}"
              f"{sum(r['finish'] in ('length', 'time_limit') for r in done):>8}{errors:>7}{str(a['peak']):>8}{flag}")
    print()
    print(f"{'task':15}" + ''.join(f"{x[2][:13]:>14}" for x in out))
    for t in ids:
        print(f"{t:15}" + ''.join(f"{sum(r['passed'] for r in x[4] if r['task'] == t)}/{sum(r['task'] == t for r in x[4])}".rjust(14) for x in out))
    print()

print('failures:')
for (suite, name), a in sorted(rows.items()):
    for r in a['res']:
        if not r['passed']:
            print(f"  {suite:7}{name:18}{r['task']:13}{str(r['finish']):11}{r['why'][:100]!r}")
