"""Summarize the fixed retest without imputing a missing judgment."""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'pra_findings_debate_recovery'))
import core
import study


def main():
    root = core.ROOT
    protocol, manifest = core.verify(root)
    rows, generation, invalid_items = [], [], []
    for entry in core.read(root/'evaluation/condition_key.json'):
        pid, condition = entry['paper_id'], entry['condition']
        packet = core.read(root/'normalization'/pid/condition/'packet.json')
        review = study.review_path(root, pid, condition).read_text()
        assert core.shared.digest(review.encode()) == packet['review_sha256']
        rebuilt = core.packet_from_paragraphs({'concerns': [{'paragraph_ids': c['source_paragraph_ids']}
                                                           for c in packet['concerns']]}, review)
        assert rebuilt == packet['concerns']
        refs = core.read(root/'inputs'/pid/'reference.json')['concerns']
        manuscript = (root/'inputs'/pid/'manuscript.txt').read_text()
        judgments = {}
        for judge in ['A', 'B']:
            path = root/'evaluation'/pid/entry['anonymous_id']/judge/'judgment.json'
            if path.exists():
                value = core.read(path)
                study.validate_judgment(value, refs, packet['concerns'], manuscript)
                judgments[judge] = value
                invalid_items.extend({**entry, 'judge': judge, **r} for r in value['support'] if not r['evidence_valid'])
        matches = {j: {r['reference_id'] for r in v['matches'] if r['matched']} for j, v in judgments.items()}
        n = len(refs)
        both = len(matches['A'] & matches['B']) if len(matches) == 2 else None
        invalid = sum(not r['evidence_valid'] for v in judgments.values() for r in v['support'])
        quality_complete = len(judgments) == 2 and not invalid
        support_sets = [{r['candidate_id'] for r in judgments[j]['support'] if r['label'] == 'supported'}
                        for j in ['A', 'B']] if quality_complete else []
        false_sets = [{r['candidate_id'] for r in judgments[j]['support'] if r['label'] == 'contradicted' and r['major']}
                      for j in ['A', 'B']] if quality_complete else []
        source = 'generation' if condition == 'pra_revised' else 'saved_baselines'
        usage = [r for r in core.shared.jsonl(root/source/pid/condition/'usage.jsonl')
                 if r['label'] != 'extract_final_concerns']
        rows.append({**entry, 'reference_count': n, 'concern_count': len(packet['concerns']),
                     'matched_A': len(matches['A']) if 'A' in matches else None,
                     'matched_B': len(matches['B']) if 'B' in matches else None,
                     'matched_both': both, 'coverage_both': both/n if both is not None else None,
                     'coverage_both_bounds': [both/n, both/n] if both is not None else [0, min(map(len, matches.values()))/n],
                     'quoted_words': packet['quoted_word_count'], 'invalid_support_judgments': invalid,
                     'support_judgments_available': sum(len(v['support']) for v in judgments.values()),
                     'raw_support_label_counts': dict(Counter(r['label'] for v in judgments.values() for r in v['support'])),
                     'supported_both': len(support_sets[0] & support_sets[1]) if quality_complete else None,
                     'contradicted_major_both': len(false_sets[0] & false_sets[1]) if quality_complete else None,
                     'generation_tokens': sum(r.get('observed_tokens', 0) for r in usage),
                     'generation_seconds': sum(r.get('elapsed_seconds', 0) for r in usage)})
    by = {(r['paper_id'], r['condition']): r for r in rows}
    paired = {}
    for baseline in ['pra_original', 'single_agent']:
        ids = [p for p in protocol['paper_ids'] if all(by[p,c]['coverage_both'] is not None for c in ['pra_revised', baseline])]
        differences = [by[p,'pra_revised']['coverage_both']-by[p,baseline]['coverage_both'] for p in ids]
        paired[baseline] = {'paper_ids': ids, 'n': len(ids),
                            'mean_revised': statistics.mean(by[p,'pra_revised']['coverage_both'] for p in ids),
                            'mean_baseline': statistics.mean(by[p,baseline]['coverage_both'] for p in ids),
                            'mean_difference': statistics.mean(differences),
                            'wins': sum(d > 0 for d in differences), 'ties': sum(d == 0 for d in differences),
                            'losses': sum(d < 0 for d in differences)}
    bounds = {c: [statistics.mean(by[p,c]['coverage_both_bounds'][i] for p in protocol['paper_ids'])
                  for i in [0,1]] for c in protocol['conditions']}
    for pid in protocol['paper_ids']:
        out = root/'generation'/pid/'pra_revised'
        ledger = core.read(out/'finding_ledger.json')
        findings = {f['id']: f for f in ledger['findings']}
        core.exactly_ids(ledger['editor']['dispositions'], findings)
        core.exactly_ids(ledger['resolutions'], findings)
        review = (out/'review.md').read_text()
        for identifier in ledger['editor']['selected_ids']:
            for field in ['claim', 'why_it_matters', 'remedy', 'limitations']:
                assert findings[identifier][field] in review
        state = core.read(out/'state.json')
        assert len(state['reports']) == 5 and len(state['audits']) == 2
        assert {(t['role'],t['round']) for t in state['debate']} == {(r,n) for r in ['advocate','skeptic'] for n in [1,2]}
        for turn in state['debate']:
            core.exactly_ids(json.loads(turn['content'])['positions'], findings)
        quality = core.read(out/'quality.json')
        generation.append({'paper_id': pid, 'findings': len(findings), 'selected': len(ledger['editor']['selected_ids']),
                           'dispositions': dict(Counter(d['action'] for d in ledger['editor']['dispositions'])),
                           'resolutions': dict(Counter(r['status'] for r in ledger['resolutions'])),
                           'source_range_length_violations': len(quality['location_recovery'])})
    usage = [r for p in root.rglob('usage.jsonl') if 'saved_baselines' not in p.parts for r in core.shared.jsonl(p)]
    audit = core.read(root/'manual_audit.json')
    assert len(audit['items']) == 30 and audit['human_ratings'] == 'empty'
    result = {'scientific_results': False, 'phase': 'development', 'screening_signal': 'inconclusive',
              'direction': 'No observed improvement in human-review coverage.',
              'rows': rows, 'paired_available_comparisons': paired, 'three_paper_coverage_bounds': bounds,
              'generation': generation, 'invalid_support_items': invalid_items,
              'cost_by_condition': {c: {'mean_generation_tokens': statistics.mean(by[p,c]['generation_tokens'] for p in protocol['paper_ids']),
                                       'mean_generation_seconds': statistics.mean(by[p,c]['generation_seconds'] for p in protocol['paper_ids']),
                                       'mean_quoted_words': statistics.mean(by[p,c]['quoted_words'] for p in protocol['paper_ids'])}
                                    for c in protocol['conditions']},
              'judgments_available': 17, 'judgments_expected': 18,
              'missing': core.read(root/'completion_manifest.json')['skipped_failed_calls'],
              'calls': len(usage), 'successful_calls': sum(r['ok'] for r in usage),
              'observed_tokens': sum(r.get('observed_tokens',0) for r in usage),
              'unknown_usage_calls': sum('observed_tokens' not in r for r in usage),
              'active_call_seconds': sum(r['elapsed_seconds'] for r in usage),
              'requested_models': sorted({r['model_requested'] for r in usage}),
              'resolved_model_identity': 'Unavailable in CLI event stream',
              'manual_audit_items': len(audit['items']), 'human_audit': 'pending',
              'limitations': ['Three previously exposed papers with unverified manuscript and review version pairing.',
                              'One scoring pass is missing and is not imputed.',
                              'Source range format violations required export recovery and invalidate the strict screening gate.',
                              'Support statistics are withheld when evidence validation fails or a pass is missing.',
                              'Human-review overlap is not correctness. Same-model scoring passes are correlated.',
                              'No fresh expert audit, figure validation, or causal isolation of debate.'],
              'analysis_source_sha256': core.shared.digest(Path(__file__).read_bytes()),
              'checks': {'frozen_hashes': True, 'all_packets_exact_copies': True, 'complete_dispositions': True,
                         'selected_finding_text_preserved': True, 'all_debates_complete': True}}
    core.write(root/'available_results.json', result)
    compact = {k:v for k,v in result.items() if k not in ['invalid_support_items','limitations']}
    print(json.dumps(compact,indent=2))


if __name__ == '__main__':
    main()
