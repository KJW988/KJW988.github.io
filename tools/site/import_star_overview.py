"""Import the author-verified overview only; no manuscript or font files are committed."""
from pathlib import Path
import argparse, hashlib, json, tempfile
import fitz
ROOT=Path(__file__).resolve().parents[2]
SOURCE_ID='1L7EaOh1gzy6Ux2ThxCyijN9nzPY0qQbw'
SOURCE_SHA='0bfc1a94005a4c03f2e69afd8d5e0ef9be02c25bf2efa077da976c4cf6e5876e'
DRAWING_SHA='d7da66d524df13e2a80fc7e5be2aefabbb99ffd3085dc55886552957225ae616'
UPLOAD_SHA='2cfafbdc4d1665bc741fcdb2c19fc640f3088d5f3d9feea0f2046700ec6207e4'

def export(source,output):
    if hashlib.sha256(source.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('STAR manuscript differs from the verified author source')
    doc=fitz.open(source)
    forms=[x for x,_,parent,_ in doc[1].get_xobjects() if parent==0 and hashlib.sha256(doc.xref_stream(x)).hexdigest()==DRAWING_SHA]
    if len(forms)!=1:raise ValueError('The exact uploaded overview drawing was not found')
    form=forms[0];page=doc.new_page(width=770,height=344)
    doc.xref_set_key(page.xref,'Resources',doc.xref_get_key(form,'Resources')[1])
    stream=doc.get_new_xref();doc.update_object(stream,'<<>>');doc.update_stream(stream,doc.xref_stream(form));doc.xref_set_key(page.xref,'Contents',f'{stream} 0 R')
    svg=page.get_svg_image(text_as_path=True)
    if any(x in svg for x in ('<text','<script','@font-face','file://')):raise ValueError('Unsafe or font-dependent SVG')
    output.mkdir(parents=True,exist_ok=True)
    name='star-overview-'+hashlib.sha256(svg.encode()).hexdigest()[:12]+'.svg'
    (output/name).write_text(svg,encoding='utf-8')
    manifest=dict(name=name,sha256=hashlib.sha256(svg.encode()).hexdigest(),uploaded_pdf_sha256=UPLOAD_SHA,drawing_stream_sha256=DRAWING_SHA,width=770,height=344,vector_text=True,source_pdf_published=False)
    (output/'star-overview.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--output',type=Path,default=ROOT/'tools/site/media');a=p.parse_args()
    if a.source:export(a.source,a.output)
    else:
        import gdown
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.pdf'
            if not gdown.download(id=SOURCE_ID,output=str(source),quiet=False):raise RuntimeError('Cannot retrieve the previously shared manuscript')
            export(source,a.output)
