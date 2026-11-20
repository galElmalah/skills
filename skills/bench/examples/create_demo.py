#!/usr/bin/env python3
"""Create and measure a disposable local Git fixture. Never touches an existing repo."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
destination = args.output.resolve()
if destination.exists(): raise SystemExit('Output must not exist; choose a new directory')
repo, study = destination / 'fixture', destination / 'study'
repo.mkdir(parents=True)
def git(*argv):
    subprocess.run(['git', '-C', str(repo), *argv], check=True, capture_output=True, text=True)
def bench(*argv):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/bench.py'), *map(str, argv)], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)
for filename in ('adapter.py', 'strategy.json'): shutil.copyfile(ROOT / 'examples' / filename, repo / filename)
git('init'); git('config', 'user.name', 'Benchmark fixture'); git('config', 'user.email', 'fixture@localhost')
git('add', '.'); git('commit', '-m', 'Add isolated demonstration harness')
bench('init', '--study', study, '--repo', repo)
for suite in ('screen', 'full'):
    print('Measuring baseline:', suite, flush=True)
    bench('run', '--study', study, '--experiment', 'E00', '--suite', suite, '--runtime', 'python-stdlib-demo', '--', sys.executable, 'adapter.py')
experiment = bench('experiment', '--study', study, '--id', 'E01', '--parent', 'E00', '--label', 'Reuse unchanged file contents', '--hypothesis', 'Caching within a case should reduce repeated file reads and lookup latency.', '--change', 'Use a per-case cache for immutable file contents.')
worktree = Path(experiment['worktree'])
(worktree / 'strategy.json').write_text('{"strategy":"cached"}\n')
subprocess.run(['git', '-C', str(worktree), 'commit', '-am', 'Cache immutable file contents within a case'], check=True, capture_output=True)
for suite in ('screen', 'full'):
    print('Measuring candidate:', suite, flush=True)
    bench('run', '--study', study, '--experiment', 'E01', '--suite', suite, '--runtime', 'python-stdlib-demo', '--', sys.executable, 'adapter.py')
analysis = bench('analyze', '--study', study, '--experiment', 'E01')
print(json.dumps({'study': str(study), 'verdict': analysis['verdict'], 'reasons': analysis['reasons']}, indent=2))
print('Held-out cases remain unmeasured. Promote only after reviewing the evidence.')
