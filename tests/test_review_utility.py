import unittest

from experiments.pra_review_utility import assess, DIMENSIONS, review_spans, hydrate_review_spans


class ReviewUtilityTests(unittest.TestCase):
    def fixture(self):
        anonymous={label:[{'finding_id':label+'1','comment':'Clarify allocation. Explain allocation.'}] for label in 'ABC'}
        conditions=[]
        for label in 'ABC':
            ratings=[{'point_id':label+str(i),'finding_id':label+'1','review_excerpt':excerpt,
                      'verdict':'valid_clarification','importance':'high','evidence':[{'quote':'Source'}],
                      'counterevidence':[]} for i,excerpt in enumerate(('Clarify allocation.','Explain allocation.'),1)]
            conditions.append({'label':label,'ratings':ratings,'overall_score':8,'overall_reason':'Useful',
                'dimensions':{k:{'score':4,'reason':'Useful'} for k in DIMENSIONS},
                'strongest_contribution':'Allocation','most_important_limitation':'Limited coverage'})
        value={'conditions':conditions,'issue_groups':[{'issue_id':'allocation','members':['A1','A2','B1','B2','C1','C2'],'reason':'Same question'}],
            'pairwise':[{'label_a':a,'label_b':b,'preferred_label':'tie','reason':'Equal'} for a,b in [('A','B'),('A','C'),('B','C')]],
            'preferred_label':'tie','preference_reason':'Equal usefulness','ranking_confidence':'medium'}
        return value,anonymous

    def test_reworded_points_do_not_inflate_valid_count(self):
        value,anonymous=self.fixture()
        result=assess(value,anonymous)
        self.assertEqual(result['metrics']['basic']['raw_point_count'],2)
        self.assertEqual(result['metrics']['basic']['distinct_valid_points'],1)

    def test_invented_review_excerpt_is_unscored_and_preference_provisional(self):
        value,anonymous=self.fixture()
        value['conditions'][0]['ratings'][0]['review_excerpt']='This was never said.'
        result=assess(value,anonymous)
        self.assertEqual(result['metrics']['basic']['unscored'],1)
        self.assertTrue(result['preference_provisional'])

    def test_review_handles_cannot_point_into_another_review(self):
        value,anonymous=self.fixture()
        spans=review_spans(anonymous)
        for c in value['conditions']:
            for r in c['ratings']:
                r.pop('review_excerpt')
                r['review_handle']='review-'+r['finding_id']+'-0'
        hydrated=hydrate_review_spans(value,spans)
        self.assertFalse(assess(hydrated,anonymous)['preference_provisional'])
        value['conditions'][0]['ratings'][0]['review_handle']='review-B1-0'
        with self.assertRaisesRegex(ValueError,'different review'):hydrate_review_spans(value,spans)

    def test_two_condition_comparison_preserves_pair_and_point_accounting(self):
        from experiments.pra_review_utility import schema
        value,anonymous=self.fixture()
        del anonymous['C']
        value['conditions']=value['conditions'][:2]
        value['pairwise']=value['pairwise'][:1]
        value['issue_groups'][0]['members']=['A1','A2','B1','B2']
        mapping={'A':'saved','B':'updated'}
        result=assess(value,anonymous,mapping)
        self.assertEqual(set(result['metrics']),{'saved','updated'})
        self.assertEqual(result['metrics']['saved']['distinct_valid_points'],1)
        self.assertEqual(schema(review_spans(anonymous),mapping)['properties']['pairwise']['maxItems'],1)
        value['pairwise']*=2
        with self.assertRaises(ValueError):assess(value,anonymous,mapping)


if __name__=='__main__':unittest.main()
