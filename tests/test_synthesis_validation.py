"""Offline regression checks for in-session synthesis validation."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from paper_workspace.debate_revision import issue_ledger
from paper_workspace.ensemble_references import recover
from paper_workspace.evidence_handles import build_registry
from paper_workspace.investigation import Investigation, specs
from paper_workspace.model_runtime import tool_profile
from paper_workspace.storage import digest, read, write
from paper_workspace.synthesis_validation import validate_draft, destination_diagnostics, preflight_receipts


class SynthesisValidationTests(unittest.TestCase):
    def setUp(self):
        text = 'We studied five plants.'
        self.paper = {'id': 'paper', 'blocks': [{'id': 'b1', 'text': text, 'sha256': digest(text)}]}
        self.finding = {'title': 'Allocation', 'kind': 'question', 'severity': 'moderate',
                        'block_id': 'b1', 'quote': text, 'evidence_blocks': ['b1'],
                        'comment': 'Please clarify allocation.', 'replacement': '',
                        'counterevidence': '', 'source_urls': []}
        self.ledger = issue_ledger({'findings': [self.finding]})
        self.handle = build_registry(self.paper).handles[0].handle_id
        f = {k: v for k, v in self.finding.items() if k not in ('block_id', 'quote', 'evidence_blocks')}
        f.update(anchor_handle=self.handle, manuscript_evidence_handles=[self.handle])
        self.raw = {'summary': 'Review', 'findings': [f], 'limitations': [], 'new_candidates': [],
                    'decisions': [{'issue_id': 'issue-1', 'scientific_status': 'supported_clarification',
                    'presentation': 'primary', 'strongest_criticism': 'Allocation is unclear.',
                    'strongest_author_defense': 'A count is supplied.', 'decisive_question': 'How allocated?',
                    'decision_reason': 'Clarification is needed.', 'evidence': [{'evidence_handle': self.handle}],
                    'secondary_finding': None, 'components': [{'component_id': 'issue-1-part-1',
                    'treatment': 'preserved', 'final_finding_number': 1,
                    'final_quote': self.finding['comment'], 'reason': 'Retain the request.', 'evidence': []}]}]}

    def test_valid_draft_and_format_recovery_leave_input_unchanged(self):
        self.raw['decisions'][0]['components'][0]['final_quote'] = 'please clarify allocation'
        before = copy.deepcopy(self.raw)
        checked = validate_draft(self.raw, self.ledger, self.paper)
        self.assertTrue(checked['valid'])
        self.assertEqual(checked['problems'], [])
        self.assertEqual(self.raw, before)
        self.assertEqual(len(checked['reference_recovery']['changed_fields']), 1)

    def test_empty_output_and_missing_content_are_not_repaired(self):
        empty = copy.deepcopy(self.raw)
        empty['findings'] = []
        result = validate_draft(empty, self.ledger, self.paper)
        self.assertFalse(result['valid'])
        self.assertEqual(result['problems'][0]['code'], 'missing_final_finding')
        self.raw['decisions'][0]['components'][0]['final_quote'] = 'Please report the sampling dates.'
        result = validate_draft(self.raw, self.ledger, self.paper)
        self.assertFalse(result['valid'])
        self.assertEqual(result['problems'][0]['code'], 'missing_final_quote')

    def test_secondary_feedback_names_missing_fields_and_preserves_required_wording(self):
        secondary = copy.deepcopy(self.raw['findings'][0])
        secondary.pop('source_urls')
        self.raw['findings'] = []
        decision = self.raw['decisions'][0]
        decision.update(presentation='supporting', secondary_finding=secondary)
        decision['components'][0].update(treatment='deferred', final_finding_number=0, final_quote='')
        result = validate_draft(self.raw, self.ledger, self.paper)
        self.assertFalse(result['valid'])
        self.assertIn('source_urls', result['error'])
        self.assertIn('source_evidence', result['error'])
        self.assertEqual(result['problems'][0]['issue_id'], 'issue-1')
        decision['secondary_finding'] = None
        result = validate_draft(self.raw, self.ledger, self.paper)
        self.assertFalse(result['valid'])
        self.assertIn('requires an adjudicated finding', result['error'])
        secondary.update(source_urls=[], source_evidence=[])
        decision['secondary_finding'] = secondary
        self.assertTrue(validate_draft(self.raw, self.ledger, self.paper)['valid'])

    def test_invalid_evidence_is_still_rejected(self):
        self.raw['findings'][0]['anchor_handle'] = 'invented'
        self.assertFalse(validate_draft(self.raw, self.ledger, self.paper)['valid'])

    def test_recovery_reports_the_later_error_not_the_repaired_error(self):
        from paper_workspace.evidence_handles import hydrate_response
        value = hydrate_response(self.raw, build_registry(self.paper))['response']
        value['decisions'][0]['components'][0]['final_quote'] = 'please clarify allocation'
        hypothesis = {'issue_id': 'issue-2', 'source_kind': 'discarded_hypothesis',
                      'components': [{'component_id': 'issue-2-part-1', 'text': 'Was allocation biased?'}]}
        ledger = copy.deepcopy(self.ledger)
        ledger['issues'].append(hypothesis)
        decision = copy.deepcopy(value['decisions'][0])
        decision.update(issue_id='issue-2', scientific_status='contradicted', presentation='omitted')
        decision['components'][0].update(component_id='issue-2-part-1', treatment='deferred',
                                         final_finding_number=0, final_quote='')
        value['decisions'].append(decision)
        result = recover(value, ledger, self.paper)
        self.assertIsNone(result['recovered'])
        self.assertEqual(result['audit']['error'], 'Rejected hypothesis must resolve every component with source evidence')
        problems = destination_diagnostics(value, ledger, result['changed_fields'])
        self.assertEqual([p['code'] for p in problems], ['rejected_hypothesis_unresolved_component'])

    def test_preflight_is_separate_bounded_persistent_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write(root/'paper.json', self.paper)
            write(root/'manifest.json', {'files': {'paper.json': digest((root/'paper.json').read_bytes())}})
            write(root/'ledger.json', self.ledger)
            config = {'paper': str(root), 'output': str(root/'out'), 'cache': str(root/'cache'),
                      'tool_limit': 1, 'synthesis_ledger': str(root/'ledger.json')}
            server = Investigation(config)
            server.call('calculate', {'expression': '2+2'})
            first = server.call('validate_synthesis', {'draft_json': json.dumps(self.raw)})
            self.assertTrue(first['valid'])
            self.assertEqual(server.calls, 1)
            restarted = Investigation(config)
            second = restarted.call('validate_synthesis', {'draft_json': '{'})
            self.assertFalse(second['valid'])
            exhausted = server.call('validate_synthesis', {'draft_json': json.dumps(self.raw)})
            self.assertIn('exhausted', exhausted['error'])
            self.assertEqual(len(list((root/'out/synthesis-preflight').glob('*.json'))), 2)
            self.assertFalse((root/'reviews').exists())
            saved = read(root/'out/synthesis-preflight/check-1.json')
            self.assertEqual(saved['result']['draft_sha256'], first['draft_sha256'])
            self.assertTrue(preflight_receipts(root/'out/synthesis-preflight', self.raw)['submitted_draft_preflight_passed'])
            changed = {**self.raw, 'summary': 'Edited after validation'}
            self.assertFalse(preflight_receipts(root/'out/synthesis-preflight', changed)['submitted_draft_preflight_passed'])

    def test_tool_exposure_matches_runtime_allowlist_only_for_synthesis(self):
        self.assertNotIn('validate_synthesis', tool_profile({})[1])
        for domain in (False, True):
            config = {'synthesis_ledger': 'ledger.json'}
            if domain:
                config['tool_profile'] = 'domains-v1'
            self.assertEqual(set(tool_profile(config)[1]), {s['name'] for s in specs(domain, True)})
