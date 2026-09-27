"""Check no-tool transport and isolation between shared review branches."""
import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from experiments.pra_three_condition import generate
from experiments.pra_three_condition.run import ORDERS,CONDITIONS
from paper_workspace.evidence_handles import build_registry
from paper_workspace.reviewer import save_initial_checkpoint
from paper_workspace.storage import read,write,digest


class FourConditionGeneration(unittest.TestCase):
    def test_basic_passes_have_no_tools_and_reuse_first_guarded_draft(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            base=root/'inputs'
            paper={'id':'paper','title':'An experiment','source_sha256':'source',
                'blocks':[{'id':'b1','text':'We studied 5 plants.','sha256':digest('We studied 5 plants.')}],
                'sections':[],'assets':[],'references':[],'statistics':{'total_words':4}}
            write(base/'workspace/paper.json',paper)
            write(base/'workspace/manifest.json',{'files':{'paper.json':digest((base/'workspace/paper.json').read_bytes())}})
            write(base/'images.json',[])
            write(root/'billing_confirmation.json',{'checked_at':time.time(),'no_paid_credits_verified':True})
            handle=build_registry(paper).handles[0].handle_id
            response={'summary':'Review','findings':[{'title':'Count','kind':'question','severity':'moderate',
                'comment':'How were plants allocated?','replacement':'','counterevidence':'','source_urls':[],
                'anchor_handle':handle,'manuscript_evidence_handles':[handle]}],
                'limitations':[],'investigation_summary':'Checked','discarded_hypotheses':[]}
            calls=[]
            def fake(protocol,out,prompt,schema,**kwargs):
                calls.append((prompt,kwargs))
                return copy.deepcopy(response)
            with patch.object(generate,'require_subscription'),patch.object(generate,'model_call',side_effect=fake):
                generate.basic(root,base,root/'basic',{},lambda n:None)
            self.assertEqual(len(calls),2)
            self.assertTrue(all(c[1]['tools'] is False for c in calls))
            self.assertNotIn('YOUR PRIOR DRAFT',calls[0][0])
            self.assertIn('How were plants allocated?',calls[1][0])
            self.assertNotIn('ADVISORY MANUSCRIPT CHECKS',calls[0][0])
            self.assertNotIn('RESULT MAP OVERVIEW',calls[0][0])

    def test_branch_clones_investigator_budget_and_excludes_debate_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            pra=root/'pra'
            write(pra/'sources/requests.json',{'limit':6,'requests':[{'first':True}]})
            write(pra/'source-cache/first.json',{'original':True})
            write(pra/'execution/workspace/tool-config.json',{'tool_limit':4,'source_state':str(pra/'sources')})
            save_initial_checkpoint(pra,'first prompt',{}, {'findings':[]},[])
            write(pra/'source-cache/debate.json',{'secret':'later evidence'})
            out=root/'ordinary'
            initial=generate.restore_checkpoint(pra/'initial-checkpoint',out,root/'paper')
            self.assertEqual(initial['prompt'],'first prompt')
            self.assertFalse((out/'source-cache/debate.json').exists())
            self.assertEqual(len(read(out/'sources/requests.json')['requests']),1)
            self.assertEqual(read(out/'execution/workspace/tool-config.json')['tool_limit'],2)
            write(pra/'initial-checkpoint/source-cache/first.json',{'tampered':True})
            with self.assertRaisesRegex(ValueError,'checkpoint changed'):
                generate.restore_checkpoint(pra/'initial-checkpoint',root/'other',root/'paper')

    def test_each_method_occupies_every_label_position(self):
        for index in range(4):
            self.assertEqual(sorted(order[index] for order in ORDERS.values()),sorted(CONDITIONS))


if __name__=='__main__':unittest.main()
