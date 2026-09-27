"""Check sequential baseline limits and its isolated continuation context."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.pra_ensemble_fresh import generate
from paper_workspace.evidence_handles import build_registry
from paper_workspace.storage import read,write,digest


class SequentialBaselineTests(unittest.TestCase):
    def test_three_pass_baseline_keeps_its_own_history_and_secondary_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            base=root/'inputs'
            paper={'id':'paper','title':'Plants','source_sha256':'original','blocks':[
                {'id':'b1','text':'Five plants were studied.','sha256':digest('Five plants were studied.')}],
                'sections':[],'assets':[],'references':[],'statistics':{'total_words':4}}
            write(base/'workspace/paper.json',paper)
            write(base/'workspace/manifest.json',{'files':{'paper.json':digest((base/'workspace/paper.json').read_bytes())}})
            write(base/'images.json',[])
            write(root/'billing.json',{'checked_at':time.time(),'no_paid_credits_verified':True})
            handle=build_registry(paper).handles[0].handle_id
            draft={'summary':'First draft','findings':[],'limitations':[],'investigation_summary':'Reviewed','discarded_hypotheses':[]}
            write(root/'shared/editor-package.json',draft)
            write(root/'shared/editor-package.json',{**draft,
                'result_map':{'data':'REDUNDANT WORKSPACE METADATA'},
                'evidence_handle_audit':{'data':'REDUNDANT HANDLE AUDIT'},
                'domain_profile':{'data':'REDUNDANT PROFILE'}})
            write(root/'shared/execution/calls/one.request.json',{'prompt':'Shared manuscript prompt. At most 4 tool calls.'})
            write(root/'independent/editor-package.json',{'secret':'SIBLING CONTENT MUST STAY HIDDEN'})
            seen=[]
            def fake(protocol,out,prompt,schema,**kwargs):
                seen.append({'prompt':prompt,'schema':schema,'config':read(out/'workspace/tool-config.json')})
                finding={'title':'Allocation','kind':'question','severity':'moderate','comment':'Clarify allocation.',
                    'replacement':'','counterevidence':'','source_urls':[],'source_evidence':[],
                    'anchor_handle':handle,'manuscript_evidence_handles':[handle]}
                value={**copy.deepcopy(draft),'findings':[finding]}
                if len(seen)==2:value['secondary_findings']=[{**finding,'title':'Replication','comment':'Clarify replication.'}]
                return value
            protocol={'literature_cutoff':'2026-09-25'}
            with patch.object(generate,'require_subscription'),patch.object(generate,'model_call',side_effect=fake):
                generate.sequential(root,base,root/'sequential-2',protocol,root/'billing.json',[root/'shared'])
                value=generate.sequential(root,base,root/'sequential-3',protocol,root/'billing.json',
                                          [root/'shared',root/'sequential-2'],final=True)
            self.assertEqual([c['config']['tool_limit'] for c in seen],[4,2])
            self.assertEqual([c['config']['external_request_limit'] for c in seen],[6,2])
            self.assertEqual([c['schema']['properties']['findings']['maxItems'] for c in seen],[10,5])
            self.assertIn('First draft',seen[1]['prompt'])
            self.assertIn('Clarify allocation.',seen[1]['prompt'])
            self.assertTrue(all('SIBLING CONTENT' not in c['prompt'] for c in seen))
            self.assertTrue(all('REDUNDANT' not in c['prompt'] for c in seen))
            self.assertEqual(value['secondary_findings'][0]['block_id'],'b1')
            self.assertNotEqual(seen[0]['config']['source_state'],seen[1]['config']['source_state'])
            with self.assertRaisesRegex(ValueError,'already prepared'):
                generate.sequential(root,base,root/'sequential-3',protocol,root/'billing.json',[root/'shared'],final=True)

    def test_projection_preserves_scientific_history_without_mutating_artifact(self):
        value={'summary':'Summary','findings':[{'comment':'Primary'}],
               'secondary_findings':[{'comment':'Secondary'}],
               'limitations':['Uncertain'], 'investigation_summary':'Checked outcomes',
               'discarded_hypotheses':['Rejected with evidence'],
               'result_map':{'large':'workspace data'},'source_cards':[{'source':'separately supplied'}]}
        result=generate.prior_review_context(value)
        self.assertNotIn('result_map',result)
        self.assertNotIn('source_cards',result)
        self.assertEqual(result['secondary_findings'],value['secondary_findings'])
        self.assertEqual(result['discarded_hypotheses'],value['discarded_hypotheses'])
        result['findings'][0]['comment']='Changed'
        self.assertEqual(value['findings'][0]['comment'],'Primary')


if __name__=='__main__':unittest.main()
