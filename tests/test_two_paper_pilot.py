"""Checks for pilot leakage controls and complete evaluation accounting."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_workspace.investigation import Investigation
from paper_workspace.reviewer import editor_package
from paper_workspace.storage import digest,write

spec=importlib.util.spec_from_file_location('two_paper_runner',Path(__file__).parents[1]/'experiments/pra_workspace_two_paper/run.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PilotIntegrity(unittest.TestCase):
    def setUp(self):
        self.paper={'id':'paper','blocks':[{'id':'b1','text':'The trial had no control group.'}]}
        self.anonymous={label:[{'finding_id':label+'1','kind':'question'}] for label in ('A','B')}
        self.concerns=[{'id':'h1'}]
        self.value={'conditions':[{'label':label,
                    'ratings':[{'finding_id':label+'1','support':'supported','edit_fidelity':'not_an_edit','evidence':[{'block_id':'b1','quote':'no control group'}]}],
                    'matches':[{'human_concern_id':'h1','finding_ids':[label+'1'],'match':'direct'}]} for label in ('A','B')]}

    def test_evaluation_requires_source_quotes_and_complete_accounting(self):
        runner.validate_evaluation(self.value,self.anonymous,self.concerns,self.paper)
        for change in ('quote','missing','duplicate','foreign','edit_kind'):
            value=copy.deepcopy(self.value)
            row=value['conditions'][0]
            if change=='quote':row['ratings'][0]['evidence'][0]['quote']='made up'
            if change=='missing':row['matches']=[]
            if change=='duplicate':row['ratings']*=2
            if change=='foreign':row['matches'][0]['finding_ids']=['B1']
            if change=='edit_kind':row['ratings'][0]['edit_fidelity']='introduces_unsupported_claim'
            with self.subTest(change=change),self.assertRaises(ValueError):
                runner.validate_evaluation(value,self.anonymous,self.concerns,self.paper)

    def test_pilot_cannot_search_public_review_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/'paper.json',self.paper)
            write(root/'manifest.json',{'files':{'paper.json':digest((root/'paper.json').read_bytes())}})
            investigation=Investigation({'paper':directory,'output':str(root/'out'),'cache':str(root/'cache'),
                                        'allow_literature':False})
            with patch.object(investigation,'fetch',side_effect=AssertionError('Network is forbidden')):
                result=investigation.call('search_literature',{'query':'public review of this paper'})
            self.assertIn('disabled',result['unavailable'])

    def test_debate_can_cite_newly_inspected_source_blocks(self):
        concern={'title':'Control','block_id':'b0','quote':'The trial','comment':'Check control','evidence_blocks':['b0']}
        final={'summary':'Resolved','findings':[],'source_dispositions':[{
               'source_finding_id':'r1-f1','disposition':'rejected','final_finding_numbers':[],
               'reason':'The methods identify the control.','evidence_blocks':['b1']}]}
        result=editor_package(final,[{'findings':[concern]}],self.paper)
        self.assertEqual(result['verification_queue_count'],0)
        self.assertEqual(result['source_disposition_validation'][0]['status'],'valid')


if __name__=='__main__':unittest.main()
