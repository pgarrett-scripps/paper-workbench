"""Offline checks for preservation, evidence scope, and real graph routing."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core
import revision
import study


def finding(identifier='F1'):
    return {'id':identifier,'claim':'The comparison omits a control.','evidence':[{'start':1,'end':1}],
            'why_it_matters':'The reported difference cannot isolate the proposed mechanism.',
            'remedy':'Add the matched control.','counterevidence':[],'limitations':'Only the supplied text was checked.',
            'severity':'major','resolved_evidence':[{'start':1,'end':1,'text':'A study.'}],
            'resolved_counterevidence':[],'evidence_spans_valid':True}


class RevisionTests(unittest.TestCase):
    def test_spans_are_exact_and_out_of_range_is_rejected(self):
        self.assertEqual(core.resolve_spans([{'start':2,'end':3}], 'One\nTwo\nThree')[0]['text'],'Two\nThree')
        for spans in ([{'start':0,'end':1}],[{'start':1,'end':9}],[{'start':1,'end':4}]):
            with self.assertRaises(core.Blocked):core.resolve_spans(spans,'One\nTwo\nThree')

    def test_invalid_evidence_is_flagged_not_fabricated(self):
        value=core.attach_evidence({'evidence':[{'start':1,'end':999}]},'Text')
        self.assertFalse(value['evidence_spans_valid'])
        self.assertEqual(value['resolved_evidence'],[])

    def test_rounds_never_see_current_opponent(self):
        state={'debate':[{'role':'advocate','round':1,'content':'old A'},
                         {'role':'skeptic','round':1,'content':'old S'},
                         {'role':'skeptic','round':2,'content':'current S'}]}
        self.assertEqual(revision.prior_turns(state,1),[])
        self.assertEqual(len(revision.prior_turns(state,2)),2)
        self.assertNotIn('current S',json.dumps(revision.prior_turns(state,2)))

    def test_editor_preserves_all_selected_finding_fields(self):
        f=finding()
        original=copy.deepcopy(f)
        decision={'selected_ids':['F1'],'dispositions':[{'finding_id':'F1','action':'selected','reason':'Central issue','merged_into':''}]}
        body=revision.render_selected([f],[{'finding_id':'F1','status':'qualified','reason':'The omission is unresolved.'}],decision)
        for key in ['claim','why_it_matters','remedy','limitations']:self.assertIn(f[key],body)
        self.assertIn('Provisional concern',body)
        self.assertEqual(f,original)
        with self.assertRaises(core.Blocked):
            revision.render_selected([f],[{'finding_id':'F1','status':'refuted','reason':'Answered'}],decision)

    def test_every_finding_requires_a_disposition(self):
        with self.assertRaises(core.Blocked):
            revision.render_selected([finding()],[{'finding_id':'F1','status':'upheld','reason':'Evidence'}],
                                     {'selected_ids':[],'dispositions':[]})

    def test_normalization_only_copies_selected_source_paragraphs(self):
        body='Summary.\n\nComplete criticism with evidence.\n\nA concrete remedy.'
        result=core.packet_from_paragraphs({'concerns':[{'paragraph_ids':[2,3]}]},body)
        self.assertEqual(result[0]['source_quote'],'Complete criticism with evidence.\n\nA concrete remedy.')
        for value in ({'concerns':[{'paragraph_ids':[8]}]}, {'concerns':[{'paragraph_ids':[2]},{'paragraph_ids':[2]}]}):
            with self.assertRaises(core.Blocked):core.packet_from_paragraphs(value,body)
        with self.assertRaises(core.Blocked):core.packet_from_paragraphs({'concerns':[{'paragraph_ids':[2,3]}]},body,maximum=2)

    def test_judge_cannot_invent_ids_or_evidence(self):
        value={'matches':[{'reference_id':'R1','candidate_ids':['C1'],'matched':True,'reason':'same'}],
               'support':[{'candidate_id':'C1','label':'supported','major':True,'evidence':[{'start':1,'end':9}],'reason':'test'}]}
        study.validate_judgment(value,[{'id':'R1'}],[{'id':'C1'}],'One line')
        self.assertFalse(value['support'][0]['evidence_valid'])
        value['matches'][0]['candidate_ids']=['C9']
        with self.assertRaises(core.Blocked):study.validate_judgment(value,[{'id':'R1'}],[{'id':'C1'}],'One line')

    def test_decisive_outcome_requires_located_evidence(self):
        row={'finding_id':'f1','status':'refuted','reason':'Claimed answer','evidence':[],'duplicate_of':''}
        result=revision.resolve_outcome(row,'Original manuscript')
        self.assertEqual(result['status'],'unresolved')
        self.assertEqual(result['requested_status'],'refuted')
        self.assertEqual(row['status'],'refuted')

    def test_real_plugin_graph_retains_panel_and_two_rounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'inputs/test').mkdir(parents=True)
            manuscript='# Test paper\n\n## Methods\n\n'+('The study compared two methods and reports data.\n'*100)
            (root/'inputs/test/manuscript.txt').write_text(manuscript)
            protocol=core.read(core.HERE/'protocol.json')
            sys.path.insert(0,str(Path(protocol['parent_root'])/'source'))
            calls=[]
            def invoke(root_arg, protocol_arg, out, text, output_schema, label):
                calls.append((label,text))
                if label in revision.REVIEWERS+revision.AUDITORS:
                    f=finding()
                    return {'checks':[],'findings':[{k:f[k] for k in ['claim','evidence','why_it_matters','remedy','counterevidence','limitations','severity']}], 'score':3,'confidence':3}
                ids=[f'{role}:1' for role in revision.REVIEWERS+revision.AUDITORS]
                if '_round_' in label:
                    return {'opening_argument':'Position','closing_argument':'Conclusion',
                            'positions':[{'finding_id':i,'position':'qualify','argument':'Check original evidence',
                                          'evidence':[{'start':1,'end':1}], 'opponent_response':'Response', 'change_from_previous':'Retained'} for i in ids]}
                if label=='debate_synthesis':
                    return {'resolutions':[{'finding_id':i,'status':'qualified','reason':'Still uncertain',
                                            'evidence':[{'start':1,'end':1}],'duplicate_of':''} for i in ids]}
                if label=='editor':
                    return {'selected_ids':[ids[0]],'verdict':'major','dispositions':[
                        {'finding_id':i,'action':'selected' if i==ids[0] else 'dropped','reason':'Priority choice','merged_into':''} for i in ids]}
                self.fail(label)
            with patch.object(core,'verify',return_value=(protocol,{})),patch.object(core.shared,'require_subscription'),patch.object(core,'call',side_effect=invoke),patch('builtins.print'):
                revision.generate(root,'test')
            self.assertEqual(len(calls),13)
            state=core.read(root/'generation/test/pra_revised/state.json')
            self.assertEqual(len(state['reports']),5)
            self.assertEqual(len(state['audits']),2)
            self.assertEqual(len(state['debate']),4)
            self.assertEqual(state['debate_round'],2)
            self.assertEqual(len(revision.ledger(state)),7)
            for label,text in calls:
                if label.endswith('_round_1'):
                    self.assertTrue(text.endswith('PRIOR ROUNDS ONLY\n[]'))
                if label.endswith('_round_2'):
                    history=json.loads(text.split('PRIOR ROUNDS ONLY\n')[-1])
                    self.assertEqual({t['role'] for t in history},{'advocate','skeptic'})
                    self.assertTrue(all(t['round']==1 for t in history))
            self.assertEqual(core.read(root/'generation/test/pra_revised/result.json')['debate_turns'],4)


if __name__=='__main__':unittest.main()
