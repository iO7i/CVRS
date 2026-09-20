
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
