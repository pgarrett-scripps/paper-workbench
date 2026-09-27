"""Closed evidence and case identifiers for the investigation workflow."""

TEXT = {"type": "string"}


def obj(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def enum(values):
    return {"type": "string", "enum": list(values)}


def arr(item, maximum=None):
    result = {"type": "array", "items": item}
    if maximum is not None:
        result["maxItems"] = maximum
    return result


def ids(values, maximum=None):
    return arr(enum(values), maximum) if values else arr(TEXT, 0)


def cites(source):
    return arr({"$ref": "#/$defs/source_id"}, 6)


def with_source(function):
    def wrapped(source, *args):
        value = function(source, *args)
        value["$defs"] = {"source_id": enum(source)}
        return value
    return wrapped


def case(source):
    return obj({"text": TEXT, "evidence_ids": cites(source), "counterevidence_ids": cites(source),
                "kind": enum(["error", "missing_evidence", "scope", "specification"]),
                "severity": enum(["major", "minor", "uncertain"]),
                "test_receipts": arr(TEXT, 6)})


@with_source
def mapping(source):
    claim = obj({"claim": TEXT, "support": cites(source), "prerequisites": TEXT,
                 "check": TEXT, "innocent_explanation": TEXT})
    return obj({"claims": arr(claim, 8), "method_reconstruction": TEXT,
                "work_orders": obj({key: TEXT for key in "ABC"})})


@with_source
def investigation(source):
    return obj({"investigation_log": TEXT, "findings": arr(case(source), 6)})


@with_source
def defense(source, cases):
    item = obj({"position": enum(["answered", "partially_answered", "conceded", "unresolved"]),
                "response": TEXT, "evidence_ids": cites(source), "test_receipts": arr(TEXT, 6)})
    return obj({"answers": obj({key: item for key in cases})})


@with_source
def reply(source, cases):
    item = obj({"position": enum(["retain", "revise", "withdraw", "unresolved"]),
                "response": TEXT, "final_concern": case(source)})
    return obj({"replies": obj({key: item for key in cases})})


@with_source
def final(source, cases):
    item = obj({"status": enum(["retain", "unresolved", "answered", "duplicate"]),
                "reason": TEXT, "evidence_ids": cites(source), "duplicate_of": enum([""] + list(cases))})
    return obj({"summary": TEXT, "strengths": TEXT,
                "dispositions": obj({key: item for key in cases}),
                "ranking": ids(cases, len(cases)), "selected_ids": ids(cases, 5)})


@with_source
def judge(source, candidates):
    item = obj({"identifies_target_defect": {"type": "boolean"},
                "target_match_reason": TEXT,
                "support": enum(["supported", "contradicted", "insufficient_evidence"]),
                "major": {"type": "boolean"}, "evidence_ids": cites(source), "support_reason": TEXT})
    return obj({"judgments": obj({key: item for key in candidates}),
                "annotation_caveat": TEXT})
