/* Dependency-free Streamlit component. Playback/highlighting stay in-browser. */
(() => {
  "use strict";
  const clone = value => JSON.parse(JSON.stringify(value));
  function splitCue(cues, index, position) {
    const result = clone(cues), cue = result[index];
    if (!cue || position <= 0 || position >= cue.text.length) return null;
    const left = cue.text.slice(0, position).trim(), right = cue.text.slice(position).trim();
    if (!left || !right) return null;
    result.splice(index, 1, {start:cue.start, end:null, text:left}, {start:null, end:cue.end, text:right});
    return result;
  }
  function mergeCue(cues, index, position, direction=null) {
    const cue = cues[index];
    if (!cue) return null;
    const left = direction!=="next" && position === 0 && index > 0 ? index-1 :
      direction!=="previous" && position === cue.text.length && index < cues.length-1 ? index : -1;
    if (left < 0) return null;
    const result = clone(cues), a = result[left], b = result[left+1];
    const space = /[A-Za-z0-9]$/.test(a.text.trim()) && /^[A-Za-z0-9]/.test(b.text.trim()) ? " " : "";
    result.splice(left, 2, {start:a.start, end:b.end, text:a.text.trimEnd()+space+b.text.trimStart()});
    return {cues:result, index:left};
  }
  function activeIndex(cues, time) {
    return cues.findIndex(c => Number.isFinite(c.start) && Number.isFinite(c.end) && c.start <= time && time < c.end);
  }
  function deleteCue(cues, index) {
    if(!Number.isInteger(index) || index<0 || index>=cues.length)return null;
    const result=clone(cues);result.splice(index,1);return result;
  }
  window.EditorCore = {splitCue, mergeCue, activeIndex, deleteCue};
  const $ = id => document.getElementById(id);
  let cues = [], revision = null, args = {}, selection = null, history = [], timer = null;
  let active = -1, lastSent = null, acknowledged = false, busy = false, restoringFocus = false;
  let followAudio = false, expectedScroll = null;
  const post = (type, data={}) => window.parent.postMessage({isStreamlitMessage:true, type, ...data}, "*");
  const height = () => post("streamlit:setFrameHeight", {height:Math.min(900, document.body.scrollHeight + 10)});
  function emit(action="edit") {
    clearTimeout(timer);
    const serialized = JSON.stringify(cues);
    if (action === "edit" && serialized === lastSent) return;
    lastSent = serialized;
    acknowledged = false;
    post("streamlit:setComponentValue", {dataType:"json", value:{
      action, cues:clone(cues), revision, event_id:crypto.randomUUID()
    }});
    $("message").textContent = action === "auto" ? "正在自動辨識斷句時間…" : "同步中…";
  }
  function schedule() {
    acknowledged=false;$("message").textContent="同步中，完成後再下載或儲存…";
    clearTimeout(timer); timer = setTimeout(() => emit(), 250);
  }
  function remember() { history.push(clone(cues)); if (history.length > 50) history.shift(); }
  function controls() {
    const i = selection?.index, cue = cues[i], collapsed = selection && selection.start === selection.end;
    $("split").disabled = !collapsed || !cue || !cue.text.slice(0,selection.start).trim() || !cue.text.slice(selection.start).trim();
    $("merge-prev").disabled = !collapsed || !cue || selection.start!==0 || i===0;
    $("merge-next").disabled = !collapsed || !cue || selection.start!==cue.text.length || i>=cues.length-1;
    $("delete").disabled = !cue;
    $("delete").title=cue?`刪除第 ${i+1} 句，可按復原撤回`:"先點選要刪除的句子";
    $("selected-cue").textContent=cue?`已選取第 ${i+1} 句`:"尚未選取句子";
    $("sync").disabled=busy;
    const pending = cues.reduce((n,c) => n + (c.start===null ? 1:0) + (c.end===null ? 1:0), 0);
    $("pending").textContent = pending ? `${pending} 個起訖時間待填` : "";
    $("auto").disabled = !pending || Boolean(args.disabled);
    const current=JSON.stringify(cues);
    $("undo").disabled = !history.some(snapshot=>JSON.stringify(snapshot)!==current);
    if (busy) document.querySelectorAll("button,input,textarea").forEach(el => el.disabled=true);
  }
  function capture(textarea, index) {
    selection = {index, start:textarea.selectionStart, end:textarea.selectionEnd};
    document.querySelectorAll("tbody tr").forEach((row,j) => row.classList.toggle("selected", j===index));
    controls();
  }
  function selectRow(index, cursor=null) {
    selection={index,start:cursor,end:cursor};
    document.querySelectorAll("tbody tr").forEach((row,i)=>row.classList.toggle("selected",i===index));
    controls();
  }
  function highlight() {
    const time = $("audio").currentTime || 0, next = activeIndex(cues,time);
    $("clock").textContent = `${time.toFixed(3)} 秒`;
    if (next !== active) {
      document.querySelectorAll("tbody tr").forEach((row,i) => row.classList.toggle("active",i===next));
      active = next;
    }
    followActive();
  }
  function followActive() {
    if(!followAudio || active<0)return;
    const scroller=document.querySelector(".scroll"), row=$("rows").children[active];
    if(!row)return;
    const box=scroller.getBoundingClientRect(), item=row.getBoundingClientRect();
    const header=scroller.querySelector("thead").getBoundingClientRect().height;
    if(item.top<box.top+header+2 || item.bottom>box.bottom-2){
      const target=Math.max(0,Math.min(scroller.scrollHeight-scroller.clientHeight,
        scroller.scrollTop+item.top-box.top-header-4));
      if(Math.abs(target-scroller.scrollTop)>1){expectedScroll=target;scroller.scrollTop=target;}
    }
  }
  function setFollow(enabled, manual=false) {
    followAudio=enabled;expectedScroll=null;
    $("sync").setAttribute("aria-pressed",String(enabled));
    $("sync").classList.toggle("primary",enabled);
    $("sync-state").textContent=enabled?"跟隨已啟用":manual?"手動捲動，跟隨已關閉":"跟隨已關閉";
    if(enabled)followActive();
  }
  function seekCue(index) {
    const cue=cues[index], audio=$("audio");
    if(!cue || !Number.isFinite(cue.start))return;
    const paused=audio.paused;
    audio.currentTime=Math.max(0,Math.min(args.duration,cue.start));
    if(paused)audio.pause();
    highlight();
  }
  function timeCell(cue, index, field) {
    const cell = document.createElement("td"), input = document.createElement("input");
    cell.className = "time"; input.type="number"; input.min="0"; input.max=String(args.duration); input.step="0.001";
    input.value = cue[field]===null ? "" : Number(cue[field]).toFixed(3);
    input.placeholder="待填時間"; input.className=cue[field]===null ? "pending" : "";
    input.setAttribute("aria-label", `第 ${index+1} 句${field==="start"?"開始":"結束"}時間`);
    input.dataset.field=field;
    input.addEventListener("focus", () => {remember();selectRow(index);});
    const steps = document.createElement("div"); steps.className="steps";
    function update(value) {
      cue[field] = value;
      input.classList.toggle("pending",value===null);
      steps.querySelectorAll("button").forEach(button => button.disabled=value===null);
      controls(); highlight();
    }
    input.addEventListener("input", () => {update(input.value==="" || !Number.isFinite(input.valueAsNumber) ? null : input.valueAsNumber);schedule();});
    input.addEventListener("change", () => emit());
    for (const delta of [-0.3,-0.1,0.1,0.3]) {
      const button=document.createElement("button");button.type="button";button.textContent=delta>0?`+${delta}`:String(delta);
      button.setAttribute("aria-label",`第 ${index+1} 句${field==="start"?"開始":"結束"} ${button.textContent} 秒`);
      button.disabled=cue[field]===null;
      button.addEventListener("click",() => {
        selectRow(index);
        remember(); update(Math.round(Math.max(0,Math.min(args.duration,cue[field]+delta))*1000)/1000);
        input.value=cue[field].toFixed(3);emit();
      });steps.append(button);
    }
    cell.append(input,steps);return cell;
  }
  function renderRows(focus=false) {
    const body=$("rows"); body.replaceChildren();
    cues.forEach((cue,index) => {
      const row=document.createElement("tr"), num=document.createElement("td");num.textContent=index+1;
      row.addEventListener("click",event=>{
        if(event.target.closest("input,button"))return;
        if(event.target.tagName!=="TEXTAREA"){
          selectRow(index,0);
        }
        seekCue(index);
      });
      row.append(num,timeCell(cue,index,"start"),timeCell(cue,index,"end"));
      const cell=document.createElement("td"), text=document.createElement("textarea");cell.className="text-cell";
      text.value=cue.text;text.setAttribute("aria-label",`第 ${index+1} 句字幕`);
      text.addEventListener("focus",() => {if(!restoringFocus)remember();capture(text,index);});
      for(const event of ["keyup","mouseup","select"]) text.addEventListener(event,() => capture(text,index));
      text.addEventListener("input",() => {cue.text=text.value;capture(text,index);schedule();});
      text.addEventListener("change",() => emit());
      cell.append(text);row.append(cell);body.append(row);
    });
    active=-1;highlight();controls();height();
    if(focus && selection && cues[selection.index]) {
      const text=body.children[selection.index].querySelector("textarea");
      restoringFocus=true;text.focus();text.setSelectionRange(selection.start,selection.end);restoringFocus=false;
    }
  }
  for(const id of ["split","merge-prev","merge-next","delete"]) $(id).addEventListener("mousedown",event=>event.preventDefault());
  $("delete").addEventListener("click",()=>{
    const index=selection?.index, result=deleteCue(cues,index);if(!result)return;
    remember();cues=result;
    selection=cues.length?{index:Math.min(index,cues.length-1),start:0,end:0}:null;
    renderRows(true);emit();
  });
  $("split").addEventListener("click",() => {
    if(!selection || selection.start!==selection.end) return;
    const result=splitCue(cues,selection.index,selection.start);if(!result)return;
    remember();cues=result;selection={index:selection.index+1,start:0,end:0};renderRows(true);emit();
  });
  for(const [id,direction] of [["merge-prev","previous"],["merge-next","next"]]){
    $(id).addEventListener("click",() => {
      if(!selection || selection.start!==selection.end)return;
      const result=mergeCue(cues,selection.index,selection.start,direction);if(!result)return;
      remember();cues=result.cues;selection={index:result.index,start:0,end:0};renderRows(true);emit();
    });
  }
  $("sync").addEventListener("click",()=>setFollow(!followAudio));
  const scroller=document.querySelector(".scroll");
  for(const event of ["wheel","touchmove"])scroller.addEventListener(event,()=>{
    if(followAudio)setFollow(false,true);
  },{passive:true});
  scroller.addEventListener("keydown",event=>{
    if(!event.target.closest("input,textarea") && ["ArrowUp","ArrowDown","PageUp","PageDown","Home","End"," "].includes(event.key)
       && followAudio)setFollow(false,true);
  });
  scroller.addEventListener("scroll",()=>{
    if(expectedScroll!==null && Math.abs(scroller.scrollTop-expectedScroll)<2){expectedScroll=null;return;}
    if(followAudio)setFollow(false,true);
  });
  $("undo").addEventListener("click",() => {
    const current=JSON.stringify(cues);let previous;
    while(history.length){const snapshot=history.pop();if(JSON.stringify(snapshot)!==current){previous=snapshot;break;}}
    if(previous===undefined)return;
    cues=previous;selection=null;renderRows();emit();
  });
  $("auto").addEventListener("click",() => {busy=true;controls();emit("auto");});
  for(const event of ["timeupdate","seeking","seeked","play","pause","ended"]) $("audio").addEventListener(event,highlight);
  window.addEventListener("message",event => {
    if(event.source !== window.parent || event.data.type!=="streamlit:render")return;
    args=event.data.args;
    const theme=event.data.theme;
    if(theme){document.documentElement.style.setProperty("--bg",theme.backgroundColor);document.documentElement.style.setProperty("--fg",theme.textColor);}
    if($("audio").dataset.digest!==args.digest){
      $("audio").src=args.audio_src;$("audio").dataset.digest=args.digest;
    }
    if(revision!==args.revision){
      busy=false;
      if(revision!==null) remember();
      cues=clone(args.cues);revision=args.revision;selection=null;
      lastSent=JSON.stringify(cues);renderRows();
    }
    acknowledged = JSON.stringify(args.cues)===JSON.stringify(cues);
    if(acknowledged) $("message").textContent="已同步；可下載字幕或儲存專案。";
    controls();height();
  });
  window.addEventListener("beforeunload",event=>{if(!acknowledged){event.preventDefault();event.returnValue="";}});
  controls();post("streamlit:componentReady",{apiVersion:1});height();
})();
