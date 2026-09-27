import copy
import unittest
from unittest.mock import patch

from experiments import pra_simple_baseline as experiment


class SimpleBaselineTests(unittest.TestCase):
    def value(self):
        return {'conditions':[], 'issue_groups':[], 'preferred_label':'C', 'pairwise':[
            {'label_a':'A','label_b':'B','preferred_label':'B','reason':'Supported coverage'},
            {'label_a':'A','label_b':'C','preferred_label':'C','reason':'Supported coverage'},
            {'label_a':'B','label_b':'C','preferred_label':'tie','reason':'Equivalent quality'}]}

    def check(self, value):
        with patch.object(experiment,'audit',return_value={'valid_rating_ids':[],'invalid_ratings':[]}), \
             patch.object(experiment,'validate_issue_partition'):
            return experiment.audit_comparison(value,{}, {}, [])

    def test_all_three_reports_can_win_and_every_pair_is_required(self):
        self.assertIn('C',experiment.comparison_schema()['properties']['preferred_label']['enum'])
        self.check(self.value())
        duplicate=self.value()
        duplicate['pairwise'][2]=copy.deepcopy(duplicate['pairwise'][0])
        with self.assertRaisesRegex(ValueError,'exactly once'):self.check(duplicate)
        foreign=self.value()
        foreign['pairwise'][0]['preferred_label']='C'
        with self.assertRaisesRegex(ValueError,'Invalid pairwise'):self.check(foreign)


if __name__=='__main__':unittest.main()
