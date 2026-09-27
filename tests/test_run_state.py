import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_workspace.run_state import inspect_state, tracked_stage, process_namespace
from paper_workspace.storage import read, write


class RunStateTests(unittest.TestCase):
    def test_completed_and_interrupted_states_are_durable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'state.json'
            with tracked_stage(path, 'judge'):
                self.assertEqual(inspect_state(path)['status'], 'running')
            self.assertEqual(read(path)['status'], 'complete')
            with self.assertRaises(KeyboardInterrupt):
                with tracked_stage(path, 'judge'):
                    raise KeyboardInterrupt()
            self.assertEqual(read(path)['status'], 'interrupted')

    def test_stale_pid_and_overdue_owner_are_distinguished_without_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'state.json'
            original = {'status':'running','pid':123,'process_identity':'old','deadline_at':0,
                        'process_namespace':process_namespace()}
            write(path, original)
            with patch('paper_workspace.run_state.process_identity', return_value='new'):
                self.assertEqual(inspect_state(path)['status'], 'interrupted')
            with patch('paper_workspace.run_state.process_identity', return_value='old'):
                self.assertEqual(inspect_state(path)['status'], 'overdue')
            self.assertEqual(read(path), original)

    def test_other_namespace_does_not_falsely_report_a_dead_process(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'state.json'
            write(path, {'status':'running','pid':123,'process_namespace':'another-namespace'})
            self.assertEqual(inspect_state(path)['status'], 'unverified')


if __name__ == '__main__':
    unittest.main()
