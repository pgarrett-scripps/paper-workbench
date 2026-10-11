"""Local synthesis preflight using the same production validation contract."""
import json

from .storage import digest, read, write

VERSION = 'synthesis-preflight-v1'
MAX_CHECKS = 2
MAX_DRAFT_CHARACTERS = 300000
INSTRUCTION = '''
SYNTHESIS PREFLIGHT:
Write the final findings first, then map components to their actual text. Do not map to a planned sentence that you removed or paraphrased. Empty findings are valid only if no component is preserved. For a rejected discarded hypothesis, every component must be resolved with source evidence. If a scientific question remains open, use an honest unresolved or supported status and defer the component as appropriate.
Before submitting, call validate_synthesis with draft_json containing your complete proposed response in the response schema, including evidence handles. It performs local structural checks without external requests. You have at most two checks, separate from your source tool allowance. Fix any reported errors and check once more if needed. Submit the checked draft without further edits. Every retained secondary finding must include all finding fields, including source_urls and source_evidence arrays. Use empty source arrays only when no external sources were used. Do not null or drop required secondary wording to avoid a shape error. Do not change scientific conclusions merely to satisfy the validator or fabricate missing evidence. Unresolved failures remain failures. A passing check establishes structural validity, not scientific correctness or semantic preservation.
'''


def destination_diagnostics(value, ledger, reference_changes=()):
    """Locate all broken preserved links and contradictory hypothesis treatments."""
    findings = value.get('findings', [])
    issues = {issue['issue_id']: issue for issue in ledger['issues']}
    problems = []
    for decision in value.get('decisions', []):
        issue_id = decision.get('issue_id')
        issue = issues.get(issue_id, {})
        for component in decision.get('components', []):
            context = {'issue_id': issue_id, 'component_id': component.get('component_id')}
            number, quote = component.get('final_finding_number'), component.get('final_quote')
            for change in reference_changes:
                if (change.get('field') == 'final_quote' and change.get('issue_id') == issue_id
                        and change.get('component_id') == component.get('component_id')
                        and change.get('before') == quote):
                    quote = change['after']
            if component.get('treatment') == 'preserved':
                if type(number) is not int or not 1 <= number <= len(findings):
                    problems.append({**context, 'code': 'missing_final_finding', 'final_finding_number': number})
                elif not isinstance(quote, str) or not quote or quote not in findings[number - 1].get('comment', ''):
                    problems.append({**context, 'code': 'missing_final_quote', 'final_finding_number': number,
                                     'message': 'Copy an exact substantive span from this final comment. Do not invent a destination.'})
            if (issue.get('source_kind') == 'discarded_hypothesis'
                    and decision.get('scientific_status') == 'contradicted'
                    and component.get('treatment') != 'resolved'):
                problems.append({**context, 'code': 'rejected_hypothesis_unresolved_component',
                                 'message': 'A rejected hypothesis must resolve every component with evidence. An open question is not disproven.'})
    return problems


def validate_draft(raw, ledger, paper, cards=None):
    """Check a model-format response without saving or promoting a review."""
    from .annotations import normalize_review
    from .ensemble_debate import normalize_new_decisions, augment_ledger, adjudicated_secondary
    from .ensemble_references import recover
    from .evidence_handles import hydrate_response, build_registry
    from .external_evidence import bind_sources
    result = {'version': VERSION, 'draft_sha256': digest(json.dumps(raw, sort_keys=True)),
              'valid': False, 'problems': [],
              'limitation': 'Structural check only. Scientific correctness and semantic preservation require assessment.'}
    try:
        hydrated = hydrate_response(raw, build_registry(paper, cards or []))
        final = normalize_new_decisions(hydrated['response'])
        if cards is not None:
            final = bind_sources(final, cards)
        for index, candidate in enumerate(final.get('new_candidates', []), 1):
            checked = normalize_review(paper, {'summary': 'New candidate', 'findings': [candidate['finding']]}, 'new-' + str(index))
            candidate['finding'] = checked['findings'][0]
        augmented = augment_ledger(final, ledger, paper, cards, validate=False)
        secondary_problems = []
        for decision in final.get('decisions', []):
            try:
                adjudicated_secondary({'decisions': [decision]}, augmented, paper, cards)
            except ValueError as error:
                secondary_problems.append({'code': 'invalid_secondary_finding',
                                           'issue_id': decision.get('issue_id'), 'message': str(error)})
        checked = recover(final, augmented, paper, cards)
        accepted = checked['recovered'] if checked['recovered'] is not None else final
        result['valid'] = not secondary_problems and (checked['recovered'] is not None or checked['original']['status'] == 'valid')
        result['reference_recovery'] = {key: value for key, value in checked.items() if key != 'recovered'}
        if not result['valid']:
            result['error'] = secondary_problems[0]['message'] if secondary_problems else (checked.get('audit') or checked['original'])['error']
            result['problems'] = secondary_problems + destination_diagnostics(accepted, augmented, checked.get('changed_fields', []))
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        result['error'] = str(error)
    return result


def preflight_receipts(directory, raw):
    """Record whether a passing preflight checked the exact submitted response."""
    expected = digest(json.dumps(raw, sort_keys=True))
    rows = []
    for path in sorted(directory.glob('check-*.json')):
        saved = read(path)
        result = saved.get('result', {})
        rows.append({'file': path.name, 'status': saved.get('status'),
                     'valid': result.get('valid') is True,
                     'matches_submitted_draft': result.get('draft_sha256') == expected})
    return {'checks': rows, 'submitted_draft_sha256': expected,
            'submitted_draft_preflight_passed': any(row['valid'] and row['matches_submitted_draft'] for row in rows)}


class SynthesisPreflight:
    """Persist a two-check local allowance and every candidate validation receipt."""
    def __init__(self, ledger, paper, output, cards):
        self.ledger, self.paper, self.output, self.cards = ledger, paper, output, cards
        self.output.mkdir(parents=True, exist_ok=True)

    def call(self, draft_json):
        # Exclusive receipt reservation makes the allowance survive MCP restarts.
        for index in range(1, MAX_CHECKS + 1):
            path = self.output / f'check-{index}.json'
            try:
                with path.open('x') as stream:
                    json.dump({'status': 'started', 'check': index}, stream)
                break
            except FileExistsError:
                continue
        else:
            return {'valid': False, 'error': 'Synthesis preflight allowance exhausted', 'remaining_checks': 0}
        try:
            if not isinstance(draft_json, str) or len(draft_json) > MAX_DRAFT_CHARACTERS:
                raise ValueError('Supply a bounded JSON draft string')
            raw = json.loads(draft_json)
            result = validate_draft(raw, self.ledger, self.paper, self.cards())
        except (ValueError, TypeError, AttributeError, RecursionError) as error:
            result = {'valid': False, 'error': str(error)}
        result.update(check=index, remaining_checks=MAX_CHECKS-index,
                      tool_receipt={'tool': 'validate_synthesis', 'call_index': index, 'allowance': VERSION})
        write(path, {'status': 'complete', 'draft_json': draft_json if isinstance(draft_json, str) and len(draft_json) <= MAX_DRAFT_CHARACTERS else None,
                     'result': result})
        return result
