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


class MatchedTests(unittest.TestCase):
    def test_index_only_copies_source_in_order(self):
        body='Summary\n\nFirst complete concern.\n\nIts remedy.\n\nSecond complete concern.'
        result=core.index_findings({'concerns':[{'paragraph_ids':[2,3]},{'paragraph_ids':[4]}]},body,'R')
        self.assertEqual(result['R_F1']['text'],'First complete concern.\n\nIts remedy.')
        for groups in [[{'paragraph_ids':[4]},{'paragraph_ids':[2]}],[{'paragraph_ids':[9]}],[{'paragraph_ids':[2]},{'paragraph_ids':[2]}]]:
            with self.assertRaises(core.Blocked):core.index_findings({'concerns':groups},body,'R')

    def test_top_packet_preserves_lower_priority_in_full_ledger(self):
        records={str(i):{'text':('word '*200).strip()} for i in range(7)}
        original=copy.deepcopy(records)
        packet=core.top_packet(list(records),records)
        self.assertEqual(packet['ids'],['0','1','2','3'])
        self.assertEqual(packet['words'],800)
        self.assertEqual(records,original)

    def test_editor_cannot_silently_drop_a_retained_concern(self):
        source=core.chunks('Evidence in manuscript')
        value={'dispositions':{'f1':{'status':'minor','reason':'Still relevant','evidence_ids':[],'duplicate_of':''}},'ranking':[]}
        with self.assertRaises(core.Blocked):study.validate_editor(value,{'f1':{}},source)
        value['ranking']=['f1']
        self.assertEqual(study.validate_editor(value,{'f1':{}},source),{'f1'})
        value['dispositions']['f1']['status']='answered'
        value['ranking']=[]
        with self.assertRaises(core.Blocked):study.validate_editor(value,{'f1':{}},source)

    def test_network_retry_is_limited_and_preserves_failure(self):
        protocol=core.read(core.HERE/'protocol.json')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            node=root/'work/node'
            calls=[]
            def invoke(protocol_arg,out,text,schema,tools=False,label='call'):
                calls.append(out.name)
                if out.name=='attempt_1':
                    identity=core.shared.digest({'prompt':text,'schema':schema,'tools':tools,'protocol':protocol_arg})
                    core.write(out/'calls'/f'{identity}.json',{'ok':False,'error':'stream disconnected before completion'})
                    raise core.Blocked('Connection failure')
                return {'content':'Done'}
            with patch.object(core,'ROOT',root),patch.object(core.shared,'model_call',side_effect=invoke),patch.object(core.time,'sleep'):
                value=core.call(protocol,node,'same prompt',{},'node')
            self.assertEqual(value,{'content':'Done'})
            self.assertEqual(calls,['attempt_1','attempt_2'])
            self.assertEqual(len(list(node.glob('attempt_1/calls/*.json'))),1)
            self.assertTrue((node/'network_retry.json').exists())

    def test_validation_failure_does_not_retry(self):
        protocol=core.read(core.HERE/'protocol.json')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(core,'ROOT',Path(directory)),patch.object(core.shared,'model_call',side_effect=core.Blocked('schema error')) as model:
                with self.assertRaises(core.Blocked):core.call(protocol,Path(directory)/'work/node','prompt',{},'node')
                self.assertEqual(model.call_count,1)

    def test_matched_pipeline_and_editor_ablation(self):
        import jsonschema
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            inputs=root/'inputs/test'
            inputs.mkdir(parents=True)
            body='Summary\n\nThe comparison lacks a control. Add it.'
            manuscript='Original manuscript comparison.'
            (inputs/'manuscript.txt').write_text(manuscript)
            (inputs/'reviewer_1.md').write_text(body)
            request={'prompt':'Exact original strong-agent prompt','schema':{'type':'object'}}
            core.write(inputs/'review_request.json',request)
            core.write(inputs/'source_chunks.json',core.chunks(manuscript))
            core.write(inputs/'reference.json',{'concerns':[{'id':'R1','claim':'Missing control'}]})
            core.write(inputs/'reviewer_1_response.json',{'observed_tokens':100})
            protocol=core.read(core.HERE/'protocol.json')
            protocol['paper_ids']=['test']
            calls=[]
            barrier=threading.Barrier(2,timeout=5)
            def fake(protocol_arg,node,text,schema,label,manuscript=None):
                node.mkdir(parents=True,exist_ok=True)
                calls.append((label,text,schema,manuscript))
                if label in ['reviewer_2','reviewer_3']:
                    self.assertEqual(text,request['prompt'])
                    self.assertEqual(schema,request['schema'])
                    self.assertEqual(manuscript,'Original manuscript comparison.')
                    barrier.wait()
                    return {'content':body}
                jsonschema.Draft202012Validator.check_schema(schema)
                if label.endswith('_index'):return {'concerns':[{'paragraph_ids':[2]}]}
                if label.endswith('_debate'):return {'interventions':[]}
                if label in ['editor_only','debate_editor']:
                    ids=list(schema['properties']['dispositions']['properties'])
                    return {'summary':'Summary','strengths':'Strengths','unresolved_note':'None',
                            'dispositions':{i:{'status':'major','reason':'Keep distinct issue','evidence_ids':['E0001'],'duplicate_of':''} for i in ids},
                            'ranking':ids}
                ids=list(schema['properties']['support']['properties'])
                self.assertNotIn('reviewer_1',text)
                return {'matches':{'R1':{'candidate_ids':ids,'reason':'Matches'}},
                        'support':{i:{'label':'supported','major':True,'reason':'Evidence','evidence_ids':['E0001']} for i in ids}}
            with patch.object(core,'ROOT',root),patch.object(core,'call',side_effect=fake):
                generation=study.generate(protocol,'test')
                study.evaluate(protocol,'test',generation)
                result=study.summarize(protocol)
            self.assertEqual(len(calls),12)
            editors={label:text for label,text,_,_ in calls if label in ['editor_only','debate_editor']}
            self.assertEqual(editors['editor_only'].split('\nDISCUSSION\n')[0],editors['debate_editor'].split('\nDISCUSSION\n')[0])
            self.assertEqual(result['missing'],[])
            self.assertTrue(all(r['coverage_both']==1 for r in result['rows']))


if __name__=='__main__':unittest.main()
