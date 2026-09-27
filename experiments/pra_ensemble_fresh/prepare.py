"""Prepare complete bounded source packets for the fresh two-paper comparison."""
import subprocess
from pathlib import Path

from experiments.pra_reliability_trial import prepare as base
from paper_workspace.storage import read,write


ROOT=Path(__file__).resolve().parents[2]/'runs/pra-ensemble-fresh-v1'


def inputs():
    import openpyxl
    path=ROOT/'inputs/plant/sources/supplements/s003.xlsx'
    book=openpyxl.load_workbook(path,data_only=True)
    formulas=openpyxl.load_workbook(path,data_only=False)
    lines=['Published supplementary statistical summary. Original nonempty cells with coordinates. Blank cells are not zero. No recalculation or raw-data analysis was performed.']
    for sheet in book:
        lines+=['','Worksheet: '+sheet.title,'Merged ranges: '+str(list(sheet.merged_cells.ranges))]
        for row in sheet:
            values=[]
            for cell in row:
                if formulas[sheet.title][cell.coordinate].data_type=='f' and cell.value is None:
                    raise ValueError('Published formula has no cached value')
                if cell.value is not None:values.append(cell.coordinate+'='+str(cell.value))
            if values:lines+=['',' | '.join(values)]
    text=path.with_name('s003-cells.txt')
    text.write_text('\n'.join(lines))
    derived=path.with_name('s003-cells.docx')
    if not derived.exists():subprocess.run(['pandoc',str(text),'-o',str(derived)],check=True)
    preselection=read(ROOT/'preselection.json')
    items={key:{**item,'figures':[1,2,3],'records':[],'derived_assets':[],
        'excluded_attachments':[]} for key,item in preselection['papers'].items()}
    items['clinical']['excluded_attachments']=[
        {'id':'s002','description':'2018 IRB protocol version, superseded version omitted to bound total text. Latest January 2020 protocol included in full.'},
        {'id':'s003','description':'November 2019 IRB protocol version, omitted to bound total text. Latest January 2020 protocol included in full.'},
        {'id':'s005','description':'CONSORT checklist is mentioned in a combined caption but no separate downloadable file was found at its DOI, which returned HTTP 404.'}]
    items['plant']['derived_assets']=[{'source':'supplements/s003.xlsx','derived':'supplements/s003-cells.docx',
        'method':'Original nonempty cached cells and merged ranges, with coordinates. No recalculation.'}]
    base.ROOT=ROOT
    base.PAPERS=items
    records={}
    for key in items:
        parent=ROOT/'inputs'/key
        if not (parent/'workspace/paper.json').exists():
            subprocess.run([str(base.REPO/'.venv/bin/python'),'-m','paper_workspace','import',
                str(parent/'sources/main.pdf'),str(parent/'workspace'),'--xml',str(parent/'sources/import.xml'),
                '--source-url','https://journals.plos.org/plosone/article?id='+items[key]['doi'],
                '--supplements',str(parent/'sources/supplements')],check=True,capture_output=True)
        value=base.prepare_paper(key)
        if value['word_counts']['total_words']>35000:raise ValueError('Source packet exceeds 35,000 words')
        records[key]=value
        print(key,value['word_counts']['total_words'],len(value['images']),flush=True)
    write(ROOT/'prepared-papers.json',records)


if __name__=='__main__':inputs()
