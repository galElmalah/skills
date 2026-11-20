"""Shared validation, immutable study storage, and scope-aware analysis."""
from __future__ import annotations
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schema/benchmark.schema.json').read_text())

class BenchError(Exception):
    pass

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def digest(value):
    """Portable canonical JSON fingerprint shared with the browser (IEEE-754 numbers)."""
    def encode(item):
        if item is None: return ['null']
        if isinstance(item, bool): return ['boolean', item]
        if isinstance(item, str): return ['string', item]
        if isinstance(item, (int, float)):
            try: number = float(item)
            except OverflowError as exc: raise BenchError('Number exceeds binary64 range') from exc
            if not math.isfinite(number): raise BenchError('Non-finite number')
            return ['number', struct.pack('>d', number).hex()]
        if isinstance(item, list): return ['array', *[encode(child) for child in item]]
        if isinstance(item, dict): return ['object', [[key, encode(item[key])] for key in sorted(item)]]
        raise BenchError('Unsupported JSON value')
    return hashlib.sha256(json.dumps(encode(value), ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def read_json(path):
    try:
        return json.loads(Path(path).read_text(), parse_constant=lambda value: (_ for _ in ()).throw(BenchError('Non-finite JSON number: ' + value)))
    except (OSError, ValueError) as exc:
        raise BenchError(f'Cannot read {path}: {exc}') from exc

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, allow_nan=False) + '\n'
    fd, name = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def git(repo, *args, check=True):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
    if check and result.returncode:
        raise BenchError(result.stderr.strip() or result.stdout.strip() or 'Git command failed')
    return result.stdout.strip()

def protocol_hash(document):
    contract = {key: document[key] for key in ('protocol', 'metrics', 'scopes', 'cases', 'suites')}
    if 'mainMetricId' in document: contract['mainMetricId'] = document['mainMetricId']
    return digest(contract)

def validate_shape(value, schema, path='$'):
    """Validate the JSON Schema vocabulary used by the checked-in v1 contract."""
    if '$ref' in schema:
        return validate_shape(value, SCHEMA['$defs'][schema['$ref'].rsplit('/', 1)[1]], path)
    if 'anyOf' in schema:
        for option in schema['anyOf']:
            try:
                validate_shape(value, option, path)
                return
            except BenchError:
                pass
        raise BenchError(f'{path}: does not match any permitted type')
    if 'const' in schema and (value != schema['const'] or type(value) is not type(schema['const'])):
        raise BenchError(f'{path}: expected {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']:
        raise BenchError(f'{path}: expected one of {schema["enum"]}')
    kind = schema.get('type')
    finite_number = type(value) in (int, float) and -sys.float_info.max <= value <= sys.float_info.max
    valid = {'object': isinstance(value, dict), 'array': isinstance(value, list), 'string': isinstance(value, str), 'number': finite_number, 'integer': isinstance(value, int) and not isinstance(value, bool), 'boolean': isinstance(value, bool), 'null': value is None}
    if kind and not valid[kind]: raise BenchError(f'{path}: expected {kind}')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value: raise BenchError(f'{path}.{key}: required')
        for key, item in value.items():
            if key in schema.get('properties', {}): validate_shape(item, schema['properties'][key], f'{path}.{key}')
            elif schema.get('additionalProperties') is False: raise BenchError(f'{path}.{key}: unexpected field')
            elif isinstance(schema.get('additionalProperties'), dict): validate_shape(item, schema['additionalProperties'], f'{path}.{key}')
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', math.inf): raise BenchError(f'{path}: invalid item count')
        if schema.get('uniqueItems') and len({digest(item) for item in value}) != len(value): raise BenchError(f'{path}: duplicate items')
        for index, item in enumerate(value): validate_shape(item, schema.get('items', {}), f'{path}[{index}]')
    elif kind == 'string':
        if 'pattern' in schema and not re.search(schema['pattern'], value): raise BenchError(f'{path}: invalid format')
        if schema.get('format') == 'date-time':
            try:
                parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
                if parsed.tzinfo is None: raise ValueError('timezone required')
            except ValueError as exc: raise BenchError(f'{path}: expected timestamp with timezone') from exc
    elif kind in ('integer', 'number'):
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf) or value <= schema.get('exclusiveMinimum', -math.inf): raise BenchError(f'{path}: outside permitted range')

def unique_index(items, name):
    index = {}
    for item in items:
        if item['id'] in index: raise BenchError(f'Duplicate {name} id: {item["id"]}')
        index[item['id']] = item
    return index

def validate(document):
    validate_shape(document, SCHEMA)
    metrics = unique_index(document['metrics'], 'metric')
    scopes = unique_index(document['scopes'], 'scope')
    cases = unique_index(document['cases'], 'case')
    suites = unique_index(document['suites'], 'suite')
    experiments = unique_index(document['experiments'], 'experiment')
    unique_index(document['runs'], 'run')
    if not any(metric['role'] == 'objective' for metric in metrics.values()): raise BenchError('At least one objective metric is required')
    if 'mainMetricId' in document:
        main_metric = metrics.get(document['mainMetricId'])
        if main_metric is None or main_metric['role'] != 'objective': raise BenchError('Main metric must reference an objective metric')
    if set(suites) != {'screen', 'full', 'heldout'}: raise BenchError('Exactly screen, full, and heldout suites are required')
    groups = {}
    for case in cases.values():
        if case['scopeId'] not in scopes: raise BenchError('Unknown case scope: ' + case['scopeId'])
        if case['group'] in groups and groups[case['group']] != case['partition']: raise BenchError('Related case group crosses train/heldout split: ' + case['group'])
        groups[case['group']] = case['partition']
    for suite in suites.values():
        if any(case_id not in cases for case_id in suite['caseIds']): raise BenchError('Suite contains unknown case')
        expected = 'heldout' if suite['id'] == 'heldout' else 'train'
        if any(cases[case_id]['partition'] != expected for case_id in suite['caseIds']): raise BenchError('Suite leaks the held-out partition')
    if set(suites['full']['caseIds']) != {case['id'] for case in cases.values() if case['partition'] == 'train'}: raise BenchError('Full suite must contain all training cases')
    if set(suites['heldout']['caseIds']) != {case['id'] for case in cases.values() if case['partition'] == 'heldout'}: raise BenchError('Held-out suite must contain all held-out cases')
    if not set(suites['screen']['caseIds']) <= set(suites['full']['caseIds']): raise BenchError('Screen suite must be a training subset')
    for metric in metrics.values():
        if metric['role'] == 'guardrail' and 'target' not in metric and 'maxRegressionPct' not in metric: raise BenchError('Guardrail metric requires target or maxRegressionPct: ' + metric['id'])
        if any(scope_id not in scopes for scope_id in metric.get('scopeIds', scopes)): raise BenchError('Metric references an unknown scope')
    for scope in scopes:
        if not any(case['scopeId'] == scope and case['partition'] == 'train' for case in cases.values()): raise BenchError('Every scope needs training cases')
        if not any(case['scopeId'] == scope and case['partition'] == 'heldout' for case in cases.values()): raise BenchError('Every scope needs held-out cases')
    roots = [experiment for experiment in experiments.values() if experiment['parentId'] is None]
    if len(roots) != 1 or roots[0]['commit'] != document['repository']['baselineCommit']: raise BenchError('Exactly one frozen baseline experiment is required')
    if roots[0]['parentCommit'] is not None: raise BenchError('Baseline must not have a parent snapshot')
    if roots[0].get('contributionIds'): raise BenchError('Baseline must not have contributions')
    dependents = {ident: [] for ident in experiments}
    dependency_counts = {}
    for experiment in experiments.values():
        if experiment['parentId'] is not None:
            parent = experiments.get(experiment['parentId'])
            if not parent or experiment['parentCommit'] != parent['commit']: raise BenchError('Experiment parent snapshot mismatch: ' + experiment['id'])
        contributions = experiment.get('contributionIds', [])
        for contribution in contributions:
            if contribution not in experiments: raise BenchError('Unknown experiment contribution: ' + contribution)
            if contribution == experiment['id']: raise BenchError('Experiment cannot contribute to itself: ' + contribution)
            if contribution == roots[0]['id']: raise BenchError('Baseline cannot be a contribution')
        dependencies = set(contributions)
        if experiment['parentId'] is not None: dependencies.add(experiment['parentId'])
        dependency_counts[experiment['id']] = len(dependencies)
        for dependency in dependencies: dependents[dependency].append(experiment['id'])
    ready = [ident for ident, count in dependency_counts.items() if count == 0]
    for ident in ready:
        for dependent in dependents[ident]:
            dependency_counts[dependent] -= 1
            if dependency_counts[dependent] == 0: ready.append(dependent)
    if len(ready) != len(experiments): raise BenchError('Experiment lineage contains a cycle in parent or contribution links')
    if document['repository']['championCommit'] not in {experiment['commit'] for experiment in experiments.values()}: raise BenchError('Champion is not a recorded snapshot')
    if document['protocol']['splitHash'] != digest(document['cases']): raise BenchError('Case split fingerprint changed; start a new study')
    if document['protocolHash'] != protocol_hash(document): raise BenchError('Frozen protocol fingerprint changed; start a new study')
    for run in document['runs']:
        if run['experimentId'] not in experiments or run['suiteId'] not in suites: raise BenchError('Run references unknown experiment or suite')
        if run['commit'] != experiments[run['experimentId']]['commit'] or run['protocolHash'] != document['protocolHash']: raise BenchError('Run snapshot or protocol provenance mismatch')
        seen = set()
        for sample in run['samples']:
            case = cases.get(sample['caseId'])
            if not case or case['scopeId'] != sample['scopeId'] or case['id'] not in suites[run['suiteId']]['caseIds']: raise BenchError('Sample is outside its suite or scope')
            key = (sample['caseId'], sample['repeat'], sample['warmup'])
            if key in seen: raise BenchError('Duplicate case/repeat sample')
            seen.add(key)
            if sample['repeat'] >= document['protocol']['warmups' if sample['warmup'] else 'repetitions']: raise BenchError('Sample repeat exceeds protocol')
            if sample['status'] != 'ok' and (sample['error'] is None or sample['metrics']): raise BenchError('Failed samples must record error and no success metrics')
            if sample['status'] == 'ok' and sample['error'] is not None: raise BenchError('Successful sample must not contain an error')
            for metric_id in sample['metrics']:
                if metric_id not in metrics or sample['scopeId'] not in metrics[metric_id].get('scopeIds', scopes): raise BenchError('Unknown or inapplicable sample metric: ' + metric_id)
                observations = sample['metrics'][metric_id] if isinstance(sample['metrics'][metric_id], list) else [sample['metrics'][metric_id]]
                if metrics[metric_id]['aggregation'] == 'rate' and any(value < 0 or value > 1 for value in observations): raise BenchError('Rate observations must be fractions from 0 to 1: ' + metric_id)
        if run['status'] == 'running' and run['endedAt'] is not None: raise BenchError('Running run cannot have an end time')
        if run['status'] != 'running' and run['endedAt'] is None: raise BenchError('Terminal run needs an end time')
    return document

class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.path = self.directory / 'study.json'
    def load(self): return validate(read_json(self.path))
    def save(self, document):
        document['updatedAt'] = now()
        validate(document)
        atomic_json(self.path, document)
    @contextlib.contextmanager
    def lock(self):
        if not self.directory.is_dir(): raise BenchError('Study directory does not exist; initialize it first')
        with (self.directory / '.lock').open('a') as handle:
            try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc: raise BenchError('Study is busy: another operation owns its measurement lock') from exc
            try: yield
            finally: fcntl.flock(handle, fcntl.LOCK_UN)
    def managed(self, document, allow_pending=False):
        if not allow_pending and (self.directory / '.promotion.json').exists(): raise BenchError('Promotion was interrupted; retry the same promote command to recover')
        control = read_json(self.directory / '.managed.json')
        if control.get('protocolHash') != document['protocolHash'] or control.get('repository') != document['repository']['path']: raise BenchError('This is an imported report, not the matching managed study')
        return control

def aggregate(values, method):
    if not values: return None
    if method == 'sum': return sum(values)
    if method in ('mean', 'rate'): return statistics.mean(values)
    if method == 'median': return statistics.median(values)
    ordered = sorted(values)
    index = .95 * (len(ordered) - 1)
    lo = math.floor(index)
    return ordered[lo] + (ordered[math.ceil(index)] - ordered[lo]) * (index - lo)

def latest_run(document, experiment_id, suite_id):
    return next((run for run in reversed(document['runs']) if run['experimentId'] == experiment_id and run['suiteId'] == suite_id), None)

def summary(document, run, metric, scope_id):
    if not run: return None
    samples = [sample for sample in run['samples'] if not sample['warmup'] and sample['scopeId'] == scope_id]
    values_by_repeat = {}
    observations = 0
    for sample in samples:
        if sample['status'] != 'ok' or metric['id'] not in sample['metrics']: continue
        value = sample['metrics'][metric['id']]
        values = value if isinstance(value, list) else [value]
        values_by_repeat.setdefault(sample['repeat'], []).extend(values)
        observations += len(values)
    repeats = [aggregate(values_by_repeat[key], metric['aggregation']) for key in sorted(values_by_repeat)]
    if not repeats: return None
    return {'value': statistics.median(repeats), 'repeatValues': repeats, 'range': [min(repeats), max(repeats)], 'observations': observations, 'caseCount': len({sample['caseId'] for sample in samples if sample['status'] == 'ok'}), 'failures': sum(sample['status'] != 'ok' for sample in samples), 'repetitions': len(repeats)}

def coverage_problems(document, run, label):
    if not run: return [f'{label}: no run for this suite']
    problems = []
    if run['status'] != 'completed': problems.append(f'{label}: run {run["status"]}')
    suite = next(suite for suite in document['suites'] if suite['id'] == run['suiteId'])
    samples = {(sample['caseId'], sample['repeat']): sample for sample in run['samples'] if not sample['warmup']}
    cases = {case['id']: case for case in document['cases']}
    for case_id in suite['caseIds']:
        for repeat in range(document['protocol']['repetitions']):
            sample = samples.get((case_id, repeat))
            if not sample or sample['status'] != 'ok':
                problems.append(f'{label}: missing or failed {case_id} repeat {repeat}')
                continue
            for metric in document['metrics']:
                if cases[case_id]['scopeId'] in metric.get('scopeIds', [scope['id'] for scope in document['scopes']]) and metric['id'] not in sample['metrics']:
                    problems.append(f'{label}: {case_id} repeat {repeat} missing {metric["id"]}')
    return problems

def analyze(document, experiment_id, suite_id='full', reference_id=None):
    validate(document)
    experiment = next((experiment for experiment in document['experiments'] if experiment['id'] == experiment_id), None)
    if not experiment: raise BenchError('Unknown experiment: ' + experiment_id)
    reference_id = reference_id or experiment['parentId']
    if reference_id is None: raise BenchError('Baseline has no parent; provide --reference explicitly')
    if reference_id == experiment_id: raise BenchError('Cannot compare an experiment with itself')
    if reference_id not in {item['id'] for item in document['experiments']}: raise BenchError('Unknown reference experiment')
    current_run = latest_run(document, experiment_id, suite_id)
    reference_run = latest_run(document, reference_id, suite_id)
    reasons = coverage_problems(document, current_run, 'Candidate') + coverage_problems(document, reference_run, 'Reference')
    if current_run and reference_run:
        for key in ('profile', 'platform', 'architecture', 'cpuCount', 'runtime', 'load'):
            if not current_run['environment'].get(key) or not reference_run['environment'].get(key):
                reasons.append(f'Environment {key}: missing comparison provenance')
            elif current_run['environment'][key] != reference_run['environment'][key]:
                reasons.append(f'Environment {key}: candidate and reference differ')
        if current_run['command'] != reference_run['command']:
            reasons.append('Adapter commands differ; use a consistent harness')
    if current_run and reference_run:
        references = {(sample['caseId'], sample['repeat']): sample for sample in reference_run['samples'] if not sample['warmup'] and sample['status'] == 'ok'}
        for sample in current_run['samples']:
            if sample['warmup'] or sample['status'] != 'ok': continue
            reference_sample = references.get((sample['caseId'], sample['repeat']))
            if not reference_sample: continue
            for metric in document['metrics']:
                if metric.get('observationPolicy', 'matched') == 'variable': continue
                if metric['id'] not in sample['metrics'] or metric['id'] not in reference_sample['metrics']: continue
                current_values = sample['metrics'][metric['id']]
                reference_values = reference_sample['metrics'][metric['id']]
                current_count = len(current_values) if isinstance(current_values, list) else 1
                reference_count = len(reference_values) if isinstance(reference_values, list) else 1
                if current_count != reference_count:
                    reasons.append(f'{sample["scopeId"]} / {metric["id"]}: observation count differs for {sample["caseId"]} repeat {sample["repeat"]} (candidate {current_count}, reference {reference_count})')
    blocked = bool(reasons)
    any_clear_gain = False
    main_clear_gain = False
    main_metric_id = document.get('mainMetricId')
    objective_regression = False
    cells = []
    for scope in document['scopes']:
        for metric in document['metrics']:
            if scope['id'] not in metric.get('scopeIds', [item['id'] for item in document['scopes']]): continue
            current = summary(document, current_run, metric, scope['id'])
            reference = summary(document, reference_run, metric, scope['id'])
            cell = {'scopeId': scope['id'], 'metricId': metric['id'], 'current': current, 'reference': reference, 'absoluteChange': None, 'relativeChangePct': None, 'improvementPct': None, 'signal': 'insufficient', 'assessment': 'missing'}
            if not current or not reference:
                reasons.append(f'{scope["label"]} / {metric["label"]}: missing evidence')
                blocked = True
                cells.append(cell)
                continue
            delta = current['value'] - reference['value']
            relative = delta / abs(reference['value']) * 100 if reference['value'] else None
            sign = -1 if metric['direction'] == 'lower' else 1
            improvement = relative * sign if relative is not None else None
            clear = current['range'][1] < reference['range'][0] or current['range'][0] > reference['range'][1]
            conservative_delta = (reference['range'][0] - current['range'][1]) if sign == -1 else (current['range'][0] - reference['range'][1])
            conservative_pct = conservative_delta / abs(reference['value']) * 100 if reference['value'] else None
            cell.update(absoluteChange=delta, relativeChangePct=relative, improvementPct=improvement, signal='clear' if clear else 'overlap', assessment='improved' if delta * sign > 0 else 'regressed' if delta * sign < 0 else 'unchanged')
            target_failed = 'target' in metric and ((sign == -1 and current['value'] > metric['target']) or (sign == 1 and current['value'] < metric['target']))
            regression_failed = 'maxRegressionPct' in metric and ((improvement is not None and improvement < -metric['maxRegressionPct'] - 1e-9) or (improvement is None and delta * sign < -1e-12))
            if metric['role'] != 'diagnostic' and (target_failed or regression_failed):
                cell['assessment'] = 'guardrail_failed'
                blocked = True
                reasons.append(f'{scope["label"]} / {metric["label"]}: target or regression constraint failed')
            if metric['role'] == 'objective':
                objective_regression |= delta * sign < -1e-12
                if clear and conservative_pct is not None and conservative_pct >= metric['minImprovementPct'] and conservative_pct > 0:
                    any_clear_gain = True
                    if metric['id'] == main_metric_id: main_clear_gain = True
            cells.append(cell)
    required_gain = main_clear_gain if main_metric_id is not None else any_clear_gain
    verdict = 'blocked' if blocked else 'tradeoff' if objective_regression and any_clear_gain else 'inconclusive' if not required_gain or objective_regression else 'feasible'
    if verdict == 'tradeoff': reasons.append('Objectives conflict across scopes; no automatic promotion')
    if verdict == 'inconclusive': reasons.append('No meaningful separated improvement in the main metric; other gains do not satisfy the study objective' if main_metric_id is not None and not main_clear_gain else 'No unambiguous improvement without objective regression; repeat ranges may overlap')
    if verdict == 'feasible': reasons.append('Main metric has a meaningful separated improvement; all scope constraints pass and no objective worsens' if main_metric_id is not None else 'At least one meaningful separated objective improvement; all scope constraints pass and no objective worsens')
    return {'experimentId': experiment_id, 'referenceId': reference_id, 'suiteId': suite_id, 'verdict': verdict, 'eligible': verdict == 'feasible', 'reasons': reasons, 'method': 'median-of-repeat-aggregates; repeat-range separation (not a confidence interval)', 'cells': cells}
