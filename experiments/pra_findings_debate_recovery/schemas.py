"""Structured records for finding-preserving debate and evaluation."""


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, maximum=None):
    value = {'type': 'array', 'items': items}
    if maximum is not None:
        value['maxItems'] = maximum
    return value


def enum(*values):
    return {'type': 'string', 'enum': list(values)}


TEXT = {'type': 'string'}
INTEGER = {'type': 'integer', 'minimum': 1}
SPAN = obj({'start': INTEGER, 'end': INTEGER})
SPANS = arr(SPAN, 3)
FINDING = obj({'claim': TEXT, 'evidence': SPANS, 'why_it_matters': TEXT,
               'remedy': TEXT, 'counterevidence': SPANS, 'limitations': TEXT,
               'severity': enum('major', 'minor', 'uncertain')})
PANEL = obj({'checks': arr(obj({'question': TEXT, 'outcome': enum('issue', 'answered', 'uncertain', 'not_applicable'),
                               'reason': TEXT, 'evidence': SPANS}), 5),
             'findings': arr(FINDING, 3),
             'score': {'type': 'integer', 'minimum': 1, 'maximum': 5},
             'confidence': {'type': 'integer', 'minimum': 1, 'maximum': 5}})
DEBATE = obj({'opening_argument': TEXT,
              'positions': arr(obj({'finding_id': TEXT, 'position': enum('uphold', 'qualify', 'refute', 'unresolved'),
                                    'argument': TEXT, 'evidence': SPANS, 'opponent_response': TEXT,
                                    'change_from_previous': TEXT})),
              'closing_argument': TEXT})
SYNTHESIS = obj({'resolutions': arr(obj({'finding_id': TEXT,
                                        'status': enum('upheld', 'qualified', 'refuted', 'unresolved', 'duplicate'),
                                        'reason': TEXT, 'evidence': SPANS, 'duplicate_of': TEXT}))})
EDITOR = obj({'selected_ids': arr(TEXT, 5),
              'dispositions': arr(obj({'finding_id': TEXT, 'action': enum('selected', 'merged', 'dropped'),
                                       'reason': TEXT, 'merged_into': TEXT})),
              'verdict': enum('accept', 'minor', 'major', 'reject')})
PACKET = obj({'concerns': arr(obj({'paragraph_ids': arr(INTEGER, 16)}), 5)})
JUDGE = obj({'matches': arr(obj({'reference_id': TEXT, 'candidate_ids': arr(TEXT),
                                'matched': {'type': 'boolean'}, 'reason': TEXT})),
             'support': arr(obj({'candidate_id': TEXT, 'label': enum('supported', 'contradicted', 'insufficient_evidence'),
                                'major': {'type': 'boolean'}, 'evidence': SPANS, 'reason': TEXT}))})
