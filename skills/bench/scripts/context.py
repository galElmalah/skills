"""Read-only, evidence-derived context for resuming an optimization study."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core import BenchError, analyze, coverage_problems, latest_run, read_json, summary, validate

DETAIL_LIMIT = 12


def _timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def _champion(document):
    matches = [item for item in document['experiments'] if item['commit'] == document['repository']['championCommit']]
    promoted = [item for item in matches if item['status'] == 'promoted']
    if promoted:
        return max(promoted, key=lambda item: (max([_timestamp(item['createdAt']), *[_timestamp(event['timestamp']) for event in item['events'] if event['kind'] == 'promotion']]), item['id']))
    return next((item for item in matches if item['parentId'] is None), None) or max(matches, key=lambda item: (_timestamp(item['createdAt']), item['id']))


def _applies(metric, scope_id):
    return 'scopeIds' not in metric or scope_id in metric['scopeIds']


def _comparison_problems(document, current, reference):
    problems = coverage_problems(document, current, 'Candidate') + coverage_problems(document, reference, 'Reference')
    if not current or not reference:
        return problems
    for key in ('profile', 'platform', 'architecture', 'cpuCount', 'runtime', 'load'):
        if not current['environment'].get(key) or not reference['environment'].get(key):
            problems.append(f'Environment {key}: missing comparison provenance')
        elif current['environment'][key] != reference['environment'][key]:
            problems.append(f'Environment {key}: candidate and reference differ')
    if current['command'] != reference['command']:
        problems.append('Adapter commands differ; use a consistent harness')
    references = {(sample['caseId'], sample['repeat']): sample for sample in reference['samples'] if not sample['warmup'] and sample['status'] == 'ok'}
    for sample in current['samples']:
        if sample['warmup'] or sample['status'] != 'ok':
            continue
        previous = references.get((sample['caseId'], sample['repeat']))
        if previous is None:
            continue
        for metric in document['metrics']:
            if metric.get('observationPolicy', 'matched') == 'variable' or metric['id'] not in sample['metrics'] or metric['id'] not in previous['metrics']:
                continue
            value, before = sample['metrics'][metric['id']], previous['metrics'][metric['id']]
            count, before_count = len(value) if isinstance(value, list) else 1, len(before) if isinstance(before, list) else 1
            if count != before_count:
                problems.append(f'{sample["scopeId"]} / {metric["id"]}: observation count differs for {sample["caseId"]} repeat {sample["repeat"]}')
    return problems


def _comparison(document, experiment, suite_id, reference_id, main):
    if reference_id is None or reference_id == experiment['id']:
        return None
    current = latest_run(document, experiment['id'], suite_id)
    reference = latest_run(document, reference_id, suite_id)
    issues = _comparison_problems(document, current, reference)
    result = analyze(document, experiment['id'], suite_id, reference_id)
    effects = []
    if not issues:
        for cell in result['cells']:
            if cell['metricId'] == main['id']:
                effects.append({key: cell[key] for key in ('scopeId', 'absoluteChange', 'relativeChangePct', 'improvementPct', 'signal', 'assessment')})
    return {
        'referenceExperimentId': reference_id,
        'referenceRunId': reference['id'] if reference else None,
        'comparable': not issues,
        'issues': issues[:DETAIL_LIMIT], 'issueCount': len(issues),
        'mainMetricEffects': effects,
        'measuredGate': {'verdict': result['verdict'], 'satisfied': result['eligible'], 'reasons': result['reasons'][:DETAIL_LIMIT], 'reasonCount': len(result['reasons'])},
    }


def _main_result(document, run, metric, scope_id):
    result = summary(document, run, metric, scope_id)
    return {key: value for key, value in result.items() if key != 'repeatValues'} if result else None


def _guardrail_evidence(document, experiment, run, issues, parent_comparison):
    reference = latest_run(document, experiment['parentId'], run['suiteId']) if experiment['parentId'] is not None else None
    guards = []
    for metric in document['metrics']:
        if metric['role'] != 'guardrail':
            continue
        for scope in document['scopes']:
            if not _applies(metric, scope['id']):
                continue
            observed = None if issues else _main_result(document, run, metric, scope['id'])
            target = {'status': 'not-configured'}
            if 'target' in metric:
                target['value'] = metric['target']
                target['status'] = 'unavailable'
                if observed is not None:
                    passed = observed['value'] <= metric['target'] if metric['direction'] == 'lower' else observed['value'] >= metric['target']
                    target['status'] = 'passed' if passed else 'failed'
            regression = {'status': 'not-configured'}
            if 'maxRegressionPct' in metric:
                regression.update(maxRegressionPct=metric['maxRegressionPct'], referenceExperimentId=experiment['parentId'], referenceRunId=reference['id'] if reference else None)
                if experiment['parentId'] is None:
                    regression['status'] = 'reference-required'
                elif observed is None or not parent_comparison or not parent_comparison['comparable']:
                    regression['status'] = 'unavailable'
                else:
                    before = summary(document, reference, metric, scope['id'])
                    if before is None:
                        regression['status'] = 'unavailable'
                    else:
                        sign = -1 if metric['direction'] == 'lower' else 1
                        change = (observed['value'] - before['value']) * sign
                        improvement = change / abs(before['value']) * 100 if before['value'] else None
                        failed = improvement < -metric['maxRegressionPct'] - 1e-9 if improvement is not None else change < -1e-12
                        regression.update(status='failed' if failed else 'passed', referenceValue=before['value'], improvementPct=improvement)
            statuses = (target['status'], regression['status'])
            status = next((state for state in ('failed', 'unavailable', 'reference-required') if state in statuses), 'passed')
            guards.append({'metricId': metric['id'], 'scopeId': scope['id'], 'observed': observed, 'status': status, 'target': target, 'regression': regression})
    return guards


def _suite_evidence(document, experiment, suite_id, main, baseline):
    runs = [run for run in document['runs'] if run['experimentId'] == experiment['id'] and run['suiteId'] == suite_id]
    run = runs[-1] if runs else None
    suite = next(item for item in document['suites'] if item['id'] == suite_id)
    evidence = {
        'suiteId': suite_id, 'attempts': len(runs), 'latestRunId': run['id'] if run else None,
        'status': run['status'] if run else 'not-run',
        'expectedCases': len(suite['caseIds']), 'expectedRepetitions': document['protocol']['repetitions'],
    }
    if run is None:
        return evidence
    samples = [sample for sample in run['samples'] if not sample['warmup']]
    issues = coverage_problems(document, run, 'Latest run')
    parent_comparison = _comparison(document, experiment, suite_id, experiment['parentId'], main)
    evidence.update({
        'command': run['command'], 'environment': run['environment'],
        'startedAt': run['startedAt'], 'endedAt': run['endedAt'],
        'scoredSamples': len(samples), 'warmupSamples': len(run['samples']) - len(samples),
        'measuredCases': len({sample['caseId'] for sample in samples}),
        'sampleCounts': {status: sum(sample['status'] == status for sample in samples) for status in ('ok', 'error', 'timeout')},
        'coverageIssues': issues[:DETAIL_LIMIT], 'coverageIssueCount': len(issues),
        'mainMetric': [
            {'scopeId': scope['id'], 'result': None if issues else _main_result(document, run, main, scope['id'])}
            for scope in document['scopes'] if _applies(main, scope['id'])
        ],
        'guardrails': _guardrail_evidence(document, experiment, run, issues, parent_comparison),
        'versusParent': parent_comparison,
        'versusBaseline': _comparison(document, experiment, suite_id, baseline['id'], main) if experiment['parentId'] != baseline['id'] else {'sameAs': 'versusParent'},
    })
    return evidence


def build_context(document, limit=8, include_heldout=False):
    """Do not execute report commands, read artifacts, or mutate the input document.

    Notes lack suite provenance. Without explicit held-out disclosure, expose only
    pointers to them; attempting to detect feedback by its wording is unreliable.
    """
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise BenchError('Context limit must be between 1 and 100')
    validate(document)
    baseline = next(item for item in document['experiments'] if item['parentId'] is None)
    champion = _champion(document)
    main = next((metric for metric in document['metrics'] if metric['id'] == document.get('mainMetricId')), None)
    main = main or next(metric for metric in document['metrics'] if metric['role'] == 'objective')
    ordered = sorted(enumerate(document['experiments']), key=lambda entry: (_timestamp(entry[1]['createdAt']), entry[1]['id']))
    recent = [experiment for _, experiment in ordered[-limit:]]
    selected = {baseline['id'], champion['id'], *[item['id'] for item in recent]}
    suite_ids = ('screen', 'full', 'heldout') if include_heldout else ('screen', 'full')
    records = []
    for index, experiment in ordered:
        if experiment['id'] not in selected:
            continue
        pointer = f'/experiments/{index}'
        notes = [(event_index, event) for event_index, event in enumerate(experiment['events']) if event['kind'] in ('note', 'decision', 'promotion')]
        artifacts = list(enumerate(experiment['artifacts']))
        record = {
            'id': experiment['id'], 'commit': experiment['commit'], 'parentId': experiment['parentId'],
            'status': experiment['status'], 'isBaseline': experiment['id'] == baseline['id'],
            'isCurrentChampion': experiment['id'] == champion['id'], 'createdAt': experiment['createdAt'],
            'evidence': [_suite_evidence(document, experiment, suite_id, main, baseline) for suite_id in suite_ids],
            'decisionPointer': pointer + '/decision' if experiment['decision'] is not None else None,
            'noteCount': len(notes), 'artifactCount': len(artifacts),
            'notes': [
                {'pointer': f'{pointer}/events/{event_index}', 'kind': event['kind'], 'timestamp': event['timestamp'],
                 **({'message': event['message']} if include_heldout else {})}
                for event_index, event in notes[-DETAIL_LIMIT:]
            ],
            'artifacts': [
                {'pointer': f'{pointer}/artifacts/{artifact_index}', 'kind': artifact['kind'],
                 **({'label': artifact['label'], 'path': artifact['path']} if include_heldout else {})}
                for artifact_index, artifact in artifacts[-DETAIL_LIMIT:]
            ],
        }
        if 'contributionIds' in experiment:
            record['contributionIds'] = experiment['contributionIds']
        if include_heldout:
            record.update({key: experiment[key] for key in ('label', 'hypothesis', 'change', 'decision')})
        records.append(record)
    result = {
        'contextVersion': 1,
        'study': {'id': document['id'], 'updatedAt': document['updatedAt'], 'protocolHash': document['protocolHash']},
        'mainMetricId': main['id'],
        'mainMetricSource': 'declared' if 'mainMetricId' in document else 'first-objective-display-default',
        'metrics': [{key: value for key, value in metric.items() if key not in ('description', 'format')} for metric in document['metrics']],
        'scopes': [{key: scope[key] for key in ('id', 'label', 'kind')} for scope in document['scopes']],
        'protocol': document['protocol'],
        'baselineId': baseline['id'], 'championId': champion['id'],
        'window': {'recentLimit': limit, 'order': 'createdAt ascending, then id', 'totalExperiments': len(document['experiments']), 'includedExperiments': len(records), 'baselineAndChampionAlwaysIncluded': True},
        'heldoutIncluded': include_heldout,
        'freeTextIncluded': include_heldout,
        'limitations': [
            'Default context omits reserved case inputs, held-out runs, and unclassified free text. Note pointers are not instructions to read withheld feedback.',
            'Measured gates describe evidence, not permission to promote; current-parent and repository checks still apply.',
            'Budget, stopping rules, next-action hints, and held-out exposure are not structured report fields; consult the approved plan without inspecting reserved feedback.',
            'Repeat ranges are variability summaries, not confidence intervals.',
            f'Issue lists and recent note/artifact pointers are limited to {DETAIL_LIMIT} entries; counts retain the full totals. Raw repeat values remain in the report.',
        ],
        'experiments': records,
        'unresolvedRuns': [
            {'id': run['id'], 'experimentId': run['experimentId'], 'suiteId': run['suiteId'], 'startedAt': run['startedAt']}
            for run in document['runs'] if run['status'] == 'running' and run['suiteId'] in suite_ids
        ],
    }
    if include_heldout:
        result['study'].update({key: document[key] for key in ('title', 'description')})
    return result


def load_context(path, limit=8, include_heldout=False):
    source = Path(path)
    return build_context(read_json(source / 'study.json' if source.is_dir() else source), limit, include_heldout)
