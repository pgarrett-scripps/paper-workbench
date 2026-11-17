"""Review a Paper Scaffold workspace: its built PDF, with its code.

``paper-workbench review`` takes what the engine's ``peerreview review`` takes,
a manuscript PDF and a run folder. A folder can never be a PDF, so a folder
where the PDF goes is a workspace, and ``paper-workbench review . RUN`` from
inside one reviews it. That keeps one command with one meaning per argument.

A workspace review hands the engine two things the author did not have to name.

- The PDF is the workspace's built ``paper.pdf``, and only while it matches
  the source. Paper Scaffold records each build in ``.build-state/paper.pdf.json``:
  the hash of every file the build read and the hash of the PDF it wrote.
  The PDF is refused when it is missing, when that record is missing or
  unreadable, when a recorded file has changed since, or when the PDF is not
  the file the build wrote. A file added since the build is caught through the
  recorded file that has to name it before the PDF can use it.
- The code is the repository the workspace is in: the nearest folder at or
  above it that holds ``.git``, or the workspace itself outside git. The engine
  copies only its text source and lists what it left out, data, results,
  figures, dependencies and files that may hold secrets among it. ``--code``
  names other code and ``--no-code`` reviews the paper alone. Only an arm
  whose row in the engine's ``review_arms`` says it reviews code is handed
  it. On any other arm the paper is reviewed alone and the line says so,
  because the author never asked for the code. A ``--code`` the author gives
  on such an arm reaches the engine, which refuses it.

A run folder inside that code is fine, because the engine leaves every run
folder out of the code it copies. Nothing in the workspace is executed here,
and a refusal writes nothing.
"""

import contextlib
import io
import json
from pathlib import Path

from peerreviewagents import review_arms, review_parser
from peerreviewagents.workspace import digest

__all__ = ['BUILD_RECORD', 'WorkspaceRefused', 'built_pdf', 'code_arms', 'code_root', 'engine_argv', 'parser']

#: Paper Scaffold's record of the last ``just paper`` build, relative to the workspace.
BUILD_RECORD = Path('.build-state') / 'paper.pdf.json'

#: What the author runs to build the PDF a review reads.
BUILD = 'Build it with `just paper` and run the review again.'

#: The flag that reviews a workspace with no code. The engine has no such flag, so it never reaches it.
NO_CODE = '--no-code'

#: How many changed files a refusal names before it counts the rest.
NAMED = 3


class WorkspaceRefused(ValueError):
    """A workspace this review cannot start from, with the reason in plain words."""


def parser(prog='paper-workbench review'):
    """The engine's review parser, which also takes a workspace folder and ``--no-code``."""
    built = review_parser(prog=prog)
    built.description = ('Review one manuscript with the pra plugin in a headless Claude Code session. '
                         'The manuscript is a PDF, or a Paper Scaffold workspace folder.')
    built.epilog = ('A workspace folder, such as ".", is reviewed from its built paper.pdf, which must '
                    'match the source as `just paper` last recorded it. The code reviewer is handed the '
                    'repository the workspace is in, or the workspace itself outside git. A run folder '
                    'inside it is fine, as the engine leaves run folders out of the code it copies. '
                    '--code FOLDER_OR_URL names other code, and --no-code reviews the paper alone. Only '
                    f'the {listed(code_arms(), "and")} arms review code, so on any other arm a workspace is '
                    'reviewed without it.')
    # The engine's parser offers no public way to change a positional's help, so the action is found by name.
    for action in built._actions:
        if action.dest == 'workspace':
            action.help = 'the manuscript PDF, or a Paper Scaffold workspace folder'
    built.add_argument(NO_CODE, action='store_true',
                       help='review a workspace with no code, where the repository would be handed over')
    return built


def engine_argv(argv):
    """The engine's arguments for what the author typed, and a line saying what a workspace review reads.

    A PDF review passes through as typed, without ``--no-code``. A workspace
    review has the folder replaced by its built PDF and, unless the author
    gave ``--code`` or ``--no-code``, ``--code`` with the repository added
    when the arm reviews code.
    The line is ``None`` for a PDF. Raises :class:`WorkspaceRefused` when the
    folder cannot be reviewed, and exits as argparse does on ``-h`` or a usage
    error.
    """
    argv = list(argv)
    command = parser()
    args = command.parse_args(argv)
    if args.no_code and args.code:
        command.error('give --code or --no-code, not both')
    kept = [token for token in argv if not is_no_code(token)]
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        return kept, None
    if not (workspace / 'paper.typ').is_file():
        raise WorkspaceRefused(f'{workspace.resolve()} is a folder and not a Paper Scaffold workspace: it has '
                               'no paper.typ. Give the manuscript PDF or a workspace folder.')
    pdf = built_pdf(workspace)
    kept = with_manuscript(command, kept, args, str(pdf))
    if args.code or args.no_code:
        given = f'the code in {args.code}' if args.code else 'no code'
        return kept, f'paper-workbench review: reviewing {pdf} with {given}.'
    code = code_root(workspace)
    if not review_arms()[args.arm]['code']:
        return kept, (f'paper-workbench review: reviewing {pdf} with no code, because the {args.arm} arm reviews '
                      f'no code. The {listed(code_arms(), "and")} arms would review it with the code in {code}.')
    return [*kept, '--code', str(code)], (f'paper-workbench review: reviewing {pdf} with the code in {code}. '
                                          'Give --no-code to review the paper alone.')


def code_arms():
    """The arms that review code, in name order, as the engine's ``review_arms`` says."""
    return [name for name, arm in review_arms().items() if arm['code']]


def listed(names, word):
    """*names* in prose, the last two joined by *word*."""
    return f' {word} '.join([', '.join(names[:-1]), names[-1]] if len(names) > 1 else names)


def is_no_code(token):
    """Whether *token* is ``--no-code`` or an abbreviation argparse reads as it."""
    return token.startswith('--n') and NO_CODE.startswith(token)


def with_manuscript(command, argv, args, pdf):
    """*argv* with the workspace argument replaced by *pdf*, found by parsing rather than by position.

    The folder can be spelled the same as an option's value or the run
    folder, so each token spelled like it is tried, and the one kept is the
    one whose replacement parses to the same arguments with only the
    manuscript changed.
    """
    wanted = dict(vars(args), workspace=pdf, no_code=False)
    for index, token in enumerate(argv):
        if token != args.workspace:
            continue
        candidate = [*argv[:index], pdf, *argv[index + 1:]]
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                parsed = command.parse_args(candidate)
        except SystemExit:
            continue
        if dict(vars(parsed), no_code=False) == wanted:
            return candidate
    raise WorkspaceRefused(f'Could not tell which argument names the workspace {args.workspace}.')


def code_root(workspace):
    """The repository *workspace* is in, the nearest folder at or above it holding ``.git``.

    ``.git`` is a folder in a clone and a file in a worktree or a submodule,
    and either marks the repository. A workspace in no repository is its own
    code. Nothing is run to find it.
    """
    start = Path(workspace).expanduser().resolve()
    for folder in (start, *start.parents):
        if (folder / '.git').exists():
            return folder
    return start


def built_pdf(workspace):
    """The workspace's ``paper.pdf``, when its last recorded build says it matches the source.

    The check is Paper Scaffold's own: every file the build recorded is hashed
    again, ``stats.json`` with its ``pinned`` entry dropped because pinning
    never changes a value the PDF prints, and the PDF is hashed against the
    one the build wrote. Raises :class:`WorkspaceRefused` naming what is wrong.
    """
    root = Path(workspace).expanduser().resolve()
    pdf = root / 'paper.pdf'
    if not pdf.is_file():
        raise WorkspaceRefused(f'{root} has no built paper.pdf. {BUILD}')
    record = root / BUILD_RECORD
    try:
        state = json.loads(record.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = None
    if not (isinstance(state, dict) and state.get('schema_version') == 1
            and isinstance(state.get('sources'), dict) and isinstance(state.get('output_hash'), str)):
        raise WorkspaceRefused(f'{pdf} has no build record this app can read at {record}, so it cannot '
                               f'tell whether the PDF matches the source. {BUILD}')
    changed = [str(name) for name, recorded in sorted(state['sources'].items(), key=lambda row: str(row[0]))
               if source_digest(root, str(name)) != recorded]
    if changed:
        named = ', '.join(changed[:NAMED])
        rest = f' and {len(changed) - NAMED} more' if len(changed) > NAMED else ''
        raise WorkspaceRefused(f'{pdf} is older than its source: {named}{rest} changed since it was built. {BUILD}')
    if digest(pdf.read_bytes()) != state['output_hash']:
        raise WorkspaceRefused(f'{pdf} is not the file its last build wrote, so it cannot be shown to match '
                               f'the source. {BUILD}')
    return pdf


def source_digest(root, name):
    """The hash Paper Scaffold records for the source *name*, or ``None`` when it is not a file.

    *name* is relative to the workspace, or absolute for a file outside it,
    such as a Typst package. A ``stats.json`` that no longer parses is a
    change, so it gets a value no record holds.
    """
    path = Path(name) if Path(name).is_absolute() else root / name
    if not path.is_file():
        return None
    if name != 'stats.json':
        return digest(path.read_bytes())
    try:
        values = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 'unreadable'
    if not isinstance(values, dict):
        return 'unreadable'
    values.pop('pinned', None)
    return digest(json.dumps(values, sort_keys=True))
