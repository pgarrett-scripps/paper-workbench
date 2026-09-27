"""A fixed two-call development check of revised debate on one saved paper."""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from paper_workspace.annotations import verify_workspace, save_review, export_draft
from paper_workspace.debate_revision import issue_ledger, revision_prompt, DEBATE_REVISION, validate_revision, revision_package
from paper_workspace.evidence_tasks import complete_inspected_images
from paper_workspace.model_runtime import model_call, require_subscription, jsonl, source_manifest
from paper_workspace.storage import read, write, digest
from experiments.pra_debate_revision.evaluation import EVALUATION, INSTRUCTIONS, audit

ROOT = REPO/'runs/pra-debate-revision-v2'
OLD = REPO/'runs/pra-evidence-workflow-v1'
WORK = ROOT/'workspace'
PROTOCOL = {'provider':'codex','model':'gpt-5.6-sol','effort':'medium','held_out_runs_authorized':False,
            'max_calls_per_condition':2,'observed_token_stop':180000,'call_timeout_seconds':600,
            'max_source_images':10,'image_budget_version':'evidence-v1','stage':'debate-revision-v2',
            'paper':'paper-2','debate_operations':2,'literature_search':False}


def frozen(path, value):
    if path.exists():
        if read(path) != value:
            raise ValueError('Frozen artifact changed: '+str(path))
    else:
        write(path, value)


def prepare():
    old_work = OLD/'workspaces/paper-2'
    verify_workspace(old_work)
    for name, sha in read(OLD/'generation-lock.json').items():
        if digest((OLD/name).read_bytes()) != sha:
            raise ValueError('Historical generation changed')
    manifest = read(old_work/'manifest.json')
    for name in list(manifest['files']) + ['manifest.json']:
        source, target = old_work/name, WORK/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if source.read_bytes() != target.read_bytes():
                raise ValueError('Copied source changed')
        else:
            shutil.copy2(source, target)
    paper = verify_workspace(WORK)
    frozen(ROOT/'protocol.json', PROTOCOL)
    frozen(ROOT/'manifest.json', {
        'source_manifest':manifest, 'base_study_sha256':digest((OLD/'study-manifest.json').read_bytes()),
        'generation_lock_sha256':digest((OLD/'generation-lock.json').read_bytes()),
        'source_code':source_manifest(REPO/'paper_workspace'),
        'experiment_code':source_manifest(Path(__file__).parent),
        'protocol_document_sha256':digest((REPO/'docs/pra-debate-revision-protocol.md').read_bytes()),
        'selection':'Development paper chosen because prior debate both promoted and discarded substantive concerns. This is not held out.'})
    for folder, source in [('paper_workspace',REPO/'paper_workspace'),('experiment',Path(__file__).parent)]:
        for name in source_manifest(source):
            target = ROOT/'frozen-source'/folder/name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(source/name,target)
            elif target.read_bytes() != (source/name).read_bytes():
                raise ValueError('Frozen code copy changed')
    candidates = read(OLD/'responses/paper-2/candidates.json')
    ledger = issue_ledger(candidates)
    frozen(ROOT/'inputs/candidates.json', candidates)
    frozen(ROOT/'inputs/ledger.json', ledger)
    for condition in ('ordinary','debate'):
        frozen(ROOT/'inputs'/f'{condition}.json', read(OLD/'responses/paper-2'/f'{condition}.json'))
    images = []
    for image in read(OLD/'evidence/paper-2/prepared-evidence.json')['images']:
        source = Path(image['path'])
        if digest(source.read_bytes()) != image['sha256']:
            raise ValueError('Source page image changed')
        target = ROOT/'images'/source.name
        target.parent.mkdir(exist_ok=True)
        if not target.exists():shutil.copy2(source,target)
        if digest(target.read_bytes()) != image['sha256']:raise ValueError('Copied page image changed')
        if image['sha256'] not in {i['sha256'] for i in images}:
            images.append({'path':str(target.resolve()),'label':image['label'],'sha256':image['sha256']})
    frozen(ROOT/'inputs/images.json', images)
    prompt = revision_prompt(paper,(WORK/'manuscript.md').read_text(),ledger)
    prompt += '\nATTACHED ORIGINAL PAGES:\n'+json.dumps(images)
    frozen(ROOT/'inputs/debate-request.json',{'prompt':prompt,'schema':DEBATE_REVISION})
    return paper, ledger, images, prompt


def execute():
    paper, ledger, images, prompt = prepare()
    billing = read(ROOT/'billing_confirmation.json')
    if not billing.get('no_paid_credits_verified') or not 0 <= time.time()-billing.get('checked_at',0) < 86400:
        raise ValueError('Fresh subscription credit verification required')
    require_subscription(ROOT)
    write(ROOT/'execution/workspace/tool-config.json',{'paper':str(WORK),'output':str(ROOT/'investigation'),
          'cache':str(ROOT/'cache'),'allow_literature':False,'tool_limit':2,'tool_profile':'debate-v2'})
    write(ROOT/'progress.json',{'status':'running','stage':'revised-debate'})
    value = model_call(PROTOCOL,ROOT/'execution',prompt,DEBATE_REVISION,tools=True,label='revised-debate',
                       images=[Path(i['path']) for i in images])
    frozen(ROOT/'raw/revised-debate.json',value)
    check = validate_revision(value,ledger,paper)
    frozen(ROOT/'structural-audit.json',check)
    package = revision_package(value,ledger,check)
    review = save_review(WORK,package,'revised-debate')
    frozen(ROOT/'review-package.json',export_draft(paper,review,{'paper_id':paper['id'],'items':{}}))
    frozen(ROOT/'generation-lock.json',{'raw_sha256':digest((ROOT/'raw/revised-debate.json').read_bytes()),
                                     'package_sha256':digest((ROOT/'review-package.json').read_bytes())})
    # A common complete image union for all three evaluation conditions.
    registry = {}
    for image in read(OLD/'responses/paper-2/images.json') + images:
        if digest(Path(image['path']).read_bytes()) != image['sha256']:raise ValueError('Evaluator image changed')
        registry[image['sha256']] = {k:image[k] for k in ('path','label','sha256')}
    for path,label in complete_inspected_images(paper,WORK,ROOT/'investigation'):
        registry[digest(path.read_bytes())] = {'path':str(path),'label':label,'sha256':digest(path.read_bytes())}
    shared = [{'id':f'image-{n}',**image} for n,image in enumerate(sorted(registry.values(),key=lambda r:r['label']),1)]
    if len(shared)>10:raise ValueError('Shared image union exceeds the fixed cap')
    frozen(ROOT/'evaluation/images.json',shared)
    conditions = {'ordinary':read(ROOT/'inputs/ordinary.json'),'old_debate':read(ROOT/'inputs/debate.json'),
                  'revised_debate':review}
    mapping = {'A':'old_debate','B':'revised_debate','C':'ordinary'}
    anonymous = {label:[{'finding_id':f'{label}{n}',**{k:f.get(k) for k in
        ('title','block_id','quote','kind','severity','comment','replacement','evidence_blocks','counterevidence')}}
        for n,f in enumerate(conditions[condition]['findings'],1)] for label,condition in mapping.items()}
    frozen(ROOT/'evaluation/label-map.json',mapping)
    evaluation_prompt = INSTRUCTIONS+'\nREVIEWS:\n'+json.dumps(anonymous,ensure_ascii=False)
    evaluation_prompt += '\nIMAGES:\n'+json.dumps([{k:r[k] for k in ('id','label','sha256')} for r in shared])
    evaluation_prompt += '\nTITLE:\n'+paper['title']+'\nMANUSCRIPT:\n'+(WORK/'manuscript.md').read_text()
    frozen(ROOT/'evaluation/request.json',{'prompt':evaluation_prompt,'schema':EVALUATION})
    write(ROOT/'progress.json',{'status':'running','stage':'quality-evaluation'})
    grades = model_call(PROTOCOL,ROOT/'execution',evaluation_prompt,EVALUATION,tools=False,
                        label='quality-evaluation',images=[Path(i['path']) for i in shared])
    frozen(ROOT/'raw/quality-evaluation.json',grades)
    grading_audit = audit(grades,anonymous,paper,shared)
    frozen(ROOT/'evaluation/audit.json',grading_audit)
    valid = set(grading_audit['valid_rating_ids'])
    metrics = []
    for condition in grades['conditions']:
        ratings = [r for r in condition['ratings'] if r['finding_id'] in valid]
        metrics.append({'condition':mapping[condition['label']], 'findings':len(condition['ratings']),
            'unscored':len(condition['ratings'])-len(ratings),
            'assessments':{s:sum(r['assessment']==s for r in ratings) for s in
              ('justified_concern','justified_clarification','unsupported_allegation','unverifiable')},
            'consequential_supported':sum(r['assessment'] in ('justified_concern','justified_clarification') and
                                         r['materiality'] in ('major','moderate') for r in ratings),
            'excessive_requests':sum(r['resolution_proportionality']=='excessive' for r in ratings)})
    usage = jsonl(ROOT/'execution/usage.jsonl')
    result = {'status':'complete_with_grading_flags' if grading_audit['invalid_ratings'] else 'complete',
              'metrics':metrics,'preference':mapping.get(grades['preferred_label'],grades['preferred_label']),
              'preference_reason':grades['preference_reason'], 'calls':len(usage),
              'observed_tokens':sum(r['observed_tokens'] for r in usage),
              'source_operations':len(jsonl(ROOT/'investigation/tool-log.jsonl')),
              'limitations':['One reused development paper selected after inspecting earlier failures',
                 'One automated same-family evaluator, no expert grading',
                 'Revision changes prompt, source context, tool interface, and accounting together',
                 'Saved comparators were not regenerated under matched compute or context',
                 'No human-review overlap scores were recalculated']}
    frozen(ROOT/'results.json',result)
    write(ROOT/'progress.json',result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','run'])
    args=parser.parse_args()
    try:
        if args.stage=='prepare':
            prepare()
            print('One-paper development inputs frozen. No inference launched.')
        else:execute()
    except Exception as exc:
        write(ROOT/'progress.json',{'status':'blocked','error':str(exc)})
        raise
