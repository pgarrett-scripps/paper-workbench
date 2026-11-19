"""Write ``paper.json``, the read manuscript fixture, through the engine's own Read stage with no model.

    python tests/fixtures/reader/generate.py tests/fixtures/reader

``tests/reader_fixture.py`` holds the PDF, the pieces the converter left and the script the reader
follows. README.md here says what the fixture holds.
"""
import json
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parent))

from reader_fixture import build  # noqa: E402


def main(out):
    (Path(out) / 'paper.json').write_text(json.dumps(build(), indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main(sys.argv[1])
