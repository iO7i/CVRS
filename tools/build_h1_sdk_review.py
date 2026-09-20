"""Build the bounded RQ002 H1 SDK review page from frozen local evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def boxes_by_file(document: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    categories = {item["id"]: item["name"] for item in document["categories"]}
    images = {item["id"]: item for item in document["images"]}
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for annotation in document["annotations"]:
        image = images[annotation["image_id"]]
        grouped[image["file_name"]].append(
            {
                "label": categories[annotation["category_id"]],
                "bbox": [float(value) for value in annotation["bbox"]],
            }
        )
    return grouped


def compare(left: list[dict[str, object]], right: list[dict[str, object]]) -> dict[str, object]:
    unused = set(range(len(right)))
    deltas: list[float] = []
    unmatched_left = 0
    for source in left:
        candidates = [
            index
            for index in unused
            if right[index]["label"] == source["label"]
        ]
        if not candidates:
            unmatched_left += 1
            continue
        index = min(
            candidates,
            key=lambda candidate: max(
                abs(a - b)
                for a, b in zip(source["bbox"], right[candidate]["bbox"], strict=True)
            ),
        )
        delta = max(
            abs(a - b)
            for a, b in zip(source["bbox"], right[index]["bbox"], strict=True)
        )
        deltas.append(delta)
        unused.remove(index)
    return {
        "source_count": len(left),
        "output_count": len(right),
        "matched_by_label": len(deltas),
        "unmatched_source": unmatched_left,
        "unmatched_output": len(unused),
        "max_abs_bbox_delta_px": max(deltas, default=0.0),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out.resolve()
    if out.exists():
        parser.error(f"refusing to overwrite output: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    source_path = root / "qualification/inputs/coco2017-val-128-official-http/annotations/instances_val2017_subset.json"
    supervision_path = root / "qualification/evidence/supervision-roundtrip-2026-09-19-corrected/annotations.json"
    fiftyone_path = root / "qualification/evidence/fiftyone-roundtrip-2026-09-19-final-category-names/export/labels.json"
    torchgeo_path = root / "qualification/evidence/torchgeo-smoke-2026-09-19/report.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    supervision = json.loads(supervision_path.read_text(encoding="utf-8"))
    fiftyone = json.loads(fiftyone_path.read_text(encoding="utf-8"))
    torchgeo = json.loads(torchgeo_path.read_text(encoding="utf-8"))
    source_boxes = boxes_by_file(source)
    supervision_boxes = boxes_by_file(supervision)
    fiftyone_boxes = boxes_by_file(fiftyone)
    source_images = sorted(source["images"], key=lambda item: item["id"])[:2]
    cases = []
    for image in source_images:
        file_name = image["file_name"]
        src = source_boxes[file_name]
        sup = supervision_boxes[file_name]
        fifty = fiftyone_boxes[file_name]
        cases.append(
            {
                "file_name": file_name,
                "source_image_id": image["id"],
                "width": image["width"],
                "height": image["height"],
                "image_path": f"../../inputs/coco2017-val-128-official-http/images/{file_name}",
                "source": src,
                "supervision": sup,
                "fiftyone": fifty,
                "supervision_comparison": compare(src, sup),
                "fiftyone_comparison": compare(src, fifty),
            }
        )
    payload = {
        "schema": "cvrs.rq002.h1-sdk-review.v1",
        "status": "HUMAN_REVIEW_REQUIRED",
        "scope": ["SUPERVISION", "FIFTYONE", "TORCHGEO_LOCAL_FIXTURE"],
        "source_sha256": sha256(source_path),
        "supervision_sha256": sha256(supervision_path),
        "fiftyone_sha256": sha256(fiftyone_path),
        "torchgeo_sha256": sha256(torchgeo_path),
        "cases": cases,
        "torchgeo": torchgeo,
        "disclosures": [
            "This H1 packet covers local SDK/bridge smokes only, not detector or foundation-model lanes.",
            "FiftyOne preserved images, detections, and used category names but omitted unused category definitions and remapped numeric category IDs.",
            "FiftyOne mask fidelity is not claimed; only segmentation-field presence was observed.",
            "TorchGeo used a deterministic local fixture, not a public geospatial AOI.",
        ],
    }
    data = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CVRS RQ002 · H1 SDK Review</title>
<style>
:root{{--bg:#0b0d12;--panel:#141821;--panel2:#1b2130;--text:#f4f6fb;--muted:#aeb7c7;--line:#30394b;--accent:#7dd3fc;--good:#4ade80;--warn:#fbbf24;--bad:#fb7185;--source:#22d3ee;--supervision:#a78bfa;--fiftyone:#fb923c}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#090b10,#101522);color:var(--text);font:15px/1.5 Inter,Segoe UI,system-ui,sans-serif}}
main{{max-width:1500px;margin:auto;padding:28px}} h1{{font-size:clamp(26px,4vw,44px);margin:0 0 8px}} h2{{margin:0 0 14px;font-size:21px}} p{{margin:0 0 12px}} .lede{{color:var(--muted);max-width:900px}}
.status{{display:inline-flex;gap:8px;align-items:center;margin:18px 0;padding:8px 12px;border:1px solid #5b4712;border-radius:999px;background:#2b220a;color:#fde68a;font-weight:700}}
.grid{{display:grid;gap:16px}} .summary{{grid-template-columns:repeat(auto-fit,minmax(230px,1fr));margin:18px 0 28px}} .card{{background:rgba(20,24,33,.94);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 14px 45px #0005}}
.metric{{font-size:28px;font-weight:800}} .label{{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.08em}} .cases{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}} button{{border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:10px;padding:10px 14px;cursor:pointer}} button.active{{border-color:var(--accent);box-shadow:0 0 0 2px #38bdf833}}
.viewer-grid{{grid-template-columns:repeat(3,minmax(0,1fr))}} .viewer h3{{margin:0 0 8px;font-size:16px}} .stage{{position:relative;overflow:auto;border:1px solid var(--line);border-radius:12px;background:#05070a;min-height:260px}} .frame{{position:relative;transform-origin:top left}} .frame img{{display:block;width:100%;height:auto}} .frame svg{{position:absolute;inset:0;width:100%;height:100%}} .box{{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}} .box-label{{font:12px Segoe UI,sans-serif;paint-order:stroke;stroke:#000;stroke-width:3px;stroke-linejoin:round}}
.source .box{{stroke:var(--source)}} .source .box-label{{fill:var(--source)}} .supervision .box{{stroke:var(--supervision)}} .supervision .box-label{{fill:var(--supervision)}} .fiftyone .box{{stroke:var(--fiftyone)}} .fiftyone .box-label{{fill:var(--fiftyone)}}
.toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:0 0 16px}} input[type=range]{{width:180px}} .comparison{{font-size:13px;color:var(--muted);margin-top:8px}} .comparison strong{{color:var(--text)}}
.notice{{border-left:4px solid var(--warn);padding:12px 14px;background:#2a220d;border-radius:8px;margin:16px 0}} .good{{color:var(--good)}} .warn{{color:var(--warn)}}
.geo-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;max-width:540px}} .geo-cell{{background:var(--panel2);border:1px solid var(--line);padding:14px;border-radius:10px}} code{{color:#bfdbfe}} ul{{padding-left:20px}} .decision{{display:flex;gap:10px;flex-wrap:wrap}} .decision button{{font-weight:700}} #decisionText{{margin-top:10px;color:var(--muted)}}
@media(max-width:1000px){{.viewer-grid{{grid-template-columns:1fr}} main{{padding:18px}}}}
</style></head><body><main>
<p class="label">CVRS Reference Qualification 002</p><h1>H1 · Local SDK bridge review</h1>
<p class="lede">Two representative COCO images are shown through the original annotation, Supervision roundtrip, and FiftyOne roundtrip. Review geometry, labels, and the disclosed interoperability differences before any further expansion.</p>
<div class="status">● HUMAN REVIEW REQUIRED</div>
<section class="grid summary" id="summary"></section>
<section class="card"><h2>COCO geometry review</h2><div class="cases" id="caseButtons"></div>
<div class="toolbar"><label>Zoom <input id="zoom" type="range" min="70" max="180" value="100"> <span id="zoomValue">100%</span></label><label><input id="labels" type="checkbox" checked> Show labels</label></div>
<div class="grid viewer-grid" id="viewers"></div></section>
<section class="card" style="margin-top:16px"><h2>TorchGeo window lineage</h2><p class="lede">The raster fixture is 64×64, EPSG:32637, 1 m/pixel. Four 32×32 windows were read without losing CRS, bounds, or affine transforms.</p><div class="geo-grid" id="geoGrid"></div><p class="comparison">This verifies local SDK behavior only. A real public GeoTIFF AOI remains unqualified.</p></section>
<section class="card" style="margin-top:16px"><h2>Disclosures to approve or reject</h2><ul id="disclosures"></ul><div class="notice">Approval means these local SDK smokes are visually acceptable for their stated scope. It does not approve detector lanes, mask fidelity, a public geospatial AOI, H2, or the full RQ002 release.</div>
<div class="decision"><button data-decision="APPROVE_LOCAL_SDK_H1">Approve local SDK H1</button><button data-decision="NEEDS_CHANGES">Needs changes</button></div><p id="decisionText">No decision saved in this browser.</p></section>
</main><script id="reviewData" type="application/json">{data}</script><script>
const d=JSON.parse(document.getElementById('reviewData').textContent);let active=0;
const fmt=n=>Number(n).toFixed(6).replace(/0+$/,'').replace(/\\.$/,'');
const summary=[['2','review images'],['128 / 906','Supervision images / boxes'],['32 / 223','FiftyOne images / boxes'],['4','TorchGeo windows']];
document.getElementById('summary').innerHTML=summary.map(x=>`<div class="card"><div class="metric">${{x[0]}}</div><div class="label">${{x[1]}}</div></div>`).join('');
const buttons=document.getElementById('caseButtons');d.cases.forEach((c,i)=>{{const b=document.createElement('button');b.textContent=`${{c.file_name}} · ${{c.source.length}} boxes`;b.onclick=()=>{{active=i;render()}};buttons.appendChild(b)}});
function svg(c,kind){{const boxes=c[kind];return `<svg viewBox="0 0 ${{c.width}} ${{c.height}}" preserveAspectRatio="none">${{boxes.map((b,i)=>{{const [x,y,w,h]=b.bbox;return `<rect class="box" x="${{x}}" y="${{y}}" width="${{w}}" height="${{h}}"/><text class="box-label" x="${{x+3}}" y="${{Math.max(13,y+13)}}">${{b.label}}</text>`}}).join('')}}</svg>`}}
function panel(c,kind,title,cmp){{return `<article class="viewer ${{kind}}"><h3>${{title}}</h3><div class="stage"><div class="frame"><img src="${{c.image_path}}" alt="${{c.file_name}} with ${{title}} boxes">${{svg(c,kind)}}</div></div><p class="comparison">${{cmp}}</p></article>`}}
function render(){{const c=d.cases[active];[...buttons.children].forEach((b,i)=>b.classList.toggle('active',i===active));const s=c.supervision_comparison,f=c.fiftyone_comparison;document.getElementById('viewers').innerHTML=panel(c,'source','Original COCO',`<strong>${{c.source.length}}</strong> source boxes · image ID ${{c.source_image_id}}`)+panel(c,'supervision','Supervision',`<strong>${{s.output_count}}</strong> boxes · max coordinate delta <strong>${{fmt(s.max_abs_bbox_delta_px)}} px</strong>`)+panel(c,'fiftyone','FiftyOne',`<strong>${{f.output_count}}</strong> boxes · max coordinate delta <strong>${{fmt(f.max_abs_bbox_delta_px)}} px</strong>`);applyControls()}}
function applyControls(){{const z=document.getElementById('zoom').value;document.getElementById('zoomValue').textContent=z+'%';document.querySelectorAll('.frame').forEach(x=>{{x.style.width=z+'%'}});document.querySelectorAll('.box-label').forEach(x=>x.style.display=document.getElementById('labels').checked?'block':'none')}}
document.getElementById('zoom').oninput=applyControls;document.getElementById('labels').onchange=applyControls;
document.getElementById('geoGrid').innerHTML=d.torchgeo.windows.map((w,i)=>`<div class="geo-cell"><strong>Window ${{i+1}}</strong><br><span class="comparison">shape ${{w.shape.join('×')}}<br>sum ${{w.sum}}<br>x ${{w.index[0]}}–${{w.index[1]}}<br>y ${{w.index[2]}}–${{w.index[3]}}</span></div>`).join('');
document.getElementById('disclosures').innerHTML=d.disclosures.map(x=>`<li>${{x}}</li>`).join('');
document.querySelectorAll('[data-decision]').forEach(b=>b.onclick=()=>{{const value={{decision:b.dataset.decision,timestamp:new Date().toISOString(),schema:d.schema,source_sha256:d.source_sha256}};localStorage.setItem('cvrs-rq002-h1-sdk',JSON.stringify(value));showDecision()}});
function showDecision(){{const v=localStorage.getItem('cvrs-rq002-h1-sdk');document.getElementById('decisionText').textContent=v?`Saved locally: ${{JSON.parse(v).decision}}. Please report this decision in the conversation; the page does not modify the repository.`:'No decision saved in this browser.'}}
render();showDecision();
</script></body></html>"""
    out.write_text(page, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "cases": len(cases), "out": str(out), "sha256": sha256(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
