import json,sys,subprocess,time,tempfile,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,'/home/ty/Repos/insilico')
from peerreviewagents.workspace import digest, save_review, write_json
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    text='A claim with 12 samples.'
    paper={'id':'qa','title':'QA','source_sha256':'qa','blocks':[{'id':'b1','text':text,'sha256':digest(text)}],'statistics':{'pdf_pages':1}}
    write_json(root/'paper.json',paper)
    write_json(root/'manifest.json',{'files':{'paper.json':digest((root/'paper.json').read_bytes())}})
    save_review(root,{'findings':[{'kind':'edit','block_id':'b1','quote':'12 samples','replacement':'12 donors','evidence_blocks':['b1']} ]},'qa')
    process=subprocess.Popen([sys.executable,'-m','paper_workspace','serve',tmp,'--port','38745'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    def req(path,data=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        request=urllib.request.Request('http://127.0.0.1:38745'+path,data=json.dumps(data).encode() if data else None,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=5) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)
    try:
        for attempt in range(40):
            try:
                code,value=req('/api/reviews')
                break
            except urllib.error.URLError:time.sleep(.1)
        assert value==['qa']
        decision={'review_id':'qa','annotation_id':'qa-1','status':'accepted','revision':0}
        assert req('/api/decisions',decision,'http://bad.example')[0]==403
        assert req('/api/decisions',decision)[0]==200
        assert req('/api/decisions',decision)[0]==409
        code,value=req('/api/export?review=qa')
        assert value['proposed_blocks'][0]['text']=='A claim with 12 donors.'
        assert value['original_blocks'][0]['text']==text
        assert value['findings'][0]['issue_status']=='open'
        assert json.load(open(root/'decisions/qa.json'))['revision']==1
        decision.update(status='proposed',revision=1)
        assert req('/api/decisions',decision)[0]==200
        assert req('/api/export?review=qa')[1]['proposed_blocks'][0]['text']==text
        print('HTTP QA passed: durable save, undo, stale revision, cross-origin rejection, immutable original, open scientific issue')
    finally:
        process.terminate()
        process.wait(timeout=10)
