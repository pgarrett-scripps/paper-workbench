"""Dynamic enums prevent invalid manuscript coordinates or finding IDs."""

TEXT={'type':'string'}


def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def enum(values):
    return {'type':'string','enum':list(values)}


def arr(items,maximum=None):
    result={'type':'array','items':items}
    if maximum is not None:result['maxItems']=maximum
    return result


def evidence(base,ids):
    return {**base,'$defs':{'source_id':enum(ids)}}


CITES=arr({'$ref':'#/$defs/source_id'},4)


def reviewer(ids):
    finding=obj({'claim':TEXT,'why_it_matters':TEXT,'remedy':TEXT,'limitations':TEXT,
                 'evidence_ids':CITES,'counterevidence_ids':CITES,'severity':enum(['major','minor','uncertain'])})
    return evidence(obj({'summary':TEXT,'strengths':TEXT,'findings':arr(finding,5)}),ids)


def discuss(ids,fids):
    item=obj({'position':enum(['keep','drop','uncertain']),'reason':TEXT,'evidence_ids':CITES})
    return evidence(obj({'positions':obj({f:item for f in fids})}),ids)


def id_array(ids,maximum=5):
    return arr(enum(ids),maximum) if ids else arr(TEXT,0)


def moderate(ids,fids):
    item=obj({'status':enum(['supported','unsupported','uncertain','duplicate']),
              'reason':TEXT,'evidence_ids':CITES,'duplicate_of':enum(['']+list(fids))})
    return evidence(obj({'resolutions':obj({f:item for f in fids}),'selected_ids':id_array(fids),
                         'discussion_summary':TEXT}),ids)


def editor(fids,eligible):
    return obj({'selected_ids':id_array(eligible),'dispositions':obj({f:TEXT for f in fids}),
                'decision':enum(['accept','minor_revision','major_revision','reject']),'rationale':TEXT})


def judge(ids,refs,candidates):
    match=obj({'candidate_ids':id_array(candidates,len(candidates)),'reason':TEXT})
    support=obj({'label':enum(['supported','contradicted','insufficient_evidence']),
                 'major':{'type':'boolean'},'evidence_ids':CITES,'reason':TEXT})
    return evidence(obj({'matches':obj({r:match for r in refs}),
                         'support':obj({c:support for c in candidates})}),ids)
