import core

obj,arr,enum=core.shapes.obj,core.shapes.arr,core.shapes.enum
TEXT=core.shapes.TEXT
CITES=core.shapes.CITES


def index(n):
    return obj({'concerns':arr(obj({'paragraph_ids':arr({'type':'integer','minimum':1,'maximum':n})}))})


def debate(source,findings):
    entry=obj({'finding_ids':core.shapes.id_array(findings,4),'position':enum(['defend','challenge','qualify','duplicate']),
               'response_to':TEXT,'reason':TEXT,'evidence_ids':CITES,'counterevidence_ids':CITES})
    return core.shapes.evidence(obj({'interventions':arr(entry,4)}),source)


def editor(source,findings):
    item=obj({'status':enum(['major','minor','unresolved','answered','duplicate']),
              'reason':TEXT,'evidence_ids':CITES,'duplicate_of':enum(['']+list(findings))})
    return core.shapes.evidence(obj({'summary':TEXT,'strengths':TEXT,'unresolved_note':TEXT,
                                    'dispositions':obj({f:item for f in findings}),
                                    'ranking':core.shapes.id_array(findings,len(findings))}),source)


def judge(source,refs,findings):
    return core.shapes.judge(source,refs,findings)
