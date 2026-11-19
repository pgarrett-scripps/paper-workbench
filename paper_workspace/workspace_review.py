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

A manuscript workspace made with ``import-scaffold`` can stand there too.
Its current draft is reviewed: the draft's built ``artifacts/paper.pdf``,
refused when the draft has none, with the draft's own copy of the project,
``scaffold/``, as the code under the same rules. ``ledger_target`` names
the workspace and the run folder, so the command adds the review's problems
to that draft's issue ledger when the review finishes. ``import_project``
keeps the project's built PDF as the original draft's when it imports one.
"""

import contextlib
import io
import json
import shutil
from pathlib import Path

from peerreviewagents import review_arms, review_parser
from peerreviewagents.workspace import digest

from .revisions import head, snapshot
from .scaffold_import import SPANS, import_scaffold

__all__ = ['BUILD_RECORD', 'WorkspaceRefused', 'built_pdf', 'code_arms', 'code_root', 'engine_argv',
           'import_project', 'ledger_target', 'manuscript_draft', 'parser']

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
                         'The manuscript is a PDF, a Paper Scaffold workspace folder, or a manuscript '
                         'workspace made with import-scaffold.')
    built.epilog = ('A workspace folder, such as ".", is reviewed from its built paper.pdf, which must '
                    'match the source as `just paper` last recorded it. The code reviewer is handed the '
                    'repository the workspace is in, or the workspace itself outside git. A run folder '
                    'inside it is fine, as the engine leaves run folders out of the code it copies. '
                    '--code FOLDER_OR_URL names other code, and --no-code reviews the paper alone. Only '
                    f'the {listed(code_arms(), "and")} arms review code, so on any other arm a workspace is '
                    'reviewed without it. A manuscript workspace made with import-scaffold is reviewed from '
                    'its current draft\'s built PDF, with that draft\'s copy of the project as the code, and '
                    'the problems of a finished review are added to that draft\'s issue ledger.')
    # The engine's parser offers no public way to change a positional's help, so the action is found by name.
    for action in built._actions:
        if action.dest == 'workspace':
            action.help = ('the manuscript PDF, a Paper Scaffold workspace folder, or a manuscript workspace '
                           'made with import-scaffold')
    built.add_argument(NO_CODE, action='store_true',
                       help='review a workspace with no code, where the repository would be handed over')
    return built


def engine_argv(argv):
    """The engine's arguments for what the author typed, and a line saying what a workspace review reads.

    A PDF review passes through as typed, without ``--no-code``. A workspace
    review has the folder replaced by its built PDF and, unless the author
    gave ``--code`` or ``--no-code``, ``--code`` with the repository added
    when the arm reviews code. A manuscript workspace is reviewed from its
    current draft's built PDF, with the draft's ``scaffold/`` as the code.
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
    draft = manuscript_draft(workspace)
    if draft:
        name, folder = draft
        pdf = folder / 'artifacts' / 'paper.pdf'
        if not pdf.is_file():
            raise WorkspaceRefused(f'Draft {name} of {workspace.resolve()} has no built PDF, so it cannot be '
                                   'reviewed. Review a draft that was built.')
        code, reading = folder / 'scaffold', f'draft {name}, {pdf},'
    elif (workspace / 'paper.typ').is_file():
        pdf = built_pdf(workspace)
        code, reading = code_root(workspace), str(pdf)
    else:
        raise WorkspaceRefused(f'{workspace.resolve()} is a folder and not a Paper Scaffold workspace: it has '
                               'no paper.typ, and it is no manuscript workspace made with import-scaffold. '
                               'Give the manuscript PDF or a workspace folder.')
    kept = with_manuscript(command, kept, args, str(pdf))
    if args.code or args.no_code:
        given = f'the code in {args.code}' if args.code else 'no code'
        return kept, f'paper-workbench review: reviewing {reading} with {given}.'
    if not review_arms()[args.arm]['code']:
        return kept, (f'paper-workbench review: reviewing {reading} with no code, because the {args.arm} arm '
                      f'reviews no code. The {listed(code_arms(), "and")} arms would review it with the code '
                      f'in {code}.')
    return [*kept, '--code', str(code)], (f'paper-workbench review: reviewing {reading} with the code in {code}. '
                                          'Give --no-code to review the paper alone.')


def manuscript_draft(workspace):
    """The current draft of a manuscript workspace made with ``import-scaffold``, as its id and folder.

    ``None`` for any other folder. A draft kept under the workspace's
    ``revisions/`` is refused, as a review is always of the current draft
    and its problems go into that draft's ledger.
    """
    root = Path(workspace).expanduser().resolve()
    if not ((root / SPANS).is_file() and (root / 'scaffold').is_dir()):
        return None
    if root.parent.name == 'revisions' and (root.parent.parent / SPANS).is_file():
        raise WorkspaceRefused(f'{root} is a draft kept inside the manuscript workspace {root.parent.parent}. '
                               'Give the workspace, and its current draft is reviewed.')
    try:
        name = head(root)['revision_id']
        folder, _ = snapshot(root, name)
    except (ValueError, OSError) as exc:
        raise WorkspaceRefused(f'{root} is not a manuscript workspace with a current draft: {exc}') from exc
    return name, folder


def ledger_target(argv):
    """The manuscript workspace and the run folder of a review whose problems go into its ledger, or ``None``.

    *argv* is what the author typed, already accepted by :func:`engine_argv`.
    Only a review of a manuscript workspace has a ledger to add to.
    """
    args = parser().parse_args(list(argv))
    if not (Path(args.workspace).is_dir() and manuscript_draft(args.workspace)):
        return None
    return Path(args.workspace).expanduser().resolve(), Path(args.output).expanduser().resolve()


def import_project(source, output, title=None):
    """Import a Paper Scaffold project as a manuscript workspace, keeping its built PDF as the original draft's.

    The PDF is the project's ``paper.pdf`` while :func:`built_pdf` says it
    matches the source. It is kept as ``artifacts/paper.pdf``, where a built
    draft keeps its own, so the original draft can be reviewed and checked.
    Returns the manifest, and a line saying why the original has no PDF or
    ``None``.
    """
    try:
        pdf = built_pdf(source)
    except WorkspaceRefused as exc:
        reason = str(exc).removesuffix(' ' + BUILD)
        return import_scaffold(source, output, title), (
            f'{reason} The original draft has no PDF, so it cannot be reviewed or checked. Build the project with '
            '`just paper` and import it again.')

    def carry(folder, _):
        (folder / 'artifacts').mkdir()
        shutil.copyfile(pdf, folder / 'artifacts' / 'paper.pdf')

    return import_scaffold(source, output, title, prepare=carry), None


def imported_line(manifest, output, note):
    """One line saying what :func:`import_project` wrote: the paper, where, its size, and whether it kept the PDF.

    *note* is the line :func:`import_project` returned, ``None`` when the
    original draft kept the project's built PDF.
    """
    stats = manifest['statistics']
    pdf = 'no PDF' if note else "its built PDF as the original draft's"
    return (f'imported "{manifest["title"]}" as paper {manifest["paper_id"]} into '
            f'{Path(output).expanduser().resolve()}: {stats["pieces"]} pieces, {stats["total_words"]:,} words and '
            f'{stats["reference_entries"]} references, with {pdf}.')


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
