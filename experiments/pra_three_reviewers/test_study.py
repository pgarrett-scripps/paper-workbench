import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import core
import schemas
import study


def finding():
    return {'claim':'The central comparison lacks a matched control.',
            'why_it_matters':'The reported effect cannot isolate the mechanism.',
            'remedy':'Add the matched control.','limitations':'Only supplied text was assessed.',
            'evidence_ids':['E0001'],'counterevidence_ids':[],'severity':'major'}


class ExperimentTests(unittest.TestCase):
    def test_chunks_copy_source_and_reject_unknown_ids(self):
        text='\n'.join(f'Original line {n}' for n in range(19))
        chunks=core.chunks(text)
        self.assertEqual('\n'.join(r['text'] for r in chunks.values()),text)
        self.assertEqual(core.resolve(['E0002'],chunks)[0]['start'],9)
        with self.assertRaises(core.Blocked):core.resolve(['E9999'],chunks)
        with self.assertRaises(core.Blocked):core.resolve(['E0001','E0001'],chunks)

    def test_selection_preserves_text_and_enforces_budget(self):
        f=finding()
        original=copy.deepcopy(f)
        body=core.selected(['f1'],{'f1':f})
        for field in ['claim','why_it_matters','remedy','limitations']:self.assertIn(f[field],body)
        self.assertEqual(f,original)
        with self.assertRaises(core.Blocked):core.selected(['f1','f1'],{'f1':f})
        f['claim']='word '*901
        with self.assertRaises(core.Blocked):core.selected(['f1'],{'f1':f})

    def test_source_schema_has_closed_set_of_evidence_ids(self):
        import jsonschema
        schema=schemas.reviewer(['E0001'])
        jsonschema.Draft202012Validator.check_schema(schema)
        value={'summary':'Summary','strengths':'Strengths','findings':[finding()]}
        jsonschema.validate(value,schema)
        value['findings'][0]['evidence_ids']=['E0002']
        with self.assertRaises(jsonschema.ValidationError):jsonschema.validate(value,schema)

    def test_budget_counts_inflight_requests(self):
        protocol=core.read(core.HERE/'protocol.json')
        protocol['max_total_calls']=2
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(core,'inflight',2),patch.object(core,'usage',return_value=[]),patch.object(core.shared,'model_call') as model:
                with self.assertRaises(core.Blocked):core.call(protocol,Path(directory),'text',{},'test')
                model.assert_not_called()

    def test_parallel_reviews_debate_and_shared_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            target=root/'inputs/test'
            target.mkdir(parents=True)
            core.write(target/'source_chunks.json',core.chunks('The paper reports a comparison.'))
            core.write(target/'reference.json',{'concerns':[{'id':'R1','claim':'Missing matched control'}]})
            core.write(target/'single_agent_packet.json',{'concerns':[{'id':'C1','source_quote':'Missing matched control.'}]})
            (target/'single_agent_usage.jsonl').write_text('')
            protocol=core.read(core.HERE/'protocol.json')
            protocol['paper_ids']=['test']
            calls=[]
            barrier=threading.Barrier(3,timeout=5)
            def fake(protocol_arg,out,text,schema,label):
                calls.append((label,text))
                if label in ['reviewer_1','reviewer_2','reviewer_3']:
                    self.assertNotIn('ALL INITIAL REVIEWS',text)
                    self.assertNotIn('Missing matched control',text)
                    barrier.wait()
                    return {'summary':'Summary','strengths':'Strengths','findings':[finding()]}
                ids=[f'reviewer_{n}_F1' for n in [1,2,3]]
                if label.endswith('_discussion'):
                    self.assertIn('ALL INITIAL REVIEWS',text)
                    self.assertNotIn('HUMAN-DERIVED REFERENCES',text)
                    return {'positions':{i:{'position':'keep','reason':'Evidence survives','evidence_ids':['E0001']} for i in ids}}
                if label=='moderator':
                    return {'resolutions':{i:{'status':'supported','reason':'Evidence','evidence_ids':['E0001'],'duplicate_of':''} for i in ids},
                            'selected_ids':ids[:2],'discussion_summary':'Agreement after discussion'}
                if label=='editor':
                    return {'selected_ids':ids[:1],'dispositions':{i:'Selected' if i==ids[0] else 'Redundant' for i in ids},
                            'decision':'major_revision','rationale':'Important control'}
                self.assertTrue(label.startswith('judge_'))
                candidate_ids=list(schema['properties']['support']['properties'])
                self.assertNotIn('reviewer_1',text)
                return {'matches':{'R1':{'candidate_ids':candidate_ids,'reason':'Same concern'}},
                        'support':{i:{'label':'supported','major':True,'evidence_ids':['E0001'],'reason':'Located'} for i in candidate_ids}}
            with patch.object(core,'ROOT',root),patch.object(core,'call',side_effect=fake):
                generation=study.generate(protocol,'test')
                study.evaluate(protocol,'test',generation)
                result=study.summarize(protocol)
            self.assertEqual(len(calls),10)
            self.assertEqual(len(generation['discussion']),3)
            self.assertEqual(len(generation['records']),3)
            self.assertEqual(generation['stage_ids']['final'],['reviewer_1_F1'])
            self.assertTrue(all(r['coverage_both']==1 for r in result['rows']))
            self.assertEqual(result['missing'],[])


if __name__=='__main__':unittest.main()
