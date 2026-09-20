"""Offline H2 qualification-matrix browser with no model or network dependency."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from cvsubstrate.adoption.common import output_tree, write_text
from cvsubstrate.provenance.io import digest, read_json, write_json


ALLOWED = {
    "PASS",
    "FAIL_CVRS",
    "FAIL_FIDELITY",
    "FAIL_NATIVE_RUNTIME_COMPATIBILITY",
    "BLOCKED_EXTERNAL",
    "OUT_OF_SCOPE",
}
STATUS_LABELS = {
    "PASS": "Passed",
    "FAIL_CVRS": "CVRS Failure",
    "FAIL_FIDELITY": "Fidelity Failure",
    "FAIL_NATIVE_RUNTIME_COMPATIBILITY": "Native Runtime Failure",
    "BLOCKED_EXTERNAL": "Externally Blocked",
    "OUT_OF_SCOPE": "Out of Scope",
}
STATUS_ORDER = [
    "PASS",
    "FAIL_CVRS",
    "FAIL_FIDELITY",
    "FAIL_NATIVE_RUNTIME_COMPATIBILITY",
    "BLOCKED_EXTERNAL",
    "OUT_OF_SCOPE",
]


def _validate(matrix: dict[str, Any]) -> None:
    if matrix.get("schema") != "cvrs.h2.qualification-matrix.v1":
        raise ValueError("unsupported qualification matrix")
    references = {item["id"] for item in matrix.get("references", [])}
    if references != {"CVRS_REFERENCE_001", "CVRS_REFERENCE_002"}:
        raise ValueError("both frozen reference qualifications are required")
    lanes = matrix.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("qualification matrix has no lanes")
    required = {
        "reference",
        "lane",
        "disposition",
        "implementation",
        "native_execution",
        "artifact_fidelity",
        "evaluator_or_deployment",
        "portable_evidence",
        "evidence",
    }
    for lane in lanes:
        if not isinstance(lane, dict) or not required <= lane.keys():
            raise ValueError("incomplete qualification lane")
        if lane["reference"] not in references or lane["disposition"] not in ALLOWED:
            raise ValueError("invalid reference or generic disposition")


def _short_reference(value: str) -> str:
    return value.replace("CVRS_REFERENCE_", "RQ")


def _dimension_cell(value: str) -> str:
    state = "neutral"
    if value.startswith("PASS") or value in {
        "COMPLETE_WITH_LIMITATIONS",
        "HISTORICAL_EVIDENCE_INGESTED",
    }:
        state = "positive"
    elif value.startswith("FAIL"):
        state = "negative"
    elif value.startswith("BLOCKED") or value in {
        "NOT_RUN",
        "NOT_PRODUCED",
        "PINNED_NOT_ACQUIRED",
    }:
        state = "warning"
    return (
        f'<span class="dimension {state}" title="{html.escape(value)}">'
        f"{html.escape(value)}</span>"
    )


def _render_rows(matrix: dict[str, Any]) -> str:
    rows: list[str] = []
    for index, lane in enumerate(matrix["lanes"]):
        disposition = html.escape(lane["disposition"])
        lane_name = html.escape(lane["lane"])
        rows.append(
            f'<tr data-index="{index}" data-reference="{html.escape(lane["reference"])}" '
            f'data-disposition="{disposition}"><td><span class="reference-chip" translate="no">'
            f'{html.escape(_short_reference(lane["reference"]))}</span></td>'
            f'<td class="lane-name"><button type="button" class="lane-button" '
            f'data-inspect-index="{index}" aria-label="Inspect {lane_name}"><strong>{lane_name}</strong>'
            f'<small translate="no">{html.escape(lane["implementation"])}</small></button></td>'
            f'<td><span class="status-pill {disposition}">{html.escape(STATUS_LABELS[lane["disposition"]])}</span></td>'
            f'<td>{_dimension_cell(lane["native_execution"])}</td>'
            f'<td>{_dimension_cell(lane["artifact_fidelity"])}</td>'
            f'<td>{_dimension_cell(lane["evaluator_or_deployment"])}</td>'
            f'<td>{_dimension_cell(lane["portable_evidence"])}</td></tr>'
        )
    return "".join(rows)


def _render_health(matrix: dict[str, Any]) -> tuple[str, str]:
    total = len(matrix["lanes"])
    counts = {
        name: sum(lane["disposition"] == name for lane in matrix["lanes"])
        for name in ALLOWED
    }
    segments: list[str] = []
    legend: list[str] = []
    for name in STATUS_ORDER:
        count = counts[name]
        if not count:
            continue
        percent = count / total * 100
        segments.append(
            f'<span class="health-segment {name}" style="width:{percent:.4f}%" '
            f'title="{html.escape(STATUS_LABELS[name])}: {count}"></span>'
        )
        legend.append(
            f'<button type="button" data-status-filter="{name}">'
            f'<i class="legend-dot {name}" aria-hidden="true"></i>'
            f'<strong>{count}</strong><span>{html.escape(STATUS_LABELS[name])}</span></button>'
        )
    return "".join(segments), "".join(legend)


def _status_options() -> str:
    return "".join(
        f'<option value="{value}">{html.escape(STATUS_LABELS[value])}</option>'
        for value in STATUS_ORDER
    )


def render_qualification_browser(matrix_path: Path, destination: Path) -> dict[str, Any]:
    matrix = read_json(Path(matrix_path))
    _validate(matrix)
    data = (
        json.dumps(matrix, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    segments, legend = _render_health(matrix)
    version = html.escape(matrix["candidate_version"])
    lane_count = len(matrix["lanes"])
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><meta name="color-scheme" content="dark"><meta name="theme-color" content="#08111d">
<title>CVRS · H2 Qualification Browser</title><link rel="stylesheet" href="app.css"></head>
<body><a class="skip-link" href="#qualification-lanes">Skip to qualification lanes</a>
<header class="topbar"><a class="brand" href="#overview" aria-label="CVRS qualification overview"><strong>CVRS</strong><span>Research Observatory</span></a>
<label class="global-search"><span>Search</span><input id="global-search" name="qualification-search" type="search" autocomplete="off" spellcheck="false" placeholder="Search lanes or evidence…"><kbd>/</kbd></label>
<span class="version" translate="no">{version}</span></header>
<div class="workspace"><main id="overview"><section class="page-head"><div><span class="eyebrow">H2 Alpha Freeze</span><h1>Qualification Browser</h1><p>Inspect native execution, artifact fidelity, evaluator fidelity, and portable evidence without hiding failures.</p></div></section>
<section class="health-panel" aria-labelledby="health-heading"><div class="section-heading"><div><h2 id="health-heading">Qualification Status</h2><span>{lane_count} frozen lanes</span></div></div>
<div class="health-bar" role="img" aria-label="Qualification disposition distribution">{segments}</div><div class="health-legend">{legend}</div></section>
<section class="lanes" id="qualification-lanes" aria-labelledby="lanes-heading"><div class="section-heading table-heading"><div><h2 id="lanes-heading">Qualification Lanes</h2><span><b id="visible-count">{lane_count}</b> shown</span></div>
<div class="filters"><label><span>Status</span><select id="status-filter"><option value="ALL">All Statuses</option>{_status_options()}</select></label><label><span>Reference</span><select id="reference-filter"><option value="ALL">All References</option><option value="CVRS_REFERENCE_001">RQ001</option><option value="CVRS_REFERENCE_002">RQ002</option></select></label><button type="button" class="clear-button" id="clear-filters" hidden>Clear Filters</button></div></div>
<div class="table-wrap"><table><thead><tr><th>Reference</th><th>Lane / Implementation</th><th>Disposition</th><th>Native Execution</th><th>Artifact Fidelity</th><th>Evaluator / Deployment</th><th>Portable Evidence</th></tr></thead><tbody>{_render_rows(matrix)}</tbody></table><div id="empty-state" class="empty-state" hidden><strong>No Matching Lanes</strong><span>Clear the filters or use a broader search.</span></div></div></section></main>
<aside class="inspector" id="inspector" aria-label="Selected qualification lane"><div class="inspector-head"><span>Evidence</span><button type="button" id="close-inspector" aria-label="Close evidence inspector">Close</button></div><div id="inspector-content" aria-live="polite"></div></aside></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div><script id="matrix-data" type="application/json">{data}</script><script src="app.js"></script></body></html>"""
    with output_tree(Path(destination), seal=False) as out:
        write_text(out / "index.html", document)
        write_text(out / "app.css", _browser_css())
        write_text(out / "app.js", _browser_js())
        write_json(out / "qualification-matrix.json", matrix)
        write_json(
            out / "browser-manifest.json",
            {
                "schema": "cvrs.h2.browser.v1",
                "candidate_version": matrix["candidate_version"],
                "matrix_digest": digest(matrix),
                "lanes": lane_count,
                "references": len(matrix["references"]),
                "external_network_required": False,
                "interface": "research-observatory-v4",
            },
        )
    return {
        "status": "BUILT",
        "destination": str(destination),
        "lanes": lane_count,
        "references": 2,
        "external_network_required": False,
    }


def _browser_css() -> str:
    return r"""
:root{color-scheme:dark;--bg:#08111d;--panel:#0c1725;--panel2:#101f31;--line:#203348;--line2:#31506f;--text:#eef5fc;--muted:#8da2b8;--blue:#3b8cff;--cyan:#59c9ff;--pass:#37d28b;--cvrs:#ff596d;--fidelity:#ff82a0;--runtime:#aa83ff;--blocked:#f7c94b;--scope:#8496a9;--inspect:370px;--top:58px}
*{box-sizing:border-box}html{scroll-behavior:smooth;color-scheme:dark}body{margin:0;min-width:320px;background:var(--bg);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}button,input,select,a{touch-action:manipulation;-webkit-tap-highlight-color:transparent}button,input,select{font:inherit}.skip-link{position:fixed;top:-50px;left:12px;z-index:100;background:var(--blue);color:white;padding:9px 12px;border-radius:6px}.skip-link:focus{top:8px}.topbar{position:sticky;top:0;z-index:30;height:var(--top);display:grid;grid-template-columns:auto minmax(280px,560px) 1fr;align-items:center;gap:28px;padding:0 24px;border-bottom:1px solid var(--line);background:rgba(8,17,29,.96);backdrop-filter:blur(16px)}.brand{display:flex;align-items:baseline;gap:10px;color:var(--text);text-decoration:none}.brand strong{color:#b9d9ff;font-size:19px;letter-spacing:.055em}.brand span{color:var(--muted);font-size:11px}.global-search{height:36px;display:flex;align-items:center;border:1px solid var(--line2);border-radius:7px;background:#0d1b2c}.global-search:focus-within{border-color:var(--blue);box-shadow:0 0 0 3px rgba(59,140,255,.16)}.global-search>span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}.global-search input{flex:1;min-width:0;border:0;outline:0;color:var(--text);background:transparent;padding:0 11px}.global-search input::placeholder{color:#7890a7}.global-search kbd{margin-right:7px;border:1px solid var(--line2);border-radius:4px;background:#15283f;color:#7f97ae;padding:1px 7px}.version{justify-self:end;color:#8298ae;font:11px ui-monospace,SFMono-Regular,Consolas,monospace}.workspace{display:grid;grid-template-columns:minmax(0,1fr) var(--inspect);min-height:calc(100vh - var(--top))}main{min-width:0}.page-head,.health-panel,.lanes{scroll-margin-top:calc(var(--top) + 8px)}.page-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;padding:28px 30px 22px;border-bottom:1px solid var(--line)}.page-head h1{margin:3px 0 7px;font-size:29px;line-height:1.15;letter-spacing:-.02em;text-wrap:balance}.page-head p{max-width:720px;margin:0;color:var(--muted);font-size:12px;text-wrap:pretty}.eyebrow{color:var(--cyan);font-size:11px;font-weight:700;letter-spacing:.03em}.candidate-badge{margin-top:5px;border:1px solid #2f6da7;border-radius:999px;background:#102d4d;color:#7cc9ff;font-size:11px;padding:5px 10px;white-space:nowrap}.health-panel,.lanes{padding:20px 30px;border-bottom:1px solid var(--line)}.section-heading{display:flex;align-items:end;justify-content:space-between;gap:20px;margin-bottom:14px}.section-heading>div{min-width:0}.section-heading h2{display:inline;margin:0;font-size:16px;text-wrap:balance}.section-heading>div>span{margin-left:9px;color:var(--muted);font-size:11px}.text-button,.clear-button{border:0;background:transparent;color:#70baff;cursor:pointer;padding:7px 8px}.text-button:hover,.clear-button:hover{text-decoration:underline}.health-bar{display:flex;height:9px;overflow:hidden;border-radius:5px;background:#142338}.PASS{--status:var(--pass)}.FAIL_CVRS{--status:var(--cvrs)}.FAIL_FIDELITY{--status:var(--fidelity)}.FAIL_NATIVE_RUNTIME_COMPATIBILITY{--status:var(--runtime)}.BLOCKED_EXTERNAL{--status:var(--blocked)}.OUT_OF_SCOPE{--status:var(--scope)}.health-segment,.legend-dot{background:var(--status)}.health-legend{display:flex;flex-wrap:wrap;gap:10px 24px;margin-top:12px}.health-legend button{display:flex;align-items:center;gap:6px;border:0;background:transparent;color:#aabed1;cursor:pointer;padding:3px 0;font-size:11px;font-variant-numeric:tabular-nums}.health-legend button:hover{color:white}.legend-dot{width:8px;height:8px;border-radius:50%}.health-legend strong{color:var(--text)}.table-heading{align-items:end}.filters{display:flex;align-items:end;gap:8px}.filters label{display:grid;gap:3px;color:#748ba2;font-size:10px}.filters select{min-width:134px;border:1px solid var(--line2);border-radius:6px;background:#0e1d2e;color:#ccdae8;padding:7px 28px 7px 9px}.clear-button{height:34px}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:7px;background:#091521}table{width:100%;min-width:980px;border-collapse:collapse}th,td{text-align:left;vertical-align:middle;padding:10px;border-bottom:1px solid #1b2e41}th{position:sticky;top:0;z-index:2;background:#102237;color:#8198ae;font-size:9px;font-weight:700;letter-spacing:.035em;text-transform:uppercase}tbody tr{cursor:default}tbody tr:hover{background:#0d253e}tbody tr.selected{background:#133257;box-shadow:inset 3px 0 var(--blue)}tbody tr:last-child td{border-bottom:0}.reference-chip{display:inline-block;border:1px solid #254e74;border-radius:4px;background:#0f2a46;color:#75c2ff;padding:5px 6px;font:700 10px/1 ui-monospace,SFMono-Regular,Consolas,monospace}.lane-name{min-width:235px}.lane-button{display:block;width:100%;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer;padding:0}.lane-button:hover strong{color:white}.lane-name strong{display:block;color:#dce8f4;font-size:12px}.lane-name small{display:block;margin-top:3px;color:#9bb0c5;font:10px/1.3 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.status-pill{display:inline-block;max-width:145px;border:1px solid var(--status);border-radius:999px;background:color-mix(in srgb,var(--status) 9%,transparent);color:var(--status);padding:4px 7px;font-size:9px;font-weight:750;line-height:1.2;text-transform:uppercase}.dimension{display:inline-flex;align-items:center;max-width:145px;color:#a9bfd3;font:10px/1.3 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.dimension:before{content:"";width:6px;height:6px;flex:0 0 auto;margin-right:6px;border-radius:50%;background:#718397}.dimension.positive:before{background:var(--pass)}.dimension.negative:before{background:var(--cvrs)}.dimension.warning:before{background:var(--blocked)}.empty-state{padding:48px;text-align:center}.empty-state strong,.empty-state span{display:block}.empty-state span{margin-top:4px;color:var(--muted)}.inspector{position:sticky;top:var(--top);height:calc(100vh - var(--top));overflow:auto;overscroll-behavior:contain;border-left:1px solid var(--line);background:#08131f;padding:20px}.inspector-head{display:flex;align-items:center;justify-content:space-between;padding-bottom:12px;border-bottom:1px solid var(--line);color:var(--cyan);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}.inspector-head button{display:none;border:0;background:transparent;color:#9eb1c4;cursor:pointer}.inspector-title{display:grid;gap:7px;padding:18px 0 14px}.inspector-title h2{margin:0;font-size:18px;line-height:1.25;text-wrap:balance}.inspector-meta{display:flex;align-items:center;gap:7px;color:#8096ac;font-size:10px}.inspector-summary{margin-bottom:18px;border-left:3px solid var(--status);background:#0d1d2f;padding:12px}.inspector-summary strong{display:block;margin-bottom:4px;color:#dceaf7}.inspector-summary p{margin:0;color:#9bb0c5;font-size:11px}.inspector-section{margin:20px 0}.inspector-section h3{margin:0 0 8px;color:#d7e5f3;font-size:11px}.evidence-grid{overflow:hidden;border:1px solid var(--line);border-radius:6px}.evidence-row{display:grid;grid-template-columns:105px minmax(0,1fr);gap:8px;padding:8px 9px;border-bottom:1px solid var(--line);font-size:10px}.evidence-row:last-child{border-bottom:0}.evidence-row span{color:#71879e}.evidence-row code{color:#bdd2e6;overflow-wrap:anywhere}.evidence-path{display:block;border:1px solid var(--line);border-radius:6px;background:#0c2034;color:#82c8ff;padding:10px;font:10px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.evidence-actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px}.copy-path,.open-evidence{display:flex;align-items:center;justify-content:center;border:1px solid var(--line2);border-radius:6px;background:#11243a;color:#bdd5e9;padding:8px;cursor:pointer;text-decoration:none}.copy-path:hover,.open-evidence:hover{border-color:var(--blue);color:white}.inspector-footnote{padding-top:13px;border-top:1px solid var(--line);color:#8da2b8;font-size:10px}.toast{position:fixed;right:18px;bottom:18px;z-index:80;pointer-events:none;opacity:0;transform:translateY(16px);border:1px solid #2e6fa9;border-radius:6px;background:#143355;color:#ecf6ff;padding:9px 12px;transition:transform .2s,opacity .2s}.toast.visible{opacity:1;transform:translateY(0)}:focus-visible{outline:2px solid #63b7ff;outline-offset:2px}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.inspector,.toast{transition:none}}@media(max-width:1000px){:root{--inspect:330px}.page-head p{max-width:560px}.health-legend{column-gap:16px}}@media(max-width:820px){.workspace{display:block}.inspector{position:fixed;top:var(--top);right:0;bottom:0;z-index:40;width:min(380px,100vw);height:auto;transform:translateX(105%);transition:transform .2s;box-shadow:-20px 0 50px rgba(0,0,0,.38)}body.inspector-open .inspector{transform:translateX(0)}.inspector-head button{display:block}.section-heading{align-items:flex-start;flex-direction:column}.filters{width:100%;flex-wrap:wrap}.filters label{flex:1}.filters select{width:100%;min-width:0}}@media(max-width:560px){:root{--top:102px}.topbar{height:var(--top);grid-template-columns:1fr auto;grid-template-rows:44px 44px;gap:0 12px;padding:6px 14px}.brand span{display:none}.global-search{grid-column:1/-1;grid-row:2}.version{grid-column:2;grid-row:1}.page-head{padding:22px 16px 18px}.page-head h1{font-size:26px}.page-head p{font-size:11px}.health-panel,.lanes{padding:17px 16px}.health-legend{display:grid;grid-template-columns:1fr 1fr;gap:7px 12px}.table-wrap{margin-inline:-16px;border-right:0;border-left:0;border-radius:0}.clear-button{padding-inline:0}.inspector{top:var(--top)}}
"""


def _browser_js() -> str:
    return r"""
"use strict";
const matrix=JSON.parse(document.getElementById("matrix-data").textContent);
const rows=[...document.querySelectorAll("tbody tr")];
const laneButtons=[...document.querySelectorAll("[data-inspect-index]")];
const search=document.getElementById("global-search");
const statusFilter=document.getElementById("status-filter");
const referenceFilter=document.getElementById("reference-filter");
const visibleCount=document.getElementById("visible-count");
const emptyState=document.getElementById("empty-state");
const inspectorPanel=document.getElementById("inspector");
const inspector=document.getElementById("inspector-content");
const closeInspectorButton=document.getElementById("close-inspector");
const clearFiltersButton=document.getElementById("clear-filters");
const main=document.querySelector("main");
const topbar=document.querySelector(".topbar");
const referenceNames=Object.fromEntries(matrix.references.map(item=>[item.id,item.title]));
const statusNames={PASS:"Passed",FAIL_CVRS:"CVRS Failure",FAIL_FIDELITY:"Fidelity Failure",FAIL_NATIVE_RUNTIME_COMPATIBILITY:"Native Runtime Failure",BLOCKED_EXTERNAL:"Externally Blocked",OUT_OF_SCOPE:"Out of Scope"};
const statusCopy={PASS:"This lane met its declared qualification contract.",FAIL_CVRS:"CVRS rejected this lane under its canonical contract. The native result remains preserved.",FAIL_FIDELITY:"Execution completed, but the converted or deployed result did not preserve the required fidelity.",FAIL_NATIVE_RUNTIME_COMPATIBILITY:"The native runtime failed before a qualifying artifact could be produced.",BLOCKED_EXTERNAL:"A required external asset or permission was unavailable.",OUT_OF_SCOPE:"This dimension was outside the frozen qualification scope."};
const escapeHtml=value=>String(value).replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const isMobile=()=>window.matchMedia("(max-width: 820px)").matches;
let selectedIndex=null;
let lastTrigger=null;
function setSelectValue(control,value){
  const valid=[...control.options].some(option=>option.value===value);
  control.value=valid?value:"ALL";
  return valid;
}
function evidenceHref(path){
  try{return new URL("../../../"+String(path).replace(/^\/+/, ""),window.location.href).href;}
  catch(error){return "#";}
}
function writeUrl(index){
  try{
    const url=new URL(window.location.href);
    const values={q:search.value.trim(),status:statusFilter.value==="ALL"?"":statusFilter.value,reference:referenceFilter.value==="ALL"?"":referenceFilter.value,lane:Number.isInteger(index)?String(index):""};
    Object.entries(values).forEach(([key,value])=>value?url.searchParams.set(key,value):url.searchParams.delete(key));
    history.replaceState(null,"",url);
  }catch(error){return;}
}
function setInspectorState(open,moveFocus=true){
  if(!isMobile()){
    document.body.classList.remove("inspector-open");
    inspectorPanel.inert=false;inspectorPanel.removeAttribute("aria-hidden");
    inspectorPanel.removeAttribute("role");inspectorPanel.removeAttribute("aria-modal");
    main.inert=false;topbar.inert=false;return;
  }
  document.body.classList.toggle("inspector-open",open);
  inspectorPanel.inert=!open;inspectorPanel.setAttribute("aria-hidden",open?"false":"true");
  main.inert=open;topbar.inert=open;
  if(open){inspectorPanel.setAttribute("role","dialog");inspectorPanel.setAttribute("aria-modal","true");if(moveFocus)closeInspectorButton.focus();}
  else{inspectorPanel.removeAttribute("role");inspectorPanel.removeAttribute("aria-modal");}
}
function closeInspector(restoreFocus=true){
  setInspectorState(false,false);
  if(restoreFocus){const target=lastTrigger&&document.contains(lastTrigger)?lastTrigger:search;target.focus();}
}
function renderEmptyInspector(message,updateUrl=false){
  selectedIndex=null;
  rows.forEach(row=>row.classList.remove("selected"));
  inspector.textContent="";
  const title=document.createElement("div");title.className="inspector-title";title.innerHTML="<h2>No selected lane</h2>";
  const summary=document.createElement("div");summary.className="inspector-summary OUT_OF_SCOPE";
  const strong=document.createElement("strong");strong.textContent="Filtered view";
  const para=document.createElement("p");para.textContent=message;summary.append(strong,para);inspector.append(title,summary);
  setInspectorState(false,false);if(updateUrl)writeUrl(null);
}
function renderInspector(index,reveal=false,updateUrl=true,trigger=null){
  if(!Number.isInteger(index)||index<0||index>=matrix.lanes.length)return;
  selectedIndex=index;if(trigger)lastTrigger=trigger;
  const lane=matrix.lanes[index];
  const fields=[["Implementation",lane.implementation],["Native Execution",lane.native_execution],["Artifact Fidelity",lane.artifact_fidelity],["Evaluator / Deployment",lane.evaluator_or_deployment],["Portable Evidence",lane.portable_evidence]];
  const evidenceUrl=evidenceHref(lane.evidence);
  rows.forEach(row=>row.classList.toggle("selected",Number(row.dataset.index)===index));
  inspector.textContent="";
  const title=document.createElement("div");title.className="inspector-title";
  const meta=document.createElement("div");meta.className="inspector-meta";
  [lane.reference.replace("CVRS_REFERENCE_","RQ"),"·",referenceNames[lane.reference]].forEach(value=>{const span=document.createElement("span");span.textContent=value;meta.appendChild(span);});
  const heading=document.createElement("h2");heading.textContent=lane.lane;
  const status=document.createElement("span");status.className="status-pill "+lane.disposition;status.textContent=statusNames[lane.disposition];
  title.append(meta,heading,status);
  const summary=document.createElement("div");summary.className="inspector-summary "+lane.disposition;
  const summaryTitle=document.createElement("strong");summaryTitle.textContent="Disposition";
  const summaryText=document.createElement("p");summaryText.textContent=statusCopy[lane.disposition];summary.append(summaryTitle,summaryText);
  const dimensions=document.createElement("section");dimensions.className="inspector-section";
  const dimensionsTitle=document.createElement("h3");dimensionsTitle.textContent="Qualification Dimensions";
  const grid=document.createElement("div");grid.className="evidence-grid";
  fields.forEach(([key,value])=>{const row=document.createElement("div");row.className="evidence-row";const label=document.createElement("span");label.textContent=key;const code=document.createElement("code");code.setAttribute("translate","no");code.textContent=value;row.append(label,code);grid.appendChild(row);});
  dimensions.append(dimensionsTitle,grid);
  const evidence=document.createElement("section");evidence.className="inspector-section";
  const evidenceTitle=document.createElement("h3");evidenceTitle.textContent="Primary Evidence";
  const evidencePath=document.createElement("code");evidencePath.className="evidence-path";evidencePath.setAttribute("translate","no");evidencePath.textContent=lane.evidence;
  const actions=document.createElement("div");actions.className="evidence-actions";
  const open=document.createElement("a");open.className="open-evidence";open.href=evidenceUrl;open.target="_blank";open.rel="noopener";open.textContent="Open Evidence";
  const copy=document.createElement("button");copy.className="copy-path";copy.type="button";copy.dataset.copyPath=lane.evidence;copy.textContent="Copy Path";copy.addEventListener("click",copyPath);
  actions.append(open,copy);evidence.append(evidenceTitle,evidencePath,actions);
  const footnote=document.createElement("p");footnote.className="inspector-footnote";footnote.textContent="Read-only view of the frozen qualification matrix. Native outputs and failed evidence remain unchanged.";
  inspector.append(title,summary,dimensions,evidence,footnote);
  if(reveal)setInspectorState(true);else setInspectorState(false,false);
  if(updateUrl)writeUrl(index);
}
function visibleIndexes(){
  const query=search.value.trim().toLowerCase(),visible=[];
  rows.forEach((row,index)=>{
    const lane=matrix.lanes[index],haystack=Object.values(lane).join(" ").toLowerCase();
    const show=(!query||haystack.includes(query))&&(statusFilter.value==="ALL"||lane.disposition===statusFilter.value)&&(referenceFilter.value==="ALL"||lane.reference===referenceFilter.value);
    row.hidden=!show;if(show)visible.push(index);
  });
  return visible;
}
function applyFilters(updateUrl=true){
  const visible=visibleIndexes();
  visibleCount.textContent=String(visible.length);emptyState.hidden=visible.length!==0;
  clearFiltersButton.hidden=!search.value.trim()&&statusFilter.value==="ALL"&&referenceFilter.value==="ALL";
  if(!visible.length)renderEmptyInspector("No lane matches the current filters.");
  else if(!Number.isInteger(selectedIndex)||!visible.includes(selectedIndex))renderInspector(visible[0],false,false);
  if(updateUrl)writeUrl(selectedIndex);
}
function restoreFromUrl(initial=false){
  let params;try{params=new URL(window.location.href).searchParams;}catch(error){params=new URLSearchParams();}
  search.value=params.get("q")||"";
  const statusValid=setSelectValue(statusFilter,params.get("status")||"ALL");
  const referenceValid=setSelectValue(referenceFilter,params.get("reference")||"ALL");
  const laneRaw=params.get("lane"),requested=laneRaw===null?null:Number(laneRaw);
  selectedIndex=Number.isInteger(requested)&&requested>=0&&requested<matrix.lanes.length?requested:null;
  const visible=visibleIndexes();
  visibleCount.textContent=String(visible.length);emptyState.hidden=visible.length!==0;
  clearFiltersButton.hidden=!search.value.trim()&&statusFilter.value==="ALL"&&referenceFilter.value==="ALL";
  if(!visible.length)renderEmptyInspector("No lane matches the current URL state.");
  else if(Number.isInteger(selectedIndex)&&visible.includes(selectedIndex))renderInspector(selectedIndex,initial&&laneRaw!==null&&isMobile(),false);
  else renderInspector(visible[0],false,false);
  if(!statusValid||!referenceValid||(laneRaw!==null&&selectedIndex!==requested))writeUrl(selectedIndex);
}
async function copyPath(event){
  try{await navigator.clipboard.writeText(event.currentTarget.dataset.copyPath);showToast("Evidence path copied");}
  catch(error){showToast("Copy unavailable in this browser");}
}
function showToast(message){
  const toast=document.getElementById("toast");toast.textContent=message;toast.classList.add("visible");
  window.setTimeout(()=>toast.classList.remove("visible"),1800);
}
function clearFilters(){search.value="";statusFilter.value="ALL";referenceFilter.value="ALL";applyFilters();search.focus();}
laneButtons.forEach(button=>button.addEventListener("click",()=>renderInspector(Number(button.dataset.inspectIndex),true,true,button)));
[search,statusFilter,referenceFilter].forEach(control=>control.addEventListener(control===search?"input":"change",()=>applyFilters()));
clearFiltersButton.addEventListener("click",clearFilters);
document.querySelectorAll("[data-status-filter]").forEach(button=>button.addEventListener("click",()=>{statusFilter.value=button.dataset.statusFilter;applyFilters();document.getElementById("qualification-lanes").scrollIntoView();}));
closeInspectorButton.addEventListener("click",()=>closeInspector(true));
document.addEventListener("keydown",event=>{
  const tag=(document.activeElement&&document.activeElement.tagName||"").toLowerCase();
  if(event.key==="/"&&!["input","select","textarea"].includes(tag)&&!(document.activeElement&&document.activeElement.isContentEditable)){event.preventDefault();search.focus();}
  if(event.key==="Escape"&&document.body.classList.contains("inspector-open")){event.preventDefault();closeInspector(true);}
  if(event.key==="Tab"&&isMobile()&&document.body.classList.contains("inspector-open")){
    const focusable=[...inspectorPanel.querySelectorAll('a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(node=>!node.hidden);
    if(focusable.length){
      const first=focusable[0],last=focusable[focusable.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }
  }
});
window.addEventListener("popstate",()=>restoreFromUrl(false));
window.addEventListener("hashchange",()=>restoreFromUrl(false));
window.addEventListener("resize",()=>setInspectorState(document.body.classList.contains("inspector-open"),false));
restoreFromUrl(true);
"""
