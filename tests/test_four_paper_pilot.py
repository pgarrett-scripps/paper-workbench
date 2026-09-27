"""Offline validation of four-paper isolation, paired labels, and image limits."""
import copy
import contextlib
import importlib.util
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_workspace.discovery import AREAS
from paper_workspace.storage import digest, read, write

spec=importlib.util.spec_from_file_location('four_paper_runner',Path(__file__).parents[1]/'experiments/pra_workspace_four_paper/run.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FourPaperPilot(unittest.TestCase):
    def test_generation_is_isolated_and_frozen_before_balanced_evaluation(self):
        finding={'title':'Clarify count','block_id':'b1','quote':'5 plants','kind':'question',
                 'severity':'moderate','comment':'How were plants selected?', 'replacement':'',
                 'evidence_blocks':['b1'],'counterevidence':'Count is reported.','source_urls':[]}
        first={'summary':'A question.','findings':[finding],'limitations':[],
               'investigation_summary':'Count considered.','discarded_hypotheses':[],
               'coverage_checks':[{'area':area,'status':'unresolved','reason':'Limited evidence.','evidence':[]} for area in AREAS]}
        debate={key:copy.deepcopy(value) for key,value in first.items() if key!='coverage_checks'}
        debate['source_dispositions']=[{'source_finding_id':'r1-f1','disposition':'retained',
                                       'final_finding_numbers':[1],'reason':'Clarification is useful.','evidence_blocks':['b1']}]
        evaluated={'conditions':[{'label':label,'ratings':[{'finding_id':label+'1','support':'supported',
                    'evidence':[{'block_id':'b1','quote':'5 plants'}],'edit_fidelity':'not_an_edit'}],
                    'matches':[{'human_concern_id':'h1','finding_ids':[label+'1'],'match':'direct'}]}
                    for label in ('A','B')],'limitations':[]}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            papers=[]
            hashes={}
            for n in range(1,5):
                pid=f'paper-{n}'
                work=root/'workspaces'/pid
                paper={'id':pid,'title':'A synthetic experiment','source_sha256':'source',
                       'blocks':[{'id':'b1','text':'We studied 5 plants.','sha256':digest('We studied 5 plants.')}],
                       'sections':[],'assets':[],'references':[]}
                write(work/'paper.json',paper)
                (work/'manuscript.md').write_text('[b1] We studied 5 plants.')
                write(work/'manifest.json',{'files':{name:digest((work/name).read_bytes()) for name in ('paper.json','manuscript.md')}})
                write(root/'diagnostics'/f'{pid}.json',{})
                human=root/'evaluation-only'/f'{pid}.txt'
                human.parent.mkdir(exist_ok=True)
                human.write_text('HIDDEN_HUMAN_REFERENCE')
                concern=root/'evaluation-only'/f'{pid}.json'
                write(concern,{'concerns':[{'id':'h1','quote':'HIDDEN_HUMAN_REFERENCE','manuscript_assessable':True}]})
                item={'id':pid,'human_reviews':str(human),'human_concerns':str(concern),'literature_cutoff':'2024-01-01'}
                papers.append(item)
                hashes[pid]={key:digest(Path(item[key]).read_bytes()) for key in ('human_reviews','human_concerns')}
            write(root/'manifest.json',{'human_reference_hashes':hashes})
            write(root/'billing_confirmation.json',{'checked_at':time.time(),'no_paid_credits_verified':True})
            seen=[]

            def fake_call(protocol,execution,prompt,schema,**kwargs):
                label=kwargs['label']
                seen.append(label)
                if label.endswith('evaluation'):
                    self.assertIn('HIDDEN_HUMAN_REFERENCE',prompt)
                    frozen=read(root/'generation-lock.json')
                    self.assertTrue(frozen)
                    self.assertTrue(all(digest((root/name).read_bytes())==sha for name,sha in frozen.items()))
                    self.assertEqual(sum(not x.endswith('evaluation') for x in seen),8)
                    result=evaluated
                else:
                    self.assertNotIn('HIDDEN_HUMAN_REFERENCE',prompt)
                    config=read(execution/'workspace/tool-config.json')
                    self.assertFalse(config['allow_literature'])
                    self.assertNotIn('evaluation-only',config['paper'])
                    result=debate if label.endswith('debate') else first
                usage=execution/'usage.jsonl'
                usage.parent.mkdir(parents=True,exist_ok=True)
                with usage.open('a') as stream:
                    stream.write(json.dumps({'label':label,'observed_tokens':10,'ok':True})+'\n')
                return copy.deepcopy(result)

            with patch.object(runner,'ROOT',root),patch.object(runner,'require_subscription'), \
                    patch.object(runner,'compact_summary',return_value={}), \
                    patch.object(runner,'inspected_images',return_value=[]), \
                    patch.object(runner,'model_call',side_effect=fake_call) as invoke, \
                    contextlib.redirect_stdout(io.StringIO()):
                runner.execute(papers,{'max_calls_per_condition':12,'observed_token_stop':1200000})
            self.assertEqual(invoke.call_count,12)
            self.assertTrue(all(label.endswith('evaluation') for label in seen[-4:]))
            self.assertEqual(read(root/'results.json')['calls'],12)
            for n in range(1,5):
                pid=f'paper-{n}'
                mapping=read(root/'evaluation'/pid/'label-map.json')
                self.assertEqual(mapping['A'],'investigator' if n%2 else 'debate')
                package=read(root/'responses'/pid/'review-package.json')
                self.assertEqual(len(package['coverage_record']['areas']),6)
                self.assertEqual(len(package['source_findings']),1)

    def test_image_limit_is_shared_deterministic_and_disclosed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            files=[]
            for n in range(5):
                path=root/f'{n}.png'
                path.write_bytes(bytes([n]))
                files.append((path,f'Original PDF page {n+1}'))
            with patch.object(runner,'inspected_images',side_effect=[files[:3],files[2:]]):
                packet=runner.shared_images({},root,{'id':'paper-1'})
            self.assertEqual(len(packet['included']),4)
            self.assertEqual(len(packet['omitted']),1)
            self.assertEqual(packet['omitted'][0]['label'],'Original PDF page 5')

    def test_duplicate_manuscript_dois_are_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            write(root/'source-selection.json',{'papers':[{'id':f'paper-{n}','doi':'10.1/SAME'} for n in range(1,5)]})
            with patch.object(runner,'ROOT',root),patch.object(runner,'import_paper') as invoke:
                with self.assertRaisesRegex(ValueError,'distinct source DOIs'):
                    runner.prepared()
            invoke.assert_not_called()


if __name__=='__main__':
    unittest.main()
