"""Experimental node adapters retaining the production PRA graph topology."""

import json
from pathlib import Path

import core
import prompts as prompt
import schemas as schema

REVIEWERS = ['scientific_validity', 'data_analysis', 'contribution_context', 'reporting_reproducibility', 'ethics']
AUDITORS = ['methods_completeness', 'citation_integrity']


def ledger(state):
    records = [f for r in state.get('reports', []) + state.get('audits', []) for f in r.get('findings', [])]
    if len({r['id'] for r in records}) != len(records):
        raise core.Blocked('Duplicate finding IDs in ledger')
    return records


def prior_turns(state, round_number):
    return sorted([t for t in state.get('debate', []) if t['round'] < round_number],
                  key=lambda t: (t['round'], t['role']))


def evidence_label(finding):
    primary = ', '.join(f"L{s['start']}-L{s['end']}" for s in finding.get('resolved_evidence', [])) or 'unlocated'
    counter = ', '.join(f"L{s['start']}-L{s['end']}" for s in finding.get('resolved_counterevidence', [])) or 'none located'
    return f'Evidence: {primary}. Counterevidence: {counter}.'


def resolve_outcome(row, manuscript):
    result = core.attach_evidence(row, manuscript)
    if result['status'] in {'upheld', 'refuted'} and not (
        result['evidence_spans_valid'] and result['resolved_evidence']
    ):
        result['requested_status'] = result['status']
        result['status'] = 'unresolved'
        result['reason'] = 'No valid evidence location for a decisive outcome. ' + result['reason']
    return result


def render_selected(records, resolutions, decision):
    by_id = {f['id']: f for f in records}
    resolved = {r['finding_id']: r for r in resolutions}
    core.exactly_ids(decision['dispositions'], by_id)
    ids = decision['selected_ids']
    if len(ids) > 5 or len(ids) != len(set(ids)) or not set(ids) <= set(by_id):
        raise core.Blocked('Invalid final finding selection')
    dispositions = {d['finding_id']: d for d in decision['dispositions']}
    for identifier, disposition in dispositions.items():
        if not disposition['reason'].strip():
            raise core.Blocked('Every disposition needs a reason')
        if (disposition['action'] == 'selected') != (identifier in ids):
            raise core.Blocked('Selected IDs disagree with dispositions')
        if disposition['action'] == 'merged':
            if disposition['merged_into'] not in ids or disposition['merged_into'] == identifier:
                raise core.Blocked('Merge does not point to another selected finding')
        elif disposition['merged_into']:
            raise core.Blocked('Non-merged finding has a merge target')
    result = []
    for index, identifier in enumerate(ids, 1):
        f, resolution = by_id[identifier], resolved[identifier]
        if resolution['status'] in {'refuted', 'duplicate'}:
            raise core.Blocked('Editor selected a refuted or duplicate finding')
        if not f.get('evidence_spans_valid') or not f.get('resolved_evidence'):
            raise core.Blocked('Selected finding has no valid manuscript location')
        provisional = 'Provisional concern' if resolution['status'] in {'qualified', 'unresolved'} else 'Concern'
        result.append(f"{provisional} {index}: {f['claim']}\n"
                      f"{evidence_label(f)}\n"
                      f"Why it matters: {f['why_it_matters']}\n"
                      f"Remedy: {f['remedy']}\n"
                      f"Limitations: {f['limitations']}\n"
                      f"Qualification ({resolution['status']}): {resolution['reason']}")
    body = '\n\n'.join(result) if result else 'No supported substantive concerns were selected.'
    if len(body.split()) > 900:
        raise core.Blocked('Complete selected findings exceed final word budget')
    return body


def install(root, protocol, out, manuscript):
    from peerreviewagents.graph import review_graph as graph

    context = prompt.SAFETY + '\nNUMBERED MANUSCRIPT\n' + core.numbered(manuscript) + '\nEND MANUSCRIPT\n'

    def invoke(text, output_schema, label):
        return core.call(root, protocol, out, context + text, output_schema, label)

    def make_panel(role, audit=False):
        def node(state):
            value = invoke('\nYOUR INVESTIGATION\n' + prompt.TASKS[role] + '\n' + prompt.PANEL, schema.PANEL, role)
            findings = []
            for i, row in enumerate(value['findings'], 1):
                f = core.attach_evidence(row, manuscript)
                f['id'] = f'{role}:{i}'
                f['origin'] = role
                f['original_sha256'] = core.shared.digest(row)
                findings.append(f)
            checks = [core.attach_evidence(c, manuscript) for c in value['checks']]
            preserved = {**value, 'findings': findings, 'checks': checks}
            core.write(out/'panel'/f'{role}.json', preserved)
            body = json.dumps(preserved, ensure_ascii=False)
            if audit:
                report = {'auditor': role, 'title': role, 'hard_gaps': None, 'soft_gaps': None,
                          'body': body, 'findings': findings}
                return {'audits': [report]}
            report = {'reviewer': role, 'score': value['score'], 'confidence': value['confidence'],
                      'body': body, 'findings': findings, 'weaknesses': [f['claim'] for f in findings],
                      'questions': [], 'score_source': 'explicit'}
            return {'reports': [report]}
        return node

    def make_debater(role, stance):
        def node(state):
            round_number = state.get('debate_round', 0) + 1
            records = ledger(state)
            history = prior_turns(state, round_number)
            value = invoke('\n' + prompt.DEBATE + '\nYOUR ROLE\n' + stance +
                           f'\nROUND {round_number}\nCOMPLETE IMMUTABLE FINDINGS\n' + json.dumps(records) +
                           '\nPRIOR ROUNDS ONLY\n' + json.dumps(history), schema.DEBATE, f'{role}_round_{round_number}')
            core.exactly_ids(value['positions'], [r['id'] for r in records])
            value['positions'] = [core.attach_evidence(p, manuscript) for p in value['positions']]
            core.write(out/'debate'/f'{role}_{round_number}.json', value)
            return {'debate': [{'role': role, 'round': round_number, 'content': json.dumps(value, ensure_ascii=False)}]}
        return node

    def synthesize(state):
        records = ledger(state)
        value = invoke('\n' + prompt.SYNTHESIS + '\nIMMUTABLE FINDINGS\n' + json.dumps(records) +
                       '\nCOMPLETE DEBATE\n' + json.dumps(prior_turns(state, 3)), schema.SYNTHESIS, 'debate_synthesis')
        core.exactly_ids(value['resolutions'], [r['id'] for r in records])
        ids = {r['id'] for r in records}
        for r in value['resolutions']:
            if r['status'] == 'duplicate':
                if r['duplicate_of'] not in ids or r['duplicate_of'] == r['finding_id']:
                    raise core.Blocked('Invalid duplicate finding target')
            elif r['duplicate_of']:
                raise core.Blocked('Unexpected duplicate target')
        value['resolutions'] = [resolve_outcome(r, manuscript) for r in value['resolutions']]
        core.write(out/'resolutions.json', value)
        return {'debate_synthesis': json.dumps(value, ensure_ascii=False)}

    def editor(state):
        records = ledger(state)
        resolutions = json.loads(state['debate_synthesis'])['resolutions']
        value = invoke('\n' + prompt.EDITOR + '\nIMMUTABLE FINDINGS\n' + json.dumps(records) +
                       '\nRESOLUTIONS\n' + json.dumps(resolutions), schema.EDITOR, 'editor')
        body = render_selected(records, resolutions, value)
        core.write(out/'finding_ledger.json', {'findings': records, 'resolutions': resolutions, 'editor': value})
        core.write(out/'editor.json', value)
        return {'decision': value['verdict'], 'decision_letter': body, 'required_revisions': [], 'minor_suggestions': []}

    graph.get_reviewer_nodes = lambda config: [(role, make_panel(role)) for role in REVIEWERS]
    graph.get_auditor_nodes = lambda revision=False: [(role, make_panel(role, True)) for role in AUDITORS]
    graph.advocate.node = make_debater('advocate', prompt.ADVOCATE)
    graph.skeptic.node = make_debater('skeptic', prompt.SKEPTIC)
    graph.debate_synthesizer.node = synthesize
    graph.editor_in_chief.node = editor


def generate(root, paper_id):
    import copy
    import sys
    protocol, _ = core.verify(root)
    core.shared.require_subscription(root)
    sys.path.insert(0, str(root/'source'))
    from peerreviewagents.default_config import DEFAULT_CONFIG
    from peerreviewagents.graph.review_graph import PeerReviewGraph, _merge_partial
    out = root/'generation'/paper_id/'pra_revised'
    if (out/'result.json').exists():
        return
    out.mkdir(parents=True, exist_ok=True)
    manuscript = (root/'inputs'/paper_id/'manuscript.txt').read_text()
    install(root, protocol, out, manuscript)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(provider='codex', reasoning_model=protocol['model'], fast_model=protocol['model'],
                  research_enabled=False, enable_debate=True, max_debate_rounds=2,
                  enable_journal_recommender=False, desk_screen_mode='off', desk_screen=False,
                  target_journal='ml-conference', article_type='conference-paper',
                  checkpoint_dir=str(out/'checkpoints'), output_dir=str(out), panel_quorum_fraction=1.0)
    graph = PeerReviewGraph(config)
    state = dict(graph.initial_state(str(root/'inputs'/paper_id/'manuscript.txt')))
    for chunk in graph.graph.stream(state, {'recursion_limit': 100, 'max_concurrency': 1}):
        for name, partial in chunk.items():
            _merge_partial(state, partial)
            core.write(out/'state.json', state)
            core.write(root/'status.json', {'stage': 'generation', 'paper_id': paper_id, 'node': name})
            if name == 'panel_gate':
                if not state.get('panel_complete'):
                    raise core.Blocked('Incomplete panel')
                core.write(out/'panel_ledger.json', ledger(state))
            print(json.dumps({'paper_id': paper_id, 'stage': name}), flush=True)
    if not state.get('panel_complete') or state.get('errors') or len(state.get('debate', [])) != 4:
        raise core.Blocked('Graph did not finish the complete panel and two debate rounds')
    (out/'review.md').write_text(state['decision_letter'] + '\n')
    core.write(out/'result.json', {'ok': True, 'paper_id': paper_id, 'model': protocol['model'],
                                  'findings_count': len(ledger(state)), 'debate_turns': 4,
                                  'selected_ids': core.read(out/'editor.json')['selected_ids'],
                                  'scientific_results': False})
