"""Prepare four development papers for a three-condition resource ablation."""
import json
import urllib.request
import xml.etree.ElementTree as ET
import shutil
import subprocess
from experiments.pra_reliability_trial import prepare as base
from paper_workspace.storage import read, write

ROOT=base.REPO/'runs/pra-four-condition-v1'
PAPERS={
 'molecular':{'doi':'10.1371/journal.pone.0311159','figures':[1,2,3], 'basis':'Earliest eligible 2025 original experimental study from the PLOS title query knockdown OR overexpression.'},
 'ecology':{'doi':'10.1371/journal.pone.0307357','figures':[1,2,3], 'basis':'Earliest eligible 2025 empirical study from the PLOS title query pollination OR predation, excluding a mathematical predator-prey model and a correction.'},
 'behavior':{'doi':'10.1371/journal.pone.0305998','figures':[1,2,3], 'basis':'Earliest clearly manipulated behavioral study in the inspected 2025 attention OR learning title results, excluding computational, qualitative and observational cohort studies.'},
 'public_health':{'doi':'10.1371/journal.pone.0319093','figures':[1,2,3], 'basis':'Earliest eligible 2025 original cohort study from the PLOS title query cohort AND activity.'}}


def fetch(url,path,limit=25000000):
    if path.exists():return
    with urllib.request.urlopen(url,timeout=60) as response:raw=response.read(limit+1)
    if len(raw)>limit:raise ValueError('Source file exceeds limit')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(raw)


def select():
    base.ROOT=ROOT
    prior=base.build_prior_corpus()
    prior['coverage']['excluded_paths']=[str(ROOT.relative_to(base.REPO))+'/**']
    write(ROOT/'prior-corpus.json',prior)
    for item in PAPERS.values():
        if any(item['doi'] in [p['doi'],*p.get('alternate_dois',[])] for p in prior['papers']):
            raise ValueError('Paper already in development corpus')
    write(ROOT/'preselection.json',{'papers':PAPERS,'status':'Development pilot selected before review generation, not part of a frozen confirmatory 24-paper sample.','exclusions':['Mathematical and computational studies','Corrections and protocols','Prior local evaluation papers','Uncontrolled observational work for the behavioral-experiment slot']})
    for key,item in PAPERS.items():
        source=ROOT/'inputs'/key/'sources'
        url='https://journals.plos.org/plosone/article/file?id='+item['doi']
        fetch(url+'&type=manuscript',source/'main.xml')
        fetch(url+'&type=printable',source/'main.pdf')
        base.sanitize_xml(source/'main.xml',source/'import.xml')
        xml=ET.parse(source/'import.xml').getroot()
        supplements=[{'id':e.get('id'),'text':base.re.sub(r'\s+',' ',''.join(e.itertext())),
                      'href':e.get('{http://www.w3.org/1999/xlink}href')} for e in xml.findall('.//supplementary-material')]
        print(json.dumps({'paper':key,'supplements':supplements}),flush=True)


def supplements():
    for key,item in PAPERS.items():
        count={'molecular':1,'ecology':9,'behavior':1,'public_health':11}[key]
        for number in range(1,count+1):
            extension='xlsx' if key in ('molecular','behavior') or (key=='ecology' and number>=3) else 'png' if key=='ecology' else 'pdf'
            path=ROOT/'inputs'/key/'attachments'/f's{number:03d}.{extension}'
            fetch('https://journals.plos.org/plosone/article/file?id='+item['doi']+f'.s{number:03d}&type=supplementary',path,10000000)
            print(key,path.name,path.stat().st_size,flush=True)


def convert_supplements():
    import openpyxl
    for key,item in PAPERS.items():
        parent=ROOT/'inputs'/key
        dest=parent/'sources/supplements'
        dest.mkdir(parents=True,exist_ok=True)
        item.update(records=[],excluded_attachments=[],derived_assets=[])
        if key=='molecular':
            item['excluded_attachments']=[{'id':'s001','description':'Raw per-assay measurements, inspected for file structure and excluded from review input. No reanalysis.'}]
            continue
        for path in sorted((parent/'attachments').glob('*')):
            if path.suffix=='.xlsx':
                book=openpyxl.load_workbook(path,data_only=True)
                formulas=openpyxl.load_workbook(path,data_only=False)
                lines=['Source '+path.name+'. Nonempty original cells with coordinates. Blank cells remain blank, not zero. Merged ranges are listed explicitly.']
                for sheet in book:
                    if key=='behavior' and sheet.title!='Variable List':
                        item['excluded_attachments'].append({'id':path.name+':'+sheet.title,'description':'Raw participant measurements excluded from review input. Variable dictionary retained.'})
                        continue
                    lines += ['', 'Worksheet: '+sheet.title, 'Merged ranges: '+str(list(sheet.merged_cells.ranges))]
                    for row in sheet:
                        values=[]
                        for cell in row:
                            formula=formulas[sheet.title][cell.coordinate]
                            if formula.data_type=='f' and cell.value is None:
                                raise ValueError('Formula lacks cached source value')
                            if cell.value is not None:
                                values.append(cell.coordinate+'='+str(cell.value))
                        if values:lines+=['',' | '.join(values)]
                derived=dest/(path.stem+'-cells.docx')
                textpath=parent/'attachments'/(path.stem+'-cells.txt')
                textpath.write_text('\n'.join(lines))
                subprocess.run(['pandoc',str(textpath),'-o',str(derived)],check=True)
                item['derived_assets'].append({'source':'../attachments/'+path.name,'derived':'supplements/'+derived.name,'method':'Nonempty cached cells and merged ranges exported with original sheet names and coordinates. No recalculation.'})
            elif path.suffix=='.pdf':
                shutil.copy2(path,dest/path.name)
                item['derived_assets'].append({'source':'supplements/'+path.name,'derived':'supplements/'+path.stem+'-text.docx','method':'pdftotext layout extraction followed by Pandoc DOCX conversion'})
                if int(path.stem[1:])>=9:
                    # Preserve each supplemental figure page as a tool-visible image.
                    from PIL import Image
                    subprocess.run(['pdftoppm','-scale-to','1800','-png',str(path),str(parent/'attachments'/path.stem)],check=True,capture_output=True)
                    for png in sorted((parent/'attachments').glob(path.stem+'-*.png')):
                        Image.open(png).save(dest/(png.stem+'.tiff'))
            elif path.suffix=='.png':
                from PIL import Image
                Image.open(path).save(dest/(path.stem+'.tiff'))
        write(parent/'supplement-preparation.json',item)
    write(ROOT/'prepared-papers.json',PAPERS)


def ready():
    base.ROOT=ROOT
    base.PAPERS=read(ROOT/'prepared-papers.json')
    for key in PAPERS:
        value=base.prepare_paper(key)
        print(json.dumps({'paper':key,'words':value['word_counts']['total_words'],'images':len(value['images'])}),flush=True)


if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='supplements':supplements()
    elif len(sys.argv)>1 and sys.argv[1]=='convert':convert_supplements()
    elif len(sys.argv)>1 and sys.argv[1]=='ready':ready()
    else:select()
