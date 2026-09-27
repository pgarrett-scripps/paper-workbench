"""Select and prepare two fresh-domain manuscripts without reading reviews."""
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from experiments.pra_reliability_trial import prepare as base
from paper_workspace.storage import read, write

ROOT = base.REPO / 'runs/pra-transfer-matched-v1'
PAPERS = {
 'clinical': {'doi':'10.1371/journal.pone.0321635','figures':[1,2,3],
              'basis':'First 2025 research article by publication date from the PLOS title search randomized AND sleep, excluding protocols and computational studies.'},
 'plant': {'doi':'10.1371/journal.pone.0332803','figures':[1,2,3],
           'basis':'First 2025 research article by publication date from the PLOS title search drought AND growth, excluding corrections and computational studies.'}}


def fetch(url, path, limit=25000000):
    path=Path(path)
    if path.exists():
        return
    with urllib.request.urlopen(url, timeout=60) as response:
        raw=response.read(limit+1)
    if len(raw)>limit:
        raise ValueError('Source exceeds bounded download size')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)


def select():
    base.ROOT=ROOT
    prior=base.build_prior_corpus()
    for item in PAPERS.values():
        if any(item['doi']==p['doi'] for p in prior['papers']):
            raise ValueError('Selected DOI already in local corpus')
    write(ROOT/'preselection.json',{'papers':PAPERS,'selection_rule':'Earliest eligible original research per query within calendar year 2025. Source quality and model outputs were not examined to select favorable cases.', 'prior_papers':len(prior['papers'])})
    for key,item in PAPERS.items():
        source=ROOT/'inputs'/key/'sources'
        url='https://journals.plos.org/plosone/article/file?id='+item['doi']
        fetch(url+'&type=manuscript',source/'main.xml')
        fetch(url+'&type=printable',source/'main.pdf')
        base.sanitize_xml(source/'main.xml',source/'import.xml')
        xml=ET.parse(source/'import.xml').getroot()
        supplements=[]
        for e in xml.findall('.//supplementary-material'):
            supplements.append({'id':e.get('id'),'text':base.re.sub(r'\s+',' ',''.join(e.itertext())),
                                'href':e.get('{http://www.w3.org/1999/xlink}href')})
        print(json.dumps({'paper':key,'supplements':supplements}),flush=True)


if __name__=='__main__':
    select()


def ready():
    base.ROOT=ROOT
    base.PAPERS={k:{**v,'records':[('crossref',v['doi'])], 'excluded_attachments':[], 'derived_assets':[]} for k,v in PAPERS.items()}
    for suffix,label in [('s001','study-protocol'),('s002','consort-checklist')]:
        doi=PAPERS['clinical']['doi']+'.'+suffix
        if suffix=='s002' and (ROOT/'inputs/clinical/sources/consort-checklist-original.doc').exists():
            continue
        fetch('https://journals.plos.org/plosone/article/file?id='+doi+'&type=supplementary',
              ROOT/'inputs/clinical/sources/supplements'/(label+'.docx'), limit=10000000)
    base.PAPERS['clinical']['derived_assets']=[{'source':'consort-checklist-original.doc','derived':'supplements/consort-checklist-original.docx','method':'LibreOffice conversion from publisher legacy Word file mislabeled DOCX'}]
    base.PAPERS['plant']['excluded_attachments']=[{'id':'pone.0332803.s001','description':'Raw XLSX data omitted. Full analysis reruns are outside scope.'}]
    for key in PAPERS:
        value=base.prepare_paper(key)
        packet=base.prepare_packet(key)
        print(json.dumps({'paper':key,'title':value['title'],'words':value['word_counts']['total_words'],'images':len(value['images']),'packet':packet}),flush=True)
