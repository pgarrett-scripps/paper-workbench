"""Prepare a fixed public manuscript without its embedded review history."""
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

from paper_workspace.storage import digest,write

ROOT=Path(__file__).resolve().parents[2]/'runs/pra-fresh-comparison-v1'


def main():
    from pypdf import PdfReader,PdfWriter
    import openpyxl
    source=ROOT/'sources'
    tree=ET.parse(source/'original.xml')
    root=tree.getroot()
    removed=len(root.findall('sub-article'))
    for child in list(root.findall('sub-article')):
        root.remove(child)
    body=root.find('body')
    appendix=ET.SubElement(body,'sec',{'id':'pra-reported-tables'})
    ET.SubElement(appendix,'title').text='Supplied reported-results tables'
    table_audit=[]
    for path in sorted((source/'supplements').glob('*.xlsx')):
        workbook=openpyxl.load_workbook(path,read_only=True,data_only=True,keep_links=False)
        for sheet in workbook:
            if sheet.max_row>2000 or sheet.max_column>100:raise ValueError('Reported table exceeds preparation cap')
            rows=list(sheet.values)
            wrap=ET.SubElement(appendix,'table-wrap',{'id':path.stem+'-'+str(len(table_audit)+1)})
            ET.SubElement(wrap,'label').text=path.stem.replace('_',' ')+' / '+sheet.title
            caption=ET.SubElement(wrap,'caption')
            ET.SubElement(caption,'p').text='Cached reported values from supplied spreadsheet. Empty cells remain empty. Formulas and merged-cell appearance are not reconstructed.'
            table=ET.SubElement(wrap,'table')
            for row in rows:
                tr=ET.SubElement(table,'tr')
                for value in row:ET.SubElement(tr,'td').text='' if value is None else str(value)
            table_audit.append({'file':path.name,'sheet':sheet.title,'rows':len(rows),'columns':sheet.max_column})
        workbook.close()
    writer=PdfWriter()
    page_registry=[]
    paths=[source/'original.pdf']+sorted((source/'supplements').glob('*.pdf'))
    for path in paths:
        reader=PdfReader(path)
        for index,page in enumerate(reader.pages,1):
            writer.add_page(page)
            page_registry.append({'packet_page':len(page_registry)+1,'source_file':str(path.relative_to(source)), 'source_page':index})
    packet=source/'manuscript-packet.pdf'
    with packet.open('wb') as stream:writer.write(stream)
    clean=source/'manuscript-only.xml'
    tree.write(clean,encoding='utf-8',xml_declaration=True)
    supplement_text=source/'import-supplements'
    supplement_text.mkdir(exist_ok=True)
    shutil.copy2(source/'supplements/S1_Text.docx',supplement_text/'S1_Text.docx')
    write(ROOT/'source-selection.json',{'doi':'10.1371/journal.pbio.3002218','version':'Published version, 2023-08-21',
        'selection':'Unused local manuscript selected before review generation. Short experimental Drosophila nutrition and genetics study with three main figures.',
        'source_url':'https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002218',
        'review_subarticles_removed':removed,'tables':table_audit,'page_registry':page_registry,
        'excluded':'S11 through S26 source-data spreadsheets and author analysis code. No analysis rerun or human-review matching.',
        'limitations':['Published rather than original submission version. Prior model training exposure cannot be excluded.',
            'Spreadsheet values are a text projection. Interpretation of merged headings needs the original source.',
            'Human reviews are not supplied to any review or evaluation call.'],
        'sources':{str(p.relative_to(source)):digest(p.read_bytes()) for p in source.rglob('*') if p.is_file()}})
    print('Prepared',len(page_registry),'pages and',len(table_audit),'table sheets')


if __name__=='__main__':main()
