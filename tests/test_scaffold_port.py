"""A port preserves scientific text while exposing only safe source edits."""
from pathlib import Path
import tempfile
import unittest

from peerreviewagents.engine.annotations import verify_workspace
from peerreviewagents.engine.storage import digest, write

from paper_workspace.scaffold_port import port_workspace


class ScaffoldPort(unittest.TestCase):
    def test_literal_markup_stays_readable_and_encoded(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'original'
            source.mkdir()
            texts=[('a','Abstract','paragraph','An association may exist.'),
                   ('b','Results','paragraph','There were 12 samples.'),
                   ('c','Results','paragraph','A citation [1] and #include "bad.typ" are literal text.'),
                   ('d','References','reference','1 Reference text'),
                   ('e','Supplement S1','table','Group\tCount\nControl\t12')]
            blocks=[{'id':i,'section':s,'kind':k,'text':t,'sha256':digest(t),'page':1,
                     'citations':['ref1'] if i=='c' else [],
                     'document':'S1.docx' if i=='e' else 'main',
                     'table':[['Group','Count'],['Control','12']] if i=='e' else None} for i,s,k,t in texts]
            paper={'id':'original','title':'Real source test','source_sha256':'source',
                   'blocks':blocks,'references':[{'id':'ref1','raw':'Reference text'}],
                   'statistics':{'pdf_pages':1},'source_url':'https://example.org/paper'}
            write(source/'paper.json',paper)
            (source/'original.pdf').write_bytes(b'Original PDF fixture bytes')
            write(source/'manifest.json',{'files':{p.name:digest(p.read_bytes()) for p in source.iterdir()}})
            output=root/'ported'
            ported=port_workspace(source,output)
            verify_workspace(output)
            self.assertEqual({b['origin_block_id'] for b in ported['blocks']}, {'a','b','c','d','e'})
            mapped={b['origin_block_id']:b for b in ported['blocks']}
            self.assertEqual(mapped['c']['text'],texts[2][3])
            self.assertEqual(mapped['c']['source_span']['encoding'], 'json-string')
            self.assertEqual(mapped['a']['source_span']['encoding'], 'json-string')
            self.assertIsNone(mapped['d']['source_span'])
            self.assertTrue(mapped['b']['source_span'])
            self.assertEqual(ported['references'],paper['references'])
            self.assertEqual((output/'original.pdf').read_bytes(),(source/'original.pdf').read_bytes())
            self.assertEqual(mapped['c']['citations'],['ref1'])
            self.assertEqual(mapped['e']['table'], blocks[-1]['table'])
            self.assertEqual(mapped['e']['document'], 'S1.docx')
            self.assertEqual(mapped['e']['section'], 'Supplement S1')
            self.assertIsNone(mapped['e']['source_span'])
            self.assertGreater(ported['statistics']['reference_words'], 0)
            with self.assertRaisesRegex(ValueError,'already exists'):
                port_workspace(source,output)


if __name__=='__main__':unittest.main()
