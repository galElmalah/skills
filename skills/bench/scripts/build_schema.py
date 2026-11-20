#!/usr/bin/env python3
"""Generate the shared JSON contract. Run after changing this source."""
import json
from pathlib import Path

S = {'type': 'string'}
N = {'type': 'number'}
I = {'type': 'integer', 'minimum': 0}
ID = {'type': 'string', 'pattern': r'^[A-Za-z][A-Za-z0-9._-]{0,79}$'}
TIME = {'type': 'string', 'format': 'date-time'}
COMMIT = {'type': 'string', 'pattern': '^[0-9a-f]{40,64}$'}
NULL = {'type': 'null'}
def enum(*items): return {'type': 'string', 'enum': list(items)}
def array(item, **kw): return {'type': 'array', 'items': item, **kw}
def ref(name): return {'$ref': '#/$defs/' + name}
def nullable(value): return {'anyOf': [value, NULL]}
def obj(fields, optional=()):
    return {'type': 'object', 'properties': fields, 'required': [k for k in fields if k not in optional], 'additionalProperties': False}

metric = obj({
    'id': ID, 'label': S, 'description': S, 'unit': S,
    'direction': enum('lower', 'higher'), 'role': enum('objective', 'guardrail', 'diagnostic'),
    'aggregation': enum('mean', 'median', 'p95', 'sum', 'rate'),
    'observationPolicy': enum('matched', 'variable'),
    'minImprovementPct': {'type': 'number', 'minimum': 0},
    'maxRegressionPct': {'type': 'number', 'minimum': 0}, 'target': N,
    'scopeIds': array(ID, minItems=1, uniqueItems=True),
    'format': obj({'precision': {'type': 'integer', 'minimum': 0, 'maximum': 8}, 'style': enum('number', 'percent', 'currency')}),
}, optional=('scopeIds', 'target', 'maxRegressionPct', 'observationPolicy'))
scope = obj({'id': ID, 'label': S, 'kind': enum('endpoint', 'workload', 'system'), 'weight': {'type': 'number', 'exclusiveMinimum': 0}, 'description': S})
case = obj({'id': ID, 'group': ID, 'scopeId': ID, 'partition': enum('train', 'heldout'), 'input': {}})
suite = obj({'id': enum('screen', 'full', 'heldout'), 'label': S, 'caseIds': array(ID, minItems=1, uniqueItems=True)})
event = obj({'timestamp': TIME, 'kind': enum('created', 'snapshot', 'run', 'decision', 'promotion', 'note'), 'message': S})
artifact = obj({'kind': enum('diff', 'log', 'trace', 'profile', 'report', 'other'), 'label': S, 'path': S})
experiment = obj({
    'id': ID, 'label': S, 'parentId': nullable(ID), 'parentCommit': nullable(COMMIT), 'commit': COMMIT,
    'contributionIds': {**array(ID, uniqueItems=True), 'description': 'Experiments whose changes were explicitly incorporated into this snapshot, distinct from its starting parent. Omitted means no contributions are recorded.'},
    'status': enum('planned', 'running', 'measured', 'failed', 'promoted', 'discarded'),
    'createdAt': TIME, 'hypothesis': S, 'change': S, 'decision': nullable(S), 'worktree': S, 'branch': S,
    'artifacts': array(ref('Artifact')), 'events': array(ref('Event')),
}, optional=('contributionIds',))
sample = obj({
    'caseId': ID, 'scopeId': ID, 'repeat': I, 'warmup': {'type': 'boolean'},
    'status': enum('ok', 'error', 'timeout'),
    'metrics': {'type': 'object', 'additionalProperties': {'anyOf': [N, array(N, minItems=1, maxItems=100000)]}},
    'durationMs': {'type': 'number', 'minimum': 0}, 'error': nullable(S),
})
run = obj({
    'id': ID, 'experimentId': ID, 'suiteId': enum('screen', 'full', 'heldout'), 'commit': COMMIT,
    'protocolHash': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'startedAt': TIME, 'endedAt': nullable(TIME),
    'status': enum('running', 'completed', 'failed'), 'samples': array(ref('Sample')),
    'environment': {'type': 'object', 'additionalProperties': S}, 'command': array(S), 'logPath': S,
})
protocol = obj({'seed': I, 'repetitions': {'type': 'integer', 'minimum': 2, 'maximum': 10000}, 'warmups': {'type': 'integer', 'minimum': 0, 'maximum': 1000}, 'timeoutSeconds': {'type': 'number', 'exclusiveMinimum': 0}, 'measurementWorkers': {'const': 1}, 'splitHash': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}})
schema = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    '$id': 'https://bench.local/schema/benchmark.schema.json',
    'title': 'BenchmarkStudy',
    **obj({
        'schemaVersion': {'const': 1}, 'id': ID, 'title': S, 'description': S,
        'createdAt': TIME, 'updatedAt': TIME,
        'repository': obj({'path': S, 'baselineCommit': COMMIT, 'championCommit': COMMIT, 'championBranch': S}),
        'protocol': ref('Protocol'), 'protocolHash': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
        'mainMetricId': {**ID, 'description': 'The objective metric this study aims to improve. Frozen with the evaluation protocol.'},
        'metrics': array(ref('Metric'), minItems=1), 'scopes': array(ref('Scope'), minItems=1),
        'cases': array(ref('Case'), minItems=1), 'suites': array(ref('Suite'), minItems=3, maxItems=3),
        'experiments': array(ref('Experiment'), minItems=1), 'runs': array(ref('Run')),
    }, optional=('mainMetricId',)),
    '$defs': {'Metric': metric, 'Scope': scope, 'Case': case, 'Suite': suite, 'Event': event, 'Artifact': artifact, 'Experiment': experiment, 'Sample': sample, 'Run': run, 'Protocol': protocol}
}
if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'schema' / 'benchmark.schema.json'
    path.write_text(json.dumps(schema, indent=2) + '\n')
    print(path)
