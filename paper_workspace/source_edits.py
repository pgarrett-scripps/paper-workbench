"""Exact source codecs and protected citation markers for prose revisions."""
import json
import re


NATIVE_CITATION = re.compile(r'(?<![\w\\:./-])@[A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)*')
NUMERIC_CITATION = re.compile(r'\[\s*\d+(?:\s*[,\u2013\u2014-]\s*\d+)*\s*\]')
TEXT_LITERAL = re.compile(r'#text\(("(?:[^"\\]|\\.)*")\)', re.S)


def citation_markers(text):
    matches = list(NATIVE_CITATION.finditer(text)) + list(NUMERIC_CITATION.finditer(text))
    return [match.group() for match in sorted(matches, key=lambda match: match.start())]


def decode_span(source, span):
    value = source[span['start']:span['end']]
    encoding = span.get('encoding')
    if encoding is None:
        return value
    if encoding != 'json-string':
        raise ValueError('Unknown manuscript source encoding')
    value = json.loads(value)
    if not isinstance(value, str):
        raise ValueError('Manuscript source span is not a string')
    return value


def encode_span(text, span):
    if span.get('encoding') == 'json-string':
        return json.dumps(text, ensure_ascii=False)
    if span.get('encoding') is not None:
        raise ValueError('Unknown manuscript source encoding')
    return text


def literal_value(expression):
    match = TEXT_LITERAL.fullmatch(expression)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return (value, match.start(1), match.end(1)) if isinstance(value, str) else None
