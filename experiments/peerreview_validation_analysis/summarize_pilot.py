"""Summarize a completed development pilot without modifying frozen inference."""

import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'runs/peerreview-validation-codex-v5'
report_path = RUN / 'report.json'
report = json.loads(report_path.read_text())
rows = report['paper_metrics']
conditions = ['one_shot', 'single_agent', 'pra_full', 'pra_no_debate']
assert len(rows) == 40
assert len({(r['paper_id'], r['condition']) for r in rows}) == 40
summary = {'phase': 'development', 'scientific_results': False,
           'source_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
           'aggregation': 'Unweighted mean of ten per-paper reference coverage fractions',
           'conditions': {}, 'paired_full_minus_baseline': {}}
for condition in conditions:
    selected = [r for r in rows if r['condition'] == condition]
    summary['conditions'][condition] = {
        'papers': len(selected),
        'mean_coverage_both': statistics.mean(r['coverage_agreement'] for r in selected),
        'mean_coverage_A': statistics.mean(r['coverage_A'] for r in selected),
        'mean_coverage_B': statistics.mean(r['coverage_B'] for r in selected),
        'mean_coverage_either': statistics.mean(r['coverage_either'] for r in selected),
        'mean_generation_tokens': statistics.mean(r['observed_tokens_including_shared_panel'] for r in selected),
        'mean_scored_quote_words': statistics.mean(r['scored_quote_word_count'] for r in selected),
        'conditions_with_complete_support_statistics': sum(r['support_statistics_complete'] for r in selected),
        'invalid_evidence_judgments': sum(r['n_invalid_evidence_A'] + r['n_invalid_evidence_B'] for r in selected),
    }
by = {(r['paper_id'], r['condition']): r for r in rows}
papers = sorted({r['paper_id'] for r in rows})
for baseline in ['one_shot', 'single_agent', 'pra_no_debate']:
    deltas = [by[(paper, 'pra_full')]['coverage_agreement'] - by[(paper, baseline)]['coverage_agreement']
              for paper in papers]
    summary['paired_full_minus_baseline'][baseline] = {
        'mean_difference': statistics.mean(deltas),
        'wins': sum(d > 0 for d in deltas), 'ties': sum(d == 0 for d in deltas),
        'losses': sum(d < 0 for d in deltas)}
usage = [json.loads(line) for path in RUN.glob('**/usage.jsonl') for line in path.read_text().splitlines()]
assert all(r['ok'] for r in usage)
summary['actual_usage'] = {'calls': len(usage),
                           'observed_tokens': sum(r.get('observed_tokens', 0) for r in usage),
                           'active_seconds': sum(r.get('elapsed_seconds', 0) for r in usage),
                           'unknown_usage_calls': sum('observed_tokens' not in r for r in usage),
                           'shared_panel_counted_once': True,
                           'excludes_connection_probes': True}
judgments = [json.loads(p.read_text()) for p in RUN.glob('evaluation/*/review_*/*/judgment.json')]
assert len(judgments) == 80
summary['support_judgments'] = sum(len(j['support']) for j in judgments)
summary['unmatched_evidence'] = sum(not r['evidence_valid'] for j in judgments for r in j['support'])
audit = json.loads((RUN / 'manual_audit/items.json').read_text())
summary['manual_audit'] = {'sample_size': len(audit['items']), 'population': audit['population'],
                           'labels': 'empty', 'unmatched_queue_is_not_an_additional_random_sample': True}
(RUN / 'aggregate_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
