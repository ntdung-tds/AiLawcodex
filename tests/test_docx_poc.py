import copy
from io import BytesIO
import tempfile
from pathlib import Path
import unittest
import zipfile
from lxml import etree as E
from docx import Document
from poc.docx.fixture import fixture
from poc.docx.track_changes import patch, patch_file, PatchError, load_package, parse, q, NS

def rewrite(data, fn):
    parts=load_package(data);root=parse(parts['word/document.xml']);fn(root)
    parts['word/document.xml']=E.tostring(root)
    return repack(parts)

def repack(parts):
    out=BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for n,v in parts.items():z.writestr(n,v)
    return out.getvalue()

def projected(root, accept):
    result=[]
    for p in root.findall('.//'+q('p')):
        text=''
        for t in p.iter():
            if t.tag not in (q('t'),q('delText')):continue
            ancestors=[a.tag for a in t.iterancestors()]
            if accept and q('del') in ancestors:continue
            if not accept and q('ins') in ancestors:continue
            text+=t.text or ''
        result.append(text)
    return result

class DocxTests(unittest.TestCase):
    def setUp(self):self.data,self.changes=fixture()
    def bad(self,code,data=None,changes=None):
        with self.assertRaises(PatchError) as c:patch(self.data if data is None else data,self.changes if changes is None else changes)
        self.assertEqual(code,c.exception.code)
    def test_real_revisions_selected_only(self):
        out,report=patch(self.data,self.changes);r=parse(load_package(out)['word/document.xml'])
        self.assertEqual(3,len(r.findall('.//'+q('ins'))));self.assertEqual(3,len(r.findall('.//'+q('del'))))
        self.assertEqual([1,2,3],report['applied_ids'])
        ids=[n.get(q('id')) for n in r.xpath('.//w:ins|.//w:del',namespaces=NS)]
        self.assertEqual(6,len(set(ids)))
        self.assertTrue(all(n.get(q('author')) and n.get(q('date')) for n in r.xpath('.//w:ins|.//w:del',namespaces=NS)))
    def test_independent_accept_reject_text_oracle(self):
        out,_=patch(self.data,self.changes);r=parse(load_package(out)['word/document.xml'])
        old=projected(parse(load_package(self.data)['word/document.xml']),False)
        self.assertEqual(old,projected(r,False))
        expected=old.copy()
        for c in self.changes:
            if c['selected']:expected[c['paragraph']]=expected[c['paragraph']].replace(c['old'],c['new'],1)
        self.assertEqual(expected,projected(r,True))
    def test_other_parts_and_structure_preserved(self):
        out,_=patch(self.data,self.changes);before=load_package(self.data);after=load_package(out)
        self.assertEqual(set(before),set(after))
        for n in before:
            if n!='word/document.xml':self.assertEqual(before[n],after[n],n)
        a,b=parse(before['word/document.xml']),parse(after['word/document.xml'])
        for tag in ('tbl','sectPr','fldSimple','pPr'):
            self.assertEqual([E.tostring(n) for n in a.findall('.//'+q(tag))],[E.tostring(n) for n in b.findall('.//'+q(tag))])
        self.assertEqual(1,len(Document(BytesIO(out)).tables))
    def test_run_properties_and_whitespace(self):
        self.changes[0]['new']='  thời hạn 45 ngày  '
        out,_=patch(self.data,self.changes);r=parse(load_package(out)['word/document.xml'])
        for rev in r.xpath('.//w:ins|.//w:del',namespaces=NS):
            self.assertIsNotNone(rev.find('.//'+q('b')))
            t=rev.find('.//'+q('t')) if rev.tag==q('ins') else rev.find('.//'+q('delText'))
            self.assertEqual('preserve',t.get('{http://www.w3.org/XML/1998/namespace}space'))
        self.assertIn('  thời hạn 45 ngày  ',projected(r,True)[1])
    def test_delete_only(self):
        self.changes[0]['new']='';out,_=patch(self.data,self.changes)
        r=parse(load_package(out)['word/document.xml']);self.assertEqual(2,len(r.findall('.//'+q('ins'))))
    def test_missing_id(self):del self.changes[0]['id'];self.bad('INVALID_CHANGE_ID')
    def test_duplicate_id(self):self.changes[1]['id']=1;self.bad('INVALID_CHANGE_ID')
    def test_boolean_id(self):self.changes[0]['id']=True;self.bad('INVALID_CHANGE_ID')
    def test_selection_required(self):del self.changes[0]['selected'];self.bad('INVALID_SELECTION')
    def test_stale_text(self):self.changes[0]['old']='không có';self.bad('STALE_TEXT')
    def test_negative_offset(self):self.changes[0]['start']=-1;self.bad('INVALID_LOCATION')
    def test_wrong_run(self):self.changes[0]['run']=999;self.bad('INVALID_LOCATION')
    def test_overlap(self):
        c=copy.deepcopy(self.changes[0]);c['id']=99;self.changes.append(c);self.bad('OVERLAPPING_TARGET')
    def test_no_selected(self):
        for c in self.changes:c['selected']=False
        self.bad('NO_SELECTED_CHANGES')
    def test_locked_content_control(self):
        def fn(root):
            p=root.findall('.//'+q('p'))[1];parent=p.getparent();i=parent.index(p);parent.remove(p)
            s=E.Element(q('sdt'));pr=E.SubElement(s,q('sdtPr'));lock=E.SubElement(pr,q('lock'));lock.set(q('val'),'sdtContentLocked')
            E.SubElement(s,q('sdtContent')).append(p);parent.insert(i,s)
        self.bad('LOCKED_OR_CONTROLLED_TEXT',rewrite(self.data,fn))
    def test_field_target(self):
        def fn(root):E.SubElement(root.findall('.//'+q('p'))[1],q('fldSimple')).set(q('instr'),'PAGE')
        self.bad('FIELD_AT_RISK',rewrite(self.data,fn))
    def test_complex_field_target(self):
        def fn(root):E.SubElement(root.findall('.//'+q('p'))[1].find(q('r')),q('fldChar'))
        self.bad('FIELD_AT_RISK',rewrite(self.data,fn))
    def test_existing_revisions(self):
        out,_=patch(self.data,self.changes);self.bad('EXISTING_REVISIONS',out)
    def test_malformed_xml(self):
        parts=load_package(self.data);parts['word/document.xml']=b'<broken>';self.bad('INVALID_XML',repack(parts))
    def test_malformed_other_xml(self):
        parts=load_package(self.data);parts['word/styles.xml']=b'<broken>';self.bad('INVALID_XML',repack(parts))
    def test_dtd(self):
        parts=load_package(self.data);parts['word/document.xml']=b'<!DOCTYPE x><x/>';self.bad('UNSAFE_XML',repack(parts))
    def test_document_protection(self):
        parts=load_package(self.data);settings=parse(parts['word/settings.xml'])
        protection=E.SubElement(settings,q('documentProtection'));protection.set(q('enforcement'),'1')
        parts['word/settings.xml']=E.tostring(settings);self.bad('DOCUMENT_PROTECTED',repack(parts))
    def test_table_cell_edit(self):
        root=parse(load_package(self.data)['word/document.xml']);paras=root.findall('.//'+q('p'))
        pi=next(i for i,p in enumerate(paras) if ''.join(p.itertext())=='Giữ nguyên')
        change=dict(id=9,selected=True,paragraph=pi,run=0,start=0,old='Giữ nguyên',new='Đã chọn')
        out,_=patch(self.data,[change]);self.assertEqual('Đã chọn',projected(parse(load_package(out)['word/document.xml']),True)[pi])
    def test_bad_zip(self):self.bad('INVALID_PACKAGE',b'bad')
    def test_zip_traversal(self):
        parts=load_package(self.data);parts['../bad']=b'x';self.bad('UNSAFE_PART',repack(parts))
    def test_macro(self):
        parts=load_package(self.data);parts['word/vbaProject.bin']=b'x';self.bad('UNSUPPORTED_PACKAGE',repack(parts))
    def test_invalid_xml_character(self):self.changes[0]['new']='x\x00';self.bad('INVALID_XML_TEXT')
    def test_newline(self):self.changes[0]['new']='x\ny';self.bad('UNSUPPORTED_TEXT')
    def test_source_and_destination_unchanged_on_failure(self):
        with tempfile.TemporaryDirectory() as td:
            src,dst=Path(td)/'in.docx',Path(td)/'out.docx';src.write_bytes(self.data);dst.write_bytes(b'prior')
            self.changes[0]['old']='stale'
            with self.assertRaises(PatchError):patch_file(src,dst,self.changes)
            self.assertEqual(self.data,src.read_bytes());self.assertEqual(b'prior',dst.read_bytes())
    def test_source_overwrite_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'in.docx';src.write_bytes(self.data)
            with self.assertRaises(PatchError) as ctx:patch_file(src,src,self.changes)
            self.assertEqual('SOURCE_OVERWRITE',ctx.exception.code);self.assertEqual(self.data,src.read_bytes())
    def test_file_export_and_hashes(self):
        from hashlib import sha256
        with tempfile.TemporaryDirectory() as td:
            src,dst=Path(td)/'in.docx',Path(td)/'out.docx';src.write_bytes(self.data)
            report=patch_file(src,dst,self.changes)
            self.assertEqual(self.data,src.read_bytes());self.assertEqual(sha256(dst.read_bytes()).hexdigest(),report['output_sha256'])
            self.assertEqual('NOT_RUN',report['word_validation']);self.assertIn('PRESERVED_NOT_WORD_VERIFIED:fldSimple',report['warnings'])
if __name__=='__main__':unittest.main()
