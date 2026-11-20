#!/usr/bin/env python3
"""Tiny real file-lookup benchmark. Counts instrumented reads, not kernel syscalls.

Copy this file and strategy.json into a committed disposable Git fixture, then
use create_demo.py for a complete baseline/candidate comparison. The benchmark
is illustrative; it is not representative of an application workload.
"""
import json
import os
from pathlib import Path
import time
import tracemalloc

case = json.loads(os.environ['BENCH_CASE_JSON'])
strategy = json.loads(Path('strategy.json').read_text())['strategy']
state = Path(os.environ['BENCH_STATE_DIR'])
state.mkdir(parents=True, exist_ok=True)
source = state / ('payload-' + str(case['bytes']) + '.txt')
expected = 'x' * case['bytes']
source.write_text(expected)
latencies, reads, errors = [], [], []
cache = None
tracemalloc.start()
for _ in range(case['requests']):
    started = time.perf_counter_ns()
    count = 0
    if strategy == 'cached' and cache is not None:
        value = cache
    else:
        value = source.read_text()
        count += 1
        if strategy == 'cached': cache = value
    errors.append(int(value != expected))
    reads.append(count)
    latencies.append((time.perf_counter_ns() - started) / 1_000_000)
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(json.dumps({'status': 'ok', 'metrics': {'latency': latencies, 'io': reads, 'memory': peak / 1_000_000, 'errors': errors}}))
