"""The read manuscript fixture is what the engine's own Read stage writes now."""
import json
import unittest

from reader_fixture import FIXTURE, build


class ReaderFixtureTest(unittest.TestCase):
    def test_the_fixture_is_what_the_engine_writes(self):
        # test_review_evidence_ui.js renders paper.json, so it must stay what the engine and the port write.
        self.assertEqual(build(), json.loads(FIXTURE.read_text()),
                         'tests/fixtures/reader/paper.json is out of date. README.md there says how to refresh it.')

    def test_the_fixture_holds_every_shape_the_viewer_renders(self):
        # The viewer test leans on these shapes, so a script change that loses one fails here and not
        # as a silent gap in what the viewer test covers.
        read = json.loads(FIXTURE.read_text())['read']
        originals = [row.get('original') or {} for row in read['pieces']]
        parts = [original for original in originals if original.get('of') == 3]
        self.assertEqual([original['part'] for original in parts], [1, 2, 3])
        # The engine writes a re-read's debris on one part only, the first part that is not prose.
        self.assertEqual([bool(original.get('absorbed')) for original in parts], [False, True, False])
        self.assertEqual([original['part'] for original in originals if original.get('of') == 1], [1])
        self.assertTrue(any(row['kind'] == 'figure-description' and row['original'].get('absorbed')
                            for row in read['pieces']))
        ai_read = read['ai_read']
        self.assertTrue(ai_read['read'])
        self.assertIn('<b>', ai_read['note'])
        self.assertEqual([page['page'] for page in ai_read['lost_pages']], [3])
        self.assertEqual(ai_read['gone'], {'absorbed': 2})


if __name__ == '__main__':
    unittest.main()
