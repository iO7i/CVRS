"""Escaped, offline static documentation and results pages. No external CDN."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import html,re,json,shutil,urllib.parse
from cvsubstrate.adoption.common import output_tree,write_text
from cvsubstrate.provenance.io import read_json,write_json,digest

CSS='body{margin:0;font:16px/1.6 system-ui,sans-serif;background:#fbfcfd;color:#162433}header{padding:28px 6%;border-bottom:1px solid #d6dee7}main{max-width:1050px;margin:auto;padding:36px 28px}h1,h2{line-height:1.2}h1{font-size:2.4rem}h2{margin-top:2rem}nav{display:flex;flex-wrap:wrap;gap:16px}a{color:#145c94}pre{padding:18px;overflow:auto;background:#eef2f6;border:1px solid #d6dee7;border-radius:8px}code{font-family:ui-monospace,monospace}table{border-collapse:collapse;width:100%}td,th{padding:9px;border-bottom:1px solid #d6dee7;text-align:left;vertical-align:top}.muted{color:#506273}.badge{padding:3px 9px;background:#e8eef5;border-radius:4px}.card{padding:18px;margin:16px 0;border:1px solid #d6dee7;border-radius:8px}.graph{display:flex;flex-wrap:wrap;gap:12px}.node{border:1px solid #b5c5d5;padding:12px}.warn{border-left:4px solid #a45f0c;padding-left:12px}img,svg{max-width:100%;height:auto}footer{padding:24px;text-align:center;border-top:1px solid #d6dee7}input{font:inherit;padding:8px;max-width:100%}'

def page(title,body,nav=''):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>'+html.escape(title)+'</title><style>'+CSS+'</style></head><body><header><strong>CV Research Substrate</strong><nav>'+nav+'</nav></header><main>'+body+'</main><footer>Implementation and evidence are separate. No external scripts or tracking.</footer></body></html>'

def _inline(text):
    text=html.escape(text)
    text=re.sub(r'`([^`]+)`',r'<code>\1</code>',text)
    def link(m):
        label,url=m.group(1),html.unescape(m.group(2));p=urllib.parse.urlsplit(url)
        if p.scheme and p.scheme not in {'https','http','mailto'}:return label
        if p.path.endswith('.md'):
            p=p._replace(path=p.path[:-3]+'.html');url=urllib.parse.urlunsplit(p)
        return '<a href="'+html.escape(url,quote=True)+'">'+label+'</a>'
    text=re.sub(r'\[([^]]+)\]\(([^)]+)\)',link,text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',text)
    return text

def markdown(text):
    out: list[str]=[];code: list[str]=[];in_code=False;table: list[str]=[]
    def flush_table():
        nonlocal table
        if table:
            rows=[]
            for i,line in enumerate(table):
                if re.fullmatch(r'[\s|:-]+',line):continue
                tag='th' if i==0 else 'td'
                rows.append('<tr>'+''.join('<'+tag+'>'+_inline(c.strip())+'</'+tag+'>' for c in line.strip('|').split('|'))+'</tr>')
            out.append('<table>'+''.join(rows)+'</table>');table=[]
    for line in text.splitlines():
        if line.startswith('```'):
            flush_table()
            if in_code:out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');code=[]
            in_code=not in_code;continue
        if in_code:code.append(line);continue
        if line.startswith('|'):table.append(line);continue
        flush_table()
        m=re.match(r'^(#{1,6}) (.+)$',line)
        if m:
            level=len(m.group(1));ident=re.sub(r'[^a-z0-9]+','-',m.group(2).lower()).strip('-')
            out.append(f'<h{level} id="{ident}">'+_inline(m.group(2))+f'</h{level}>')
        elif line.startswith('- '):out.append('<p>• '+_inline(line[2:])+'</p>')
        elif line.strip():out.append('<p>'+_inline(line)+'</p>')
    flush_table()
    if code:out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(out)

def build_docs(source,destination):
    root=Path(source);docs=root/'docs'/'public'
    if not docs.is_dir():raise ValueError('docs/public is absent')
    pages=list(sorted(docs.rglob('*.md')))
    with output_tree(destination,seal=False) as out:
        navigation='<a href="index.html">Start</a> <a href="heritage.html">Legacy projects</a> <a href="research.html">Research</a> <a href="extend.html">Extend</a>'
        for p in pages:
            rel=p.relative_to(docs).with_suffix('.html');prefix='../'*(len(rel.parts)-1)
            nav=navigation.replace('href="','href="'+prefix)
            write_text(out/rel,page(p.stem,markdown(p.read_text('utf-8')),nav))
        assets=docs/'assets'
        if assets.exists():shutil.copytree(assets,out/'assets')
        write_json(out/'search.json',[{'title':p.stem,'path':str(p.relative_to(docs).with_suffix('.html'))} for p in pages])
    return {'status':'BUILT','pages':len(pages),'destination':str(destination)}

def link_check(site):
    root=Path(site).resolve();issues=[];checked=0
    for p in root.rglob('*.html'):
        for link in re.findall(r'(?:href|src)="([^"]+)"',p.read_text('utf-8')):
            u=urllib.parse.urlsplit(html.unescape(link))
            if u.scheme or u.netloc or not u.path:continue
            checked+=1
            decoded=urllib.parse.unquote(u.path)
            target=(root/decoded.lstrip('/')).resolve() if decoded.startswith('/') else (p.parent/decoded).resolve()
            if not target.is_relative_to(root) or not target.exists():issues.append({'page':p.relative_to(root).as_posix(),'target':u.path})
    return {'status':'PASS' if not issues else 'FAIL','checked':checked,'broken':issues,'scope':'Local link targets, not external websites'}

def results_site(runs,destination):
    records: list[dict[str, Any]]=[]
    with output_tree(destination,seal=False) as out:
        for index,path in enumerate(runs):
            p=Path(path);record: dict[str, Any]={'id':p.name,'files':{}}
            for name in ('run.json','run_manifest.json','execution.json','metrics.json','environment.json','comparison.json','result.json'):
                if (p/name).is_file():record['files'][name]=read_json(p/name)
            from cvsubstrate.security import sanitize
            record=sanitize(record);records.append(record);filename='run-'+str(index)+'.html'
            body='<h1>'+html.escape(p.name)+'</h1>'
            for name,value in record['files'].items():body+='<h2>'+html.escape(name)+'</h2><pre>'+html.escape(json.dumps(value,indent=2,ensure_ascii=False))+'</pre>'
            write_text(out/filename,page(p.name,body,'<a href="index.html">All runs</a>'))
        write_json(out/'registry.json',records)
        write_text(out/'registry.ndjson',''.join(json.dumps(r,ensure_ascii=False,allow_nan=False)+'\n' for r in records))
        links=''.join('<div class="card"><a href="run-'+str(i)+'.html">'+html.escape(r['id'])+'</a></div>' for i,r in enumerate(records))
        write_text(out/'index.html',page('Research results','<h1>Research results</h1><p class="warn">These are recorded artifacts, not automatic independent reproductions.</p>'+links))
    return {'status':'EXPORTED','runs':len(records),'destination':str(destination)}

def graph_site(spec,destination):
    nodes=spec.get('nodes',[]);cards=''
    for n in nodes:
        cards+='<div class="node"><strong>'+html.escape(n['id'])+'</strong><br>'+html.escape(str(n.get('worker',n.get('paper_spec',''))))+'<br>depends on '+html.escape(', '.join(n.get('depends_on',[])))+'</div>'
    with output_tree(destination,seal=False) as out:
        write_json(out/'graph.json',spec);write_text(out/'index.html',page('Worker composition','<h1>Worker composition</h1><div class="graph">'+cards+'</div><p>Edges transfer materialized artifacts, not autograd graphs.</p>'))
    return {'status':'EXPORTED','nodes':len(nodes)}

def visual_diff(image,left,right,destination,*,allow_image_copy=False):
    if not allow_image_copy:raise ValueError('image inclusion requires explicit permission; do not publish private datasets')
    from PIL import Image,ImageDraw
    p=Path(image)
    with output_tree(destination,seal=False) as out:
        for name,pred,color in [('left',left,'#00AAFF'),('right',right,'#FF8800')]:
            im=Image.open(p).convert('RGB');draw=ImageDraw.Draw(im)
            if (pred['width'],pred['height'])!=im.size:raise ValueError('overlay geometry mismatch')
            for box,score in zip(pred.get('boxes',[]),pred.get('scores',[])):
                draw.rectangle(box,outline=color,width=2);draw.text((box[0],box[1]),format(score,'.2f'),fill=color)
            for poly in pred.get('polygons',[]):
                pts=list(zip(poly[::2],poly[1::2])) if poly and isinstance(poly[0],(int,float)) else [tuple(x) for x in poly]
                if pts:draw.line(pts+[pts[0]],fill=color,width=2)
            for item in pred.get('masks',[]):
                import numpy as np
                from cvsubstrate.vision.masks import decode_mask
                m=item.get('mask',item)
                if 'size' in m:m={'height':m['size'][0],'width':m['size'][1],'counts':m['counts'],'order':'F'}
                arr=decode_mask(m)
                if arr.shape!=(im.height,im.width):raise ValueError('mask overlay must be in original-image coordinates')
                im.paste(Image.new('RGB',im.size,color),(0,0),Image.fromarray(arr.astype('uint8')*70))
            im.save(out/(name+'.png'))
        write_text(out/'index.html',page('Prediction comparison','<h1>Prediction comparison</h1><p>No correctness labels inferred without ground truth.</p><h2>A</h2><img src="left.png" alt="Model A detections"><h2>B</h2><img src="right.png" alt="Model B detections">'))
    return {'status':'EXPORTED','image_included':True}
