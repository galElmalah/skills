#!/usr/bin/env python3
"""Local benchmark ledger, isolated runner, and read-only viewer server."""
from __future__ import annotations
import argparse
import contextlib
import copy
import hashlib
import http.server
import json
import mimetypes
import os
from pathlib import Path
import platform
import random
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import (BenchError, ROOT, Store, analyze, atomic_json, digest, git,
                  now, protocol_hash, read_json, validate, validate_shape, SCHEMA)
from context import load_context


def emit(value):
    print(json.dumps(value, indent=2, allow_nan=False), flush=True)


def event(experiment, kind, message):
    experiment['events'].append({'timestamp': now(), 'kind': kind, 'message': message})


def experiment_by_id(document, experiment_id):
    experiment = next((item for item in document['experiments'] if item['id'] == experiment_id), None)
    if experiment is None: raise BenchError('Unknown experiment: ' + experiment_id)
    return experiment


def branch_available(repo, branch):
    result = subprocess.run(['git', '-C', str(repo), 'show-ref', '--verify', '--quiet', 'refs/heads/' + branch])
    if result.returncode == 0: raise BenchError('Ref already exists: ' + branch)


def new_experiment(experiment_id, label, parent, commit, branch, worktree, hypothesis, change):
    experiment = {'id': experiment_id, 'label': label, 'parentId': parent['id'] if parent else None,
                  'parentCommit': parent['commit'] if parent else None, 'commit': commit,
                  'status': 'planned', 'createdAt': now(), 'hypothesis': hypothesis, 'change': change,
                  'decision': None, 'worktree': str(worktree), 'branch': branch, 'artifacts': [], 'events': []}
    event(experiment, 'created', f'Created isolated worktree from {commit}')
    return experiment


def init_command(args):
    directory = Path(args.study).resolve()
    if directory.exists() and any(directory.iterdir()): raise BenchError('Study directory must be new or empty')
    repo = Path(git(Path(args.repo).resolve(), 'rev-parse', '--show-toplevel')).resolve()
    baseline = git(repo, 'rev-parse', args.ref + '^{commit}')
    config = read_json(args.config)
    cases = read_json(args.cases)
    required = {'id', 'title', 'description', 'metrics', 'scopes', 'protocol'}
    if not required <= set(config) <= required | {'mainMetricId'}: raise BenchError('Config must contain: ' + ', '.join(sorted(required)) + '; optional: mainMetricId')
    validate_shape(config['metrics'], SCHEMA['properties']['metrics'])
    if 'mainMetricId' in config: validate_shape(config['mainMetricId'], SCHEMA['properties']['mainMetricId'], '$.mainMetricId')
    main_metric_id = config.get('mainMetricId', next((metric['id'] for metric in config['metrics'] if metric['role'] == 'objective'), None))
    if main_metric_id is None: raise BenchError('At least one objective metric is required')
    protocol = {'seed': 42, 'repetitions': 5, 'warmups': 1, 'timeoutSeconds': 60, 'measurementWorkers': 1, **config['protocol'], 'splitHash': digest(cases)}
    train = [case for case in cases if case['partition'] == 'train']
    heldout = [case for case in cases if case['partition'] == 'heldout']
    screen = []
    rng = random.Random(protocol['seed'])
    for scope in config['scopes']:
        groups = sorted({case['group'] for case in train if case['scopeId'] == scope['id']})
        rng.shuffle(groups)
        selected = set(groups[:min(2, len(groups))])
        screen.extend(case['id'] for case in train if case['scopeId'] == scope['id'] and case['group'] in selected)
    champion_branch = f'codex/bench/{config["id"]}/champion'
    baseline_branch = f'codex/bench/{config["id"]}/e00'
    worktree = directory / 'worktrees' / 'E00'
    document = {'schemaVersion': 1, 'id': config['id'], 'title': config['title'], 'description': config['description'], 'createdAt': now(), 'updatedAt': now(),
                'repository': {'path': str(repo), 'baselineCommit': baseline, 'championCommit': baseline, 'championBranch': champion_branch},
                'protocol': protocol, 'protocolHash': '', 'mainMetricId': main_metric_id, 'metrics': config['metrics'], 'scopes': config['scopes'], 'cases': cases,
                'suites': [{'id': 'screen', 'label': 'Small training set', 'caseIds': screen}, {'id': 'full', 'label': 'Full training set', 'caseIds': [case['id'] for case in train]}, {'id': 'heldout', 'label': 'Held-out set', 'caseIds': [case['id'] for case in heldout]}],
                'experiments': [new_experiment('E00', 'Baseline', None, baseline, baseline_branch, worktree, 'Establish the frozen reference.', 'Unmodified committed baseline.')], 'runs': []}
    document['protocolHash'] = protocol_hash(document)
    validate(document)
    branch_available(repo, champion_branch)
    branch_available(repo, baseline_branch)
    directory.mkdir(parents=True, exist_ok=True)
    git(repo, 'worktree', 'add', '-b', baseline_branch, str(worktree), baseline)
    try:
        git(repo, 'branch', champion_branch, baseline)
        store = Store(directory)
        atomic_json(directory / '.managed.json', {'repository': str(repo), 'protocolHash': document['protocolHash']})
        store.save(document)
    except BaseException:
        # This command created this otherwise-empty worktree; source files are committed.
        git(repo, 'worktree', 'remove', str(worktree), check=False)
        git(repo, 'update-ref', '-d', 'refs/heads/' + baseline_branch, baseline, check=False)
        git(repo, 'update-ref', '-d', 'refs/heads/' + champion_branch, baseline, check=False)
        raise
    emit({'study': str(store.path), 'baseline': baseline, 'worktree': str(worktree), 'championBranch': champion_branch})


def experiment_command(args):
    validate_shape(args.id, SCHEMA['$defs']['Experiment']['properties']['id'])
    store = Store(args.study)
    with store.lock():
        document = store.load()
        store.managed(document)
        if any(item['id'] == args.id for item in document['experiments']): raise BenchError('Experiment ID already exists')
        parent = experiment_by_id(document, args.parent)
        if parent['parentId'] is not None and parent['status'] not in ('measured', 'promoted'):
            raise BenchError('An experimental parent must have a frozen measured snapshot')
        branch = f'codex/bench/{document["id"]}/{args.id.lower()}'
        worktree = store.directory / 'worktrees' / args.id
        if worktree.exists(): raise BenchError('Experiment worktree path already exists')
        experiment = new_experiment(args.id, args.label, parent, parent['commit'], branch, worktree, args.hypothesis, args.change)
        if args.contribution:
            experiment['contributionIds'] = args.contribution
            for source_id in args.contribution:
                source = experiment_by_id(document, source_id)
                has_snapshot_run = any(run['experimentId'] == source_id and run['commit'] == source['commit'] for run in document['runs'])
                if source['status'] in ('planned', 'running') or not has_snapshot_run:
                    raise BenchError('A contribution must reference a frozen experimental snapshot')
        document['experiments'].append(experiment)
        validate(document)
        branch_available(document['repository']['path'], branch)
        git(document['repository']['path'], 'worktree', 'add', '-b', branch, str(worktree), parent['commit'])
        store.save(document)
        emit(experiment)


def freeze(store, document, experiment):
    if experiment['status'] in ('discarded', 'running'): raise BenchError('Cannot run a discarded or already running experiment')
    worktree = Path(experiment['worktree'])
    if not worktree.is_dir(): raise BenchError('Managed worktree is missing')
    if git(worktree, 'symbolic-ref', '--short', 'HEAD') != experiment['branch']: raise BenchError('Worktree is on a different branch')
    if git(worktree, 'status', '--porcelain'): raise BenchError('Worktree is dirty. Commit intended changes and ignore build/cache outputs before measuring.')
    commit = git(worktree, 'rev-parse', 'HEAD')
    if experiment['parentId'] is None and commit != document['repository']['baselineCommit']: raise BenchError('The baseline is immutable')
    if experiment['status'] != 'planned' and commit != experiment['commit']: raise BenchError('Measured snapshots are immutable; create another experiment for this change')
    if experiment['parentCommit']:
        ancestor = subprocess.run(['git', '-C', str(worktree), 'merge-base', '--is-ancestor', experiment['parentCommit'], commit], capture_output=True)
        if ancestor.returncode: raise BenchError('Candidate no longer descends from its pinned parent')
    experiment['commit'] = commit
    relative = f'experiments/{experiment["id"]}/change.patch'
    diff = git(worktree, 'diff', '--binary', experiment['parentCommit'], commit) if experiment['parentCommit'] else ''
    path = store.directory / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(diff + ('\n' if diff else ''))
    if not any(item['path'] == relative for item in experiment['artifacts']):
        experiment['artifacts'].append({'kind': 'diff', 'label': 'Change against parent', 'path': relative})
    event(experiment, 'snapshot', f'Frozen source snapshot {commit}')
    return commit


def environment(args):
    result = {'profile': args.profile, 'platform': platform.system(), 'architecture': platform.machine(), 'cpuCount': str(os.cpu_count()), 'runnerPython': platform.python_version(), 'runtime': args.runtime, 'load': args.load}
    return result


@contextlib.contextmanager
def measurement_lock():
    import fcntl
    # Keep the shared measurement lock stable across package renames.
    directory = Path.home() / '.cache' / 'benchmark-lab'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'measurement.lock').open('a') as handle:
        try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise BenchError('Another local benchmark is measuring; shared-host measurements are serial') from exc
        try: yield
        finally: fcntl.flock(handle, fcntl.LOCK_UN)


def wait_for_adapter_exit(process, timeout):
    """Observe exit without reaping: reserve the group leader's PID through cleanup."""
    deadline = time.monotonic() + timeout
    while True:
        if os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG):
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(min(.01, remaining))


def stop_adapter_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # Darwin returns EPERM for a group containing only an unreaped zombie.
        # Confirm no live member remains; never suppress a real cleanup failure.
        if platform.system() != 'Darwin': raise
        groups = subprocess.run(['ps', '-ax', '-o', 'pgid=', '-o', 'stat='], text=True, capture_output=True, check=True, timeout=5).stdout
        if any(fields[0] == str(process.pid) and not fields[1].startswith('Z') for line in groups.splitlines() if len(fields := line.split()) >= 2):
            raise
    finally:
        process.wait()


def execute_sample(command, cwd, case, repeat, warmup, suite_id, protocol, runtime_dir, log):
    env = os.environ.copy()
    runtime_dir.mkdir(parents=True, exist_ok=True)
    env.update({'BENCH_CASE_JSON': json.dumps(case['input']), 'BENCH_CASE_ID': case['id'], 'BENCH_SCOPE_ID': case['scopeId'], 'BENCH_REPEAT': str(repeat), 'BENCH_WARMUP': str(int(warmup)), 'BENCH_SUITE_ID': suite_id, 'BENCH_SEED': str(protocol['seed']), 'BENCH_STATE_DIR': str(runtime_dir), 'TMPDIR': str(runtime_dir), 'XDG_CACHE_HOME': str(runtime_dir / 'cache'), 'PYTHONPYCACHEPREFIX': str(runtime_dir / 'pycache')})
    sample = {'caseId': case['id'], 'scopeId': case['scopeId'], 'repeat': repeat, 'warmup': warmup, 'status': 'ok', 'metrics': {}, 'durationMs': 0, 'error': None}
    started = time.perf_counter()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            wait_for_adapter_exit(process, protocol['timeoutSeconds'])
        except subprocess.TimeoutExpired:
            sample.update(status='timeout', error=f'Timed out after {protocol["timeoutSeconds"]} seconds')
        finally:
            # A successful leader can leave children running. Stop its whole group
            # before another case starts, while its unreaped PID still proves ownership.
            stop_adapter_group(process)
        sample['durationMs'] = (time.perf_counter() - started) * 1000
        stdout.seek(0); stderr.seek(0)
        out = stdout.read(1024 * 1024 + 1)
        err = stderr.read(256 * 1024).decode('utf-8', errors='replace')
        text = out[:1024 * 1024].decode('utf-8', errors='replace')
        log.write(json.dumps({'case': case['id'], 'repeat': repeat, 'warmup': warmup, 'exitCode': process.returncode, 'stdout': text[:256 * 1024], 'stderr': err}) + '\n')
        log.flush()
        if sample['status'] == 'ok':
            try:
                if process.returncode != 0: raise BenchError(f'Adapter exited {process.returncode}')
                if len(out) > 1024 * 1024: raise BenchError('Adapter output exceeds 1 MiB')
                payload = json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('non-finite number')))
                if not isinstance(payload, dict) or payload.get('status') != 'ok' or not isinstance(payload.get('metrics'), dict): raise BenchError('Adapter must output one JSON object: {"status":"ok","metrics":{...}}')
                validate_shape(payload['metrics'], SCHEMA['$defs']['Sample']['properties']['metrics'])
                sample['metrics'] = payload['metrics']
            except (BenchError, ValueError) as exc:
                sample.update(status='error', error=str(exc), metrics={})
    return sample


def make_run(document, experiment, suite_id, env, command):
    run_id = 'R' + uuid.uuid4().hex[:12]
    return {'id': run_id, 'experimentId': experiment['id'], 'suiteId': suite_id, 'commit': experiment['commit'], 'protocolHash': document['protocolHash'], 'startedAt': now(), 'endedAt': None, 'status': 'running', 'samples': [], 'environment': env, 'command': command, 'logPath': f'runs/{run_id}.jsonl'}


def finalize_run(store, document, experiment, run, failure=None):
    run['endedAt'] = now()
    run['status'] = 'failed' if failure or any(sample['status'] != 'ok' for sample in run['samples']) else 'completed'
    if experiment['status'] != 'promoted': experiment['status'] = 'failed' if run['status'] == 'failed' else 'measured'
    event(experiment, 'run', f'{run["suiteId"]} {run["id"]}: {run["status"]}' + (f' ({failure})' if failure else ''))
    if not any(item['path'] == run['logPath'] for item in experiment['artifacts']):
        experiment['artifacts'].append({'kind': 'log', 'label': f'{run["suiteId"]} run log', 'path': run['logPath']})
    atomic_json(store.directory / 'runs' / (run['id'] + '.json'), run)
    store.save(document)


def run_command(args):
    command = args.command[1:] if args.command and args.command[0] == '--' else args.command
    if not command: raise BenchError('Provide an explicit adapter command after --; stored report commands are never executed')
    store = Store(args.study)
    with store.lock(), measurement_lock():
        document = store.load()
        store.managed(document)
        experiment = experiment_by_id(document, args.experiment)
        freeze(store, document, experiment)
        run = make_run(document, experiment, args.suite, environment(args), command)
        document['runs'].append(run)
        if experiment['status'] != 'promoted': experiment['status'] = 'running'
        event(experiment, 'run', f'Started {args.suite} run {run["id"]}; serial shared-host measurement')
        store.save(document)
        suite = next(item for item in document['suites'] if item['id'] == args.suite)
        cases = [case for case in document['cases'] if case['id'] in suite['caseIds']]
        protocol = document['protocol']
        rng = random.Random(protocol['seed'])
        log_path = store.directory / run['logPath']
        log_path.parent.mkdir(parents=True, exist_ok=True)
        failure = None
        try:
            with log_path.open('x') as log:
                for warmup, count in [(True, protocol['warmups']), (False, protocol['repetitions'])]:
                    for repeat in range(count):
                        ordered = list(cases); rng.shuffle(ordered)
                        for case in ordered:
                            runtime_dir = store.directory / 'runtime' / experiment['id'] / run['id']
                            sample = execute_sample(command, experiment['worktree'], case, repeat, warmup, args.suite, protocol, runtime_dir, log)
                            run['samples'].append(sample)
                            # Persist progress atomically; readers never see half-written JSON.
                            try: store.save(document)
                            except BenchError as exc:
                                sample.update(status='error', metrics={}, error=str(exc))
                                store.save(document)
                if git(experiment['worktree'], 'status', '--porcelain') or git(experiment['worktree'], 'rev-parse', 'HEAD') != experiment['commit']:
                    failure = 'Adapter modified the source tree; results are not promotable'
        except BaseException as exc:
            failure = str(exc) or type(exc).__name__
            finalize_run(store, document, experiment, run, failure)
            raise
        finalize_run(store, document, experiment, run, failure)
        emit({'runId': run['id'], 'status': run['status'], 'samples': len(run['samples']), 'report': str(store.path)})
        if run['status'] == 'failed': raise BenchError('Run recorded failures; inspect its log before retrying')


def ingest_command(args):
    payload = read_json(args.input)
    if not isinstance(payload, dict) or set(payload) != {'commit', 'protocolHash', 'environment', 'samples'}: raise BenchError('Ingest expects {commit,protocolHash,environment:{profile,...},samples:[...]}')
    if not isinstance(payload['environment'], dict) or not payload['environment'].get('profile'): raise BenchError('Ingest requires an explicit environment profile')
    store = Store(args.study)
    with store.lock():
        document = store.load(); store.managed(document)
        experiment = experiment_by_id(document, args.experiment)
        freeze(store, document, experiment)
        if payload['commit'] != experiment['commit'] or payload['protocolHash'] != document['protocolHash']: raise BenchError('Imported observations do not match the exact frozen snapshot and protocol')
        run = make_run(document, experiment, args.suite, payload['environment'], [])
        run['samples'] = payload['samples']
        document['runs'].append(run)
        validate(document)
        log_path = store.directory / run['logPath']
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps({'source': str(Path(args.input).resolve()), 'kind': 'external-observations-import'}) + '\n')
        finalize_run(store, document, experiment, run)
        emit({'runId': run['id'], 'status': run['status'], 'samples': len(run['samples'])})


def ensure_champion_not_checked_out(repo, ref):
    if f'branch {ref}' in git(repo, 'worktree', 'list', '--porcelain').splitlines():
        raise BenchError('Champion branch is checked out; switch that worktree to another branch before promotion')


def promote_command(args):
    store = Store(args.study)
    with store.lock():
        document = store.load(); store.managed(document, allow_pending=True)
        pending = store.directory / '.promotion.json'
        if pending.exists():
            intent = read_json(pending)
            if intent['experimentId'] != args.experiment: raise BenchError('Retry promotion for ' + intent['experimentId'] + ' first')
            recovered = validate(intent['document'])
            ref = 'refs/heads/' + document['repository']['championBranch']
            actual = git(document['repository']['path'], 'rev-parse', ref)
            if actual == intent['oldCommit']:
                ensure_champion_not_checked_out(document['repository']['path'], ref)
                git(document['repository']['path'], 'update-ref', ref, recovered['repository']['championCommit'], actual)
            elif actual != recovered['repository']['championCommit']:
                raise BenchError('Champion changed outside the interrupted promotion; manual reconciliation required')
            store.save(recovered)
            pending.unlink()
            emit({'status': 'recovered-promotion', 'commit': recovered['repository']['championCommit']}); return
        experiment = experiment_by_id(document, args.experiment)
        repo = document['repository']
        if experiment['status'] == 'promoted' and experiment['commit'] == repo['championCommit']:
            if git(repo['path'], 'rev-parse', 'refs/heads/' + repo['championBranch']) != repo['championCommit']: raise BenchError('Champion ref changed outside this study; reconcile before promotion')
            emit({'status': 'already-promoted', 'commit': experiment['commit']}); return
        if experiment['status'] != 'measured': raise BenchError('Only measured experiments can be promoted')
        freeze(store, document, experiment)
        if experiment['parentCommit'] != repo['championCommit']: raise BenchError('Champion moved: create and measure an integration experiment from the current champion')
        result = analyze(document, experiment['id'], 'full', experiment['parentId'])
        if not result['eligible']: raise BenchError('Promotion blocked: ' + '; '.join(result['reasons'][:8]))
        branch_ref = 'refs/heads/' + repo['championBranch']
        ensure_champion_not_checked_out(repo['path'], branch_ref)
        expected = repo['championCommit']
        if git(repo['path'], 'rev-parse', branch_ref) != expected: raise BenchError('Champion ref changed outside this study; reconcile before promotion')
        repo['championCommit'] = experiment['commit']
        experiment['status'] = 'promoted'; experiment['decision'] = args.reason
        event(experiment, 'promotion', f'Promoted {experiment["commit"]} over {expected}: {args.reason}')
        atomic_json(pending, {'experimentId': experiment['id'], 'oldCommit': expected, 'document': document})
        git(repo['path'], 'update-ref', branch_ref, experiment['commit'], expected)
        store.save(document)
        pending.unlink()
        emit({'status': 'promoted', 'commit': experiment['commit'], 'branch': repo['championBranch'], 'analysis': result})


def note_command(args):
    store = Store(args.study)
    with store.lock():
        document = store.load(); store.managed(document)
        experiment = experiment_by_id(document, args.experiment)
        if args.discard:
            if experiment['status'] in ('running', 'promoted'): raise BenchError('Cannot discard a running or promoted experiment')
            experiment['status'] = 'discarded'; experiment['decision'] = args.message
        event(experiment, 'decision' if args.discard else 'note', args.message)
        store.save(document)
        emit({'experimentId': experiment['id'], 'status': experiment['status']})


def recover_command(args):
    """Close a run left running after its owning CLI process exited abruptly."""
    store = Store(args.study)
    with store.lock(), measurement_lock():
        document = store.load(); store.managed(document)
        experiment = experiment_by_id(document, args.experiment)
        running = [run for run in document['runs'] if run['experimentId'] == experiment['id'] and run['status'] == 'running']
        if not running: raise BenchError('No abandoned running record for this experiment')
        for run in running:
            finalize_run(store, document, experiment, run, 'Recovered abandoned run: ' + args.reason)
        emit({'experimentId': experiment['id'], 'recovered': [run['id'] for run in running], 'status': 'failed'})


def artifact_command(args):
    """Copy explicit local evidence into the study without modifying its source snapshot."""
    source = Path(args.file).resolve()
    if not source.is_file(): raise BenchError('Artifact source must be an existing file')
    store = Store(args.study)
    with store.lock():
        document = store.load(); store.managed(document)
        experiment = experiment_by_id(document, args.experiment)
        directory = store.directory / 'artifacts' / experiment['id']
        if not directory.resolve().is_relative_to(store.directory):
            raise BenchError('Artifact destination escapes the study directory')
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.resolve().is_relative_to(store.directory):
            raise BenchError('Artifact destination escapes the study directory')
        filename = re.sub(r'[^A-Za-z0-9._-]', '_', source.name)[:100] or 'artifact'
        fingerprint = hashlib.sha256()
        temporary = None
        try:
            with source.open('rb') as incoming, tempfile.NamedTemporaryFile(prefix='.copy-', dir=directory, delete=False) as outgoing:
                temporary = Path(outgoing.name)
                while chunk := incoming.read(1024 * 1024):
                    fingerprint.update(chunk)
                    outgoing.write(chunk)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            destination = directory / (fingerprint.hexdigest() + '-' + filename)
            if destination.is_symlink(): raise BenchError('Artifact destination must not be a symlink')
            os.replace(temporary, destination)
            temporary = None
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
        relative = destination.relative_to(store.directory).as_posix()
        artifact = {'kind': args.kind, 'label': args.label, 'path': relative}
        if artifact in experiment['artifacts']:
            emit({'experimentId': experiment['id'], 'status': 'already-registered', 'artifact': artifact})
            return
        experiment['artifacts'].append(artifact)
        event(experiment, 'note', f'Attached {args.kind} artifact: {args.label} ({relative})')
        store.save(document)
        emit({'experimentId': experiment['id'], 'status': 'registered', 'artifact': artifact})


def artifact_payload(store, document, relative):
    registered = {item['path'] for experiment in document['experiments'] for item in experiment['artifacts']} | {run['logPath'] for run in document['runs']}
    candidate = Path(relative)
    if relative not in registered or candidate.is_absolute() or '..' in candidate.parts: raise BenchError('Artifact is not an allowed relative path')
    resolved = (store.directory / candidate).resolve()
    if not resolved.is_relative_to(store.directory) or not resolved.is_file(): raise BenchError('Artifact is outside the study or missing')
    with resolved.open('rb') as handle: data = handle.read(256 * 1024 + 1)
    return {'path': relative, 'content': data[:256 * 1024].decode('utf-8', errors='replace'), 'truncated': len(data) > 256 * 1024}


def serve_command(args):
    store = Store(args.study); store.load()
    static = Path(args.viewer_dir).resolve()
    if not (static / 'index.html').is_file(): raise BenchError('Bundled viewer missing. Reinstall the complete bench skill, or provide --viewer-dir with a compatible build.')
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def send(self, status, body, content_type='application/json; charset=utf-8'):
            encoded = body if isinstance(body, bytes) else json.dumps(body, allow_nan=False).encode()
            self.send_response(status); self.send_header('Content-Type', content_type); self.send_header('Content-Length', str(len(encoded))); self.send_header('X-Content-Type-Options', 'nosniff'); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(encoded)
        def do_GET(self):
            port = self.server.server_address[1]
            allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if self.headers.get('Host') not in allowed or (self.headers.get('Origin') and self.headers.get('Origin') not in {'http://' + host for host in allowed}):
                self.send(403, {'error': 'Loopback same-origin requests only'}); return
            try:
                request = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(request.query)
                if request.path in ('/api/report', '/api/study'): self.send(200, store.load()); return
                if request.path == '/api/analysis':
                    self.send(200, analyze(store.load(), query.get('experiment', [''])[0], query.get('suite', ['full'])[0], query.get('reference', [None])[0])); return
                if request.path == '/api/artifact': self.send(200, artifact_payload(store, store.load(), query.get('path', [''])[0])); return
                if request.path.startswith('/api/'): self.send(404, {'error': 'Unknown endpoint'}); return
                relative = urllib.parse.unquote(request.path).lstrip('/')
                path = (static / relative).resolve()
                if not path.is_relative_to(static): self.send(403, {'error': 'Path escapes viewer root'}); return
                if not path.is_file():
                    if Path(relative).suffix: self.send(404, {'error': 'Asset not found'}); return
                    path = static / 'index.html'
                self.send(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            except (BenchError, OSError, ValueError) as exc: self.send(400, {'error': str(exc)})
        def do_POST(self): self.send(405, {'error': 'Read-only server'})
        do_PUT = do_POST
        do_DELETE = do_POST
    server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Benchmark viewer: http://127.0.0.1:{server.server_address[1]}/', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest='action', required=True)
    init = commands.add_parser('init', help='Freeze a benchmark protocol and create an isolated baseline')
    init.add_argument('--study', required=True); init.add_argument('--repo', required=True); init.add_argument('--ref', default='HEAD')
    init.add_argument('--config', default=str(ROOT / 'examples/config.json')); init.add_argument('--cases', default=str(ROOT / 'examples/cases.json')); init.set_defaults(func=init_command)
    experiment = commands.add_parser('experiment', help='Fork an isolated experiment from a pinned parent')
    for key in ('study', 'id', 'parent', 'label', 'hypothesis', 'change'): experiment.add_argument('--' + key, required=True)
    experiment.add_argument('--contribution', action='append', default=[], metavar='EXPERIMENT', help='Record a change source for this integration; repeat for multiple sources. Does not merge code.')
    experiment.set_defaults(func=experiment_command)
    run = commands.add_parser('run', help='Run an explicitly supplied adapter once per case and repeat')
    run.add_argument('--study', required=True); run.add_argument('--experiment', required=True); run.add_argument('--suite', choices=('screen', 'full', 'heldout'), required=True)
    run.add_argument('--profile', default='local'); run.add_argument('--runtime', default='unspecified'); run.add_argument('--load', default='fixed-case-sequential'); run.add_argument('command', nargs=argparse.REMAINDER); run.set_defaults(func=run_command)
    ingest = commands.add_parser('ingest', help='Import raw externally measured samples for a frozen snapshot')
    ingest.add_argument('--study', required=True); ingest.add_argument('--experiment', required=True); ingest.add_argument('--suite', choices=('screen', 'full', 'heldout'), required=True); ingest.add_argument('--input', required=True); ingest.set_defaults(func=ingest_command)
    analysis = commands.add_parser('analyze', help='Compare every applicable scope/metric without a hidden scalar score')
    analysis.add_argument('--study', required=True); analysis.add_argument('--experiment', required=True); analysis.add_argument('--reference'); analysis.add_argument('--suite', choices=('screen', 'full', 'heldout'), default='full'); analysis.set_defaults(func=lambda args: emit(analyze(Store(args.study).load(), args.experiment, args.suite, args.reference)))
    context = commands.add_parser('context', help='Summarize recorded evidence for resuming a study without exposing held-out feedback')
    context.add_argument('--study', required=True, help='Managed study directory or portable .bench/JSON report')
    context.add_argument('--limit', type=int, default=8, help='Recent experiments to include, plus baseline and champion (1–100; default 8)')
    context.add_argument('--include-heldout', action='store_true', help='Explicitly include held-out measurements and unclassified experiment notes')
    context.set_defaults(func=lambda args: emit(load_context(args.study, args.limit, args.include_heldout)))
    promote = commands.add_parser('promote', help='Advance champion only after comparable full-suite evidence passes')
    promote.add_argument('--study', required=True); promote.add_argument('--experiment', required=True); promote.add_argument('--reason', required=True); promote.set_defaults(func=promote_command)
    note = commands.add_parser('note', help='Append a decision or observation to an experiment')
    note.add_argument('--study', required=True); note.add_argument('--experiment', required=True); note.add_argument('--message', required=True); note.add_argument('--discard', action='store_true'); note.set_defaults(func=note_command)
    recover = commands.add_parser('recover', help='Mark abandoned running records failed after their CLI exits')
    recover.add_argument('--study', required=True); recover.add_argument('--experiment', required=True); recover.add_argument('--reason', required=True); recover.set_defaults(func=recover_command)
    artifact = commands.add_parser('artifact', help='Copy and register a local trace, profile, report, or other evidence')
    for key in ('study', 'experiment', 'file', 'label'): artifact.add_argument('--' + key, required=True)
    artifact.add_argument('--kind', choices=('diff', 'log', 'trace', 'profile', 'report', 'other'), required=True); artifact.set_defaults(func=artifact_command)
    validation = commands.add_parser('validate', help='Validate a report against the schema and provenance invariants')
    validation.add_argument('path'); validation.set_defaults(func=lambda args: emit({'valid': bool(validate(read_json(Path(args.path) / 'study.json' if Path(args.path).is_dir() else args.path)))}))
    export = commands.add_parser('export', help='Write a portable viewer report without absolute local paths')
    export.add_argument('--study', required=True); export.add_argument('--output', required=True); export.set_defaults(func=export_command)
    serve = commands.add_parser('serve', help='Serve the viewer and report read-only on loopback')
    serve.add_argument('--study', required=True); serve.add_argument('--port', type=int, default=4318); serve.add_argument('--viewer-dir', default=str(ROOT / 'assets/viewer')); serve.set_defaults(func=serve_command)
    return root


def export_command(args):
    document = Store(args.study).load()
    document = copy.deepcopy(document)
    document['repository']['path'] = ''
    for experiment in document['experiments']: experiment['worktree'] = ''
    # Only local checkout paths are removed. Case inputs and command provenance remain; review before sharing.
    validate(document)
    atomic_json(Path(args.output), document)
    emit({'output': str(Path(args.output).resolve()), 'experiments': len(document['experiments']), 'runs': len(document['runs'])})


class TerminationRequested(BaseException):
    def __init__(self, signum):
        self.signum = signum
        super().__init__('Interrupted by ' + signal.Signals(signum).name)


def handle_termination(signum, _frame):
    # A second graceful termination must not interrupt process cleanup or ledger finalization.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise TerminationRequested(signum)


def main():
    previous_sigterm = signal.signal(signal.SIGTERM, handle_termination)
    try:
        args = parser().parse_args()
        args.func(args)
        return 0
    except (BenchError, OSError) as exc:
        print('bench: ' + str(exc), file=sys.stderr)
        return 2
    except TerminationRequested as exc:
        print('bench: ' + str(exc) + '; interrupted run evidence retained', file=sys.stderr)
        return 128 + exc.signum
    except KeyboardInterrupt:
        print('bench: interrupted; partial results retained', file=sys.stderr)
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)

if __name__ == '__main__': raise SystemExit(main())
