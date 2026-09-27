#!/usr/bin/env python3
"""Run a fixed three-paper development comparison with preserved findings."""

import argparse
import json
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

import core
import prompts as prompt
import schemas as schema


def review_path(root, paper_id, condition):
    directory = 'generation' if condition == 'pra_revised' else 'saved_baselines'
    return root/directory/paper_id/condition/'review.md'


def normalize(root, protocol, paper_id, condition):
    out = root/'normalization'/paper_id/condition
    if (out/'packet.json').exists():
        return core.read(out/'packet.json')['concerns']
    body = review_path(root, paper_id, condition).read_text()
    paras = core.paragraphs(body)
    numbered = '\n\n'.join(f'PARAGRAPH {i}\n{p}' for i, p in enumerate(paras, 1))
    value = core.call(root, protocol, out, prompt.SAFETY + prompt.NORMALIZE + '\nREVIEW\n' + numbered,
                      schema.PACKET, 'common_source_span_extraction')
    concerns = core.packet_from_paragraphs(value, body)
    core.write(out/'packet.json', {'concerns': concerns, 'review_sha256': core.shared.digest(body.encode()),
                                  'source_word_count': len(body.split()),
                                  'quoted_word_count': sum(len(c['source_quote'].split()) for c in concerns)})
    return concerns


def validate_judgment(value, refs, candidates, manuscript):
    core.exactly_ids(value['matches'], [r['id'] for r in refs], 'reference_id')
    core.exactly_ids(value['support'], [r['id'] for r in candidates], 'candidate_id')
    candidate_ids = {c['id'] for c in candidates}
    for row in value['matches']:
        if not set(row['candidate_ids']) <= candidate_ids or bool(row['candidate_ids']) != row['matched']:
            raise core.Blocked('Invalid matched candidate IDs')
    for i, row in enumerate(value['support']):
        if row['label'] not in {'supported', 'contradicted', 'insufficient_evidence'}:
            raise core.Blocked('Unknown support label')
        row = core.attach_evidence(row, manuscript)
        row['evidence_valid'] = row['label'] == 'insufficient_evidence' or bool(row['evidence_spans_valid'] and row['resolved_evidence'])
        value['support'][i] = row
    return value


def compare(root, protocol):
    mapping = []
    for pid in protocol['paper_ids']:
        order = list(protocol['conditions'])
        random.Random(f"{protocol['seed']}:{pid}:blinding").shuffle(order)
        for index, condition in enumerate(order, 1):
            mapping.append({'paper_id': pid, 'anonymous_id': f'review_{index}', 'condition': condition})
    core.write(root/'evaluation/condition_key.json', mapping)
    for entry in mapping:
        pid, condition = entry['paper_id'], entry['condition']
        candidates = normalize(root, protocol, pid, condition)
        refs = core.read(root/'inputs'/pid/'reference.json')['concerns']
        manuscript = (root/'inputs'/pid/'manuscript.txt').read_text()
        for judge in ['A', 'B']:
            out = root/'evaluation'/pid/entry['anonymous_id']/judge
            if (out/'judgment.json').exists():
                continue
            core.write(root/'status.json', {'stage': 'scoring', 'paper_id': pid, 'anonymous_id': entry['anonymous_id'], 'judge': judge})
            ordered_refs = refs if judge == 'A' else list(reversed(refs))
            ordered_candidates = candidates if judge == 'A' else list(reversed(candidates))
            extra = '\nActively consider an alternative interpretation before each judgment.\n' if judge == 'B' else ''
            text = prompt.SAFETY + prompt.JUDGE + extra + '\nNUMBERED MANUSCRIPT\n' + core.numbered(manuscript)
            text += '\nREFERENCE CONCERNS\n' + json.dumps(ordered_refs) + '\nANONYMOUS CANDIDATES\n' + json.dumps(ordered_candidates)
            value = core.call(root, protocol, out, text, schema.JUDGE, f'judge_{judge}')
            validate_judgment(value, refs, candidates, manuscript)
            core.write(out/'judgment.json', value)


def summarize(root, protocol):
    rows = []
    for entry in core.read(root/'evaluation/condition_key.json'):
        pid, condition = entry['paper_id'], entry['condition']
        base = root/'evaluation'/pid/entry['anonymous_id']
        if not all((base/j/'judgment.json').exists() for j in ['A', 'B']):
            raise core.Blocked('Comparison is incomplete')
        judgments = [core.read(base/j/'judgment.json') for j in ['A', 'B']]
        matches = [{r['reference_id'] for r in j['matches'] if r['matched']} for j in judgments]
        false_major = [{r['candidate_id'] for r in j['support'] if r['label']=='contradicted' and r['major'] and r['evidence_valid']} for j in judgments]
        invalid = sum(not r['evidence_valid'] for j in judgments for r in j['support'])
        packet = core.read(root/'normalization'/pid/condition/'packet.json')
        source = 'generation' if condition == 'pra_revised' else 'saved_baselines'
        usage = core.shared.jsonl(root/source/pid/condition/'usage.jsonl')
        # Baseline logs include their old extractor, which is excluded here.
        generation_usage = [u for u in usage if u['label'] != 'extract_final_concerns']
        n = len(judgments[0]['matches'])
        rows.append({**entry, 'n_reference': n, 'n_concerns': len(packet['concerns']),
                     'coverage_A': len(matches[0])/n if n else None,
                     'coverage_B': len(matches[1])/n if n else None,
                     'coverage_both': len(matches[0]&matches[1])/n if n else None,
                     'supported_both': len({r['candidate_id'] for r in judgments[0]['support'] if r['label']=='supported' and r['evidence_valid']} &
                                           {r['candidate_id'] for r in judgments[1]['support'] if r['label']=='supported' and r['evidence_valid']}) if not invalid else None,
                     'contradicted_major_both': len(false_major[0]&false_major[1]) if not invalid else None,
                     'insufficient_evidence_judgments': sum(r['label']=='insufficient_evidence' for j in judgments for r in j['support']),
                     'invalid_evidence_judgments': invalid,
                     'quoted_words': packet['quoted_word_count'], 'review_words': packet['source_word_count'],
                     'standalone_generation_tokens': sum(u.get('observed_tokens',0) for u in generation_usage)})
    by = {(r['paper_id'],r['condition']):r for r in rows}
    conditions = {c: {'mean_coverage_both': statistics.mean(r['coverage_both'] for r in rows if r['condition']==c),
                      'mean_generation_tokens': statistics.mean(r['standalone_generation_tokens'] for r in rows if r['condition']==c),
                      'mean_quoted_words': statistics.mean(r['quoted_words'] for r in rows if r['condition']==c)} for c in protocol['conditions']}
    comparisons = {}
    for baseline in ['pra_original','single_agent']:
        differences = [by[(pid,'pra_revised')]['coverage_both']-by[(pid,baseline)]['coverage_both'] for pid in protocol['paper_ids']]
        comparisons[baseline] = {'mean_difference': statistics.mean(differences), 'wins': sum(d>0 for d in differences),
                                 'ties': sum(d==0 for d in differences), 'losses': sum(d<0 for d in differences)}
    evidence_complete = not any(r['invalid_evidence_judgments'] for r in rows)
    no_added_false = evidence_complete and all(
        by[(pid,'pra_revised')]['contradicted_major_both'] <= by[(pid,base)]['contradicted_major_both']
        for pid in protocol['paper_ids'] for base in ['pra_original','single_agent'])
    generation_quality = {pid: core.read(root/'generation'/pid/'pra_revised/quality.json') for pid in protocol['paper_ids']}
    protocol_conformant = all(q['protocol_conformant'] for q in generation_quality.values())
    promising = evidence_complete and protocol_conformant and no_added_false and all(c['mean_difference']>0 and c['wins']>=2 for c in comparisons.values())
    usage = [u for p in root.glob('**/usage.jsonl') if 'saved_baselines' not in p.parts for u in core.shared.jsonl(p)]
    result = {'phase':'development', 'scientific_results':False, 'paper_metrics':rows,'conditions':conditions,
              'paired_comparisons':comparisons,'evidence_complete':evidence_complete,
              'generation_quality': generation_quality, 'protocol_conformant': protocol_conformant,
              'screening_signal':'promising_pending_human_audit' if promising else 'inconclusive' if not (evidence_complete and protocol_conformant) else 'improvement_not_demonstrated',
              'new_calls':len(usage),'new_observed_tokens':sum(u.get('observed_tokens',0) for u in usage),
              'human_audit':'pending','limitations':['Three previously exposed development papers only.',
                  'Bundled changes do not isolate the causal contribution of debate.',
                  'Same-model judges are correlated and span existence does not prove correctness.',
                  'Condition labels are hidden but style can reveal the workflow.',
                  'Manuscript versions and figure access remain unverified.',
                  'Same source-span extractor and evaluator were applied to all three arms. Old scores are not pooled.',
                  'Export recovery accepts exact in-bounds evidence locations longer than the requested eight lines. Original violations remain flagged and make the strict screening result inconclusive.']}
    core.write(root/'report.json',result)
    return result


def audit(root):
    items=[]
    for entry in core.read(root/'evaluation/condition_key.json'):
        pid, condition = entry['paper_id'], entry['condition']
        candidate = core.read(root/'normalization'/pid/condition/'packet.json')['concerns']
        refs = core.read(root/'inputs'/pid/'reference.json')['concerns']
        value = core.read(root/'evaluation'/pid/entry['anonymous_id']/'A/judgment.json')
        for category in ['matches','support']:
            for row in value[category]:
                items.append({'paper_id':pid,'anonymous_id':entry['anonymous_id'],'category':category,
                              'target_id':row.get('reference_id',row.get('candidate_id')),'candidates':candidate,'references':refs})
    random.Random(20260917).shuffle(items)
    core.write(root/'manual_audit.json',{'sampling':'simple random sample of 30 evaluator A items',
                                      'population':len(items),'items':items[:30],'human_ratings':'empty'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=core.ROOT)
    parser.add_argument('command',choices=['prepare','run','worker','summarize'])
    parser.add_argument('--paper')
    args=parser.parse_args()
    root=args.root.resolve()
    try:
        if args.command=='prepare':
            core.prepare(root)
            return 0
        protocol,manifest=core.verify(root)
        if args.command=='summarize':
            print(json.dumps(summarize(root,protocol),indent=2))
            return 0
        core.shared.require_subscription(root)
        if args.command=='worker':
            from revision import generate
            generate(root,args.paper)
            return 0
        for pid in protocol['paper_ids']:
            if not (root/'generation'/pid/'pra_revised/result.json').exists():
                result=subprocess.run([protocol['pra_python'],str(core.HERE/'study.py'),'--root',str(root),'worker','--paper',pid],env=core.shared.clean_env())
                if result.returncode:
                    raise core.Blocked(f'Generation failed for {pid}. Preserve and inspect the attempt.')
        compare(root,protocol)
        result=summarize(root,protocol)
        audit(root)
        core.write(root/'status.json',{'stage':'complete','scientific_results':False,'screening_signal':result['screening_signal'],'human_audit':'pending'})
        print(json.dumps(result,indent=2))
    except Exception as exc:
        core.write(root/'status.json',{'stage':'blocked','reason':str(exc),'updated_at':time.time()})
        print(f'STOPPED: {exc}',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    sys.exit(main())
