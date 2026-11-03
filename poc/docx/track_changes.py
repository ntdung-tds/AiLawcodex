"""Narrow synthetic-data POC, not a general DOCX editor or production importer."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import zipfile
from lxml import etree as E

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
def q(name): return '{%s}%s' % (W, name)

class PatchError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def fail(code): raise PatchError(code)

def parse(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper(): fail('UNSAFE_XML')
    try:
        return E.fromstring(data, E.XMLParser(resolve_entities=False, no_network=True))
    except E.XMLSyntaxError:
        fail('INVALID_XML')

def load_package(data):
    if len(data) > 10_000_000: fail('PACKAGE_LIMIT')
    try:
        with zipfile.ZipFile(BytesIO(data)) as z:
            items = z.infolist()
            names = [i.filename for i in items]
            if len(names) != len(set(names)): fail('DUPLICATE_PART')
            if len(names)>500 or sum(i.file_size for i in items)>30_000_000: fail('PACKAGE_LIMIT')
            if any(n.startswith('/') or '..' in n.split('/') or '\\' in n for n in names): fail('UNSAFE_PART')
            if any('vbaproject' in n.lower() or n.startswith('_xmlsignatures/') for n in names): fail('UNSUPPORTED_PACKAGE')
            parts = {i.filename: z.read(i) for i in items}
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        fail('INVALID_PACKAGE')
    for name in ('[Content_Types].xml', '_rels/.rels', 'word/document.xml'):
        if name not in parts: fail('MISSING_PART')
    for name, content in parts.items():
        if name.endswith(('.xml', '.rels')): parse(content)
    return parts

def patch(data, changes, author='AI Law POC', timestamp='2026-11-03T00:00:00Z'):
    parts = load_package(data)
    root = parse(parts['word/document.xml'])
    if 'word/settings.xml' in parts:
        settings = parse(parts['word/settings.xml'])
        for protection in settings.findall(q('documentProtection')):
            if protection.get(q('enforcement')) not in ('0', 'false', 'off'):
                fail('DOCUMENT_PROTECTED')
    if root.tag != q('document') or root.find(q('body')) is None: fail('INVALID_DOCUMENT')
    if not isinstance(changes, list) or not changes: fail('INVALID_CHANGES')
    ids = set()
    for c in changes:
        if not isinstance(c, dict): fail('INVALID_CHANGE')
        ident = c.get('id')
        if type(ident) is not int or ident < 0 or ident > 1000000 or ident in ids: fail('INVALID_CHANGE_ID')
        ids.add(ident)
        if type(c.get('selected')) is not bool: fail('INVALID_SELECTION')
    # Existing tracked edits are not composed by this POC.
    if root.xpath('.//w:ins | .//w:del | .//w:moveFrom | .//w:moveTo | .//w:rPrChange | .//w:pPrChange', namespaces=NS): fail('EXISTING_REVISIONS')
    paras = root.findall('.//' + q('p'))
    planned=[]; targets=set()
    for c in changes:
        if not c['selected']: continue
        pi, ri, start = c.get('paragraph'), c.get('run'), c.get('start')
        if any(type(v) is not int or v < 0 for v in (pi,ri,start)): fail('INVALID_LOCATION')
        if pi >= len(paras): fail('INVALID_LOCATION')
        p = paras[pi]
        if any(a.tag == q('sdt') for a in p.iterancestors()) or p.find('.//'+q('sdt')) is not None: fail('LOCKED_OR_CONTROLLED_TEXT')
        if p.xpath('.//w:fldChar | .//w:instrText | .//w:fldSimple', namespaces=NS): fail('FIELD_AT_RISK')
        runs=p.findall(q('r'))
        if ri >= len(runs): fail('INVALID_LOCATION')
        r=runs[ri]
        if any(child.tag not in (q('rPr'),q('t')) for child in r) or len(r.findall(q('t'))) != 1: fail('UNSUPPORTED_RUN')
        if r.find('.//'+q('vanish')) is not None: fail('UNSUPPORTED_RUN')
        old,new=c.get('old'),c.get('new')
        if not isinstance(old,str) or not old or not isinstance(new,str) or old==new: fail('INVALID_TEXT')
        if any(ch in new for ch in '\r\n\t'): fail('UNSUPPORTED_TEXT')
        text=r.find(q('t')).text or ''
        if text[start:start+len(old)] != old: fail('STALE_TEXT')
        key=(pi,ri)
        if key in targets: fail('OVERLAPPING_TARGET')
        targets.add(key); planned.append((c,p,r,text))
    if not planned: fail('NO_SELECTED_CHANGES')
    def run(text, source, deleted=False):
        r=E.Element(q('r'))
        props=source.find(q('rPr'))
        if props is not None: r.append(deepcopy(props))
        t=E.SubElement(r,q('delText' if deleted else 't'))
        t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=text
        return r
    try:
        for c,p,r,text in planned:
            i=p.index(r); nodes=[]; start=c['start']; end=start+len(c['old'])
            if text[:start]: nodes.append(run(text[:start],r))
            for tag,value,offset in [('del',c['old'],0),('ins',c['new'],1)]:
                if tag=='ins' and not value: continue
                revision=E.Element(q(tag))
                revision.set(q('id'),str(c['id']*2+offset))
                revision.set(q('author'),author);revision.set(q('date'),timestamp)
                revision.append(run(value,r,tag=='del'));nodes.append(revision)
            if text[end:]: nodes.append(run(text[end:],r))
            p.remove(r)
            for n in nodes: p.insert(i,n);i+=1
    except ValueError:
        fail('INVALID_XML_TEXT')
    parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
    out=BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in parts.items(): z.writestr(name,content)
    result=out.getvalue()
    warnings=[]
    for tag in ('fldChar','fldSimple','drawing','commentRangeStart','sdt','footnoteReference','hyperlink','bookmarkStart'):
        if root.find('.//'+q(tag)) is not None: warnings.append('PRESERVED_NOT_WORD_VERIFIED:'+tag)
    return result, {'input_sha256':sha256(data).hexdigest(),'output_sha256':sha256(result).hexdigest(),
                    'applied_ids':[c['id'] for c,_,_,_ in planned], 'warnings':warnings,
                    'word_validation':'NOT_RUN','compatibility':'POC_SINGLE_RUN_ONLY'}

def patch_file(source, destination, changes):
    source,destination=Path(source),Path(destination)
    if source.resolve()==destination.resolve(): fail('SOURCE_OVERWRITE')
    data, report=patch(source.read_bytes(),changes)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False) as f:
        tmp=Path(f.name);f.write(data)
    try: tmp.replace(destination)
    finally: tmp.unlink(missing_ok=True)
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('changes');p.add_argument('output');a=p.parse_args()
    try: print(json.dumps(patch_file(a.input,a.output,json.loads(Path(a.changes).read_text())),ensure_ascii=False))
    except PatchError as e: print(json.dumps({'status':'FAIL','code':e.code}));raise SystemExit(1)
