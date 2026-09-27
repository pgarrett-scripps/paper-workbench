import unittest
from paper_workspace.evidence_handles import build_registry
from paper_workspace.judge_evidence import judge_schema, hydrate_judgment
from experiments.pra_debate_revision.evaluation import EVALUATION


class JudgeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_registry({'blocks': [
            {'id': 'b1', 'text': 'Monitoring was planned.'},
            {'id': 'b2', 'text': 'Weekly contact was described.'}]})
        self.images = [{'id': 'image-1'}]

    def value(self, refs):
        return {'conditions': [{'ratings': [{'finding_id': 'A1', 'evidence': refs,
                                             'counterevidence': []}]}]}

    def test_two_source_spans_stay_separate(self):
        refs = [{'evidence_handle': h.handle_id} for h in self.registry.handles]
        result = hydrate_judgment(self.value(refs), self.registry, [])
        evidence = result['response']['conditions'][0]['ratings'][0]['evidence']
        self.assertEqual([r['block_id'] for r in evidence], ['b1', 'b2'])
        self.assertEqual(evidence[0]['quote'], 'Monitoring was planned.')
        self.assertEqual(len(result['receipts']), 2)

    def test_unknown_mixed_and_raw_references_rejected(self):
        for ref in ({'evidence_handle': 'mh-invented'},
                    {'block_id': 'b1', 'quote': 'Monitoring was planned.'},
                    {'evidence_handle': self.registry.handles[0].handle_id,
                     'image_id': 'image-1'},
                    {'image_id': 'image-2', 'visual_observation': 'A point'},
                    {'image_id': 'image-1', 'visual_observation': ' '}):
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                hydrate_judgment(self.value([ref]), self.registry, self.images)

    def test_image_reference_and_schema(self):
        result = hydrate_judgment(self.value([{'image_id': 'image-1',
            'visual_observation': 'The axis starts at zero.'}]), self.registry, self.images)
        self.assertEqual(result['response']['conditions'][0]['ratings'][0]['evidence'][0]['quote'], '')
        schema = judge_schema(EVALUATION, self.registry, self.images)
        self.assertEqual(schema['$defs']['judgeSourceHandle']['enum'],
                         [h.handle_id for h in self.registry.handles])
        self.assertNotIn('$defs', EVALUATION)


if __name__ == '__main__':
    unittest.main()
