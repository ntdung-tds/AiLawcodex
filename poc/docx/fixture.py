"""Reproducible synthetic fixture; no customer data."""
from io import BytesIO
from docx import Document
from docx.shared import RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def fixture():
    d=Document()
    for name in ('Title','Heading 1'):
        style=d.styles[name];style.font.color.rgb=RGBColor(0,0,0)
        for border in style.element.findall('.//'+qn('w:pBdr')):border.getparent().remove(border)
    d.add_heading('Hợp đồng minh họa dữ liệu giả lập',0)
    phrases=['thanh toán trong 30 ngày','giao hàng trong 10 ngày','thông báo trước 05 ngày','gia hạn 01 tháng','bảo hành 12 tháng']
    replacements=['thanh toán trong 45 ngày','giao hàng trong 15 ngày','thông báo trước 07 ngày','gia hạn 02 tháng','bảo hành 24 tháng']
    changes=[]
    for i,(old,new) in enumerate(zip(phrases,replacements)):
        p=d.add_paragraph(style='List Number');r=p.add_run('Các bên thống nhất '+old+'.');r.bold=True
        changes.append(dict(id=i+1,selected=i<3,paragraph=i+1,run=0,start=len('Các bên thống nhất '),old=old,new=new))
    d.sections[0].header.paragraphs[0].text='AI Law POC — Tổng hợp'
    d.sections[0].footer.paragraphs[0].text='Không phải hợp đồng thật'
    t=d.add_table(rows=2,cols=2);t.style='Table Grid'
    for c,text in zip([c for row in t.rows for c in row.cells],['Mục','Trạng thái','Phụ lục','Giữ nguyên']):c.text=text
    # Field outside target paragraphs must survive unchanged.
    p=d.add_paragraph('Trang ');fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
    out=BytesIO();d.save(out);return out.getvalue(),changes
