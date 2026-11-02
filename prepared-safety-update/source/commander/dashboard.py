"""Dashboard fragments injected into web_app.HTML_PAGE (nav button, view, script).

All dynamic text goes through esc()/textContent: agent names, logs and chat output are untrusted.
Real-time updates use 2s polling with an id cursor (the stdlib server in web_app has no WebSocket support).
"""

NAV_BUTTON = """
      <button id="navTabCommander" onclick="switchMainTab('commander')" class="px-3.5 py-1.5 rounded-lg text-xs font-bold transition text-rose-400 hover:text-rose-300 hover:bg-slate-800 flex items-center gap-2">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z"></path></svg>
        SUPREME AI COMMANDER
        <span id="cmdrNavBadge" class="px-1.5 rounded-full bg-rose-500/20 text-rose-300 text-[10px] font-mono border border-rose-500/30">L1</span>
      </button>
"""

VIEW = """
    <div id="commanderView" class="space-y-4 hidden">
      <div class="rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900/90 to-slate-900 border border-rose-500/30 p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-2xl font-black text-white">Supreme AI Commander</h2>
            <p id="cmdrObjective" class="text-xs text-slate-400 font-mono mt-1">No objective yet</p>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <label class="text-[11px] text-slate-400 font-bold">Autonomy</label>
            <select id="cmdrLevel" onchange="cmdrSetLevel(this.value)" class="bg-slate-800 border border-slate-600 text-xs text-white rounded px-2 py-1">
              <option value="1">L1 Observer</option><option value="2">L2 Supervisor</option>
              <option value="3">L3 Autonomous Manager</option><option value="4">L4 Full Authorized Command</option>
            </select>
            <button onclick="cmdrEstop()" id="cmdrEstopBtn" class="px-3 py-1.5 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-black">EMERGENCY STOP</button>
          </div>
        </div>
        <div id="cmdrEstopBanner" class="hidden mt-3 p-2 rounded bg-red-900/60 border border-red-500 text-red-200 text-xs font-bold">EMERGENCY STOP ENGAGED - all agents stopped, tasks cancelled. <button onclick="cmdrPost('estop/release')" class="underline ml-2">Release</button></div>
        <div id="cmdrCounts" class="grid grid-cols-2 md:grid-cols-6 gap-2 mt-4"></div>
      </div>

      <div class="flex flex-wrap gap-1" id="cmdrTabs"></div>

      <div id="cmdrPane_agents" class="cmdr-pane rounded-xl bg-slate-900/70 border border-slate-700 p-3 overflow-x-auto"></div>
      <div id="cmdrPane_tasks" class="cmdr-pane hidden rounded-xl bg-slate-900/70 border border-slate-700 p-3 overflow-x-auto"></div>
      <div id="cmdrPane_comms" class="cmdr-pane hidden rounded-xl bg-slate-900/70 border border-slate-700 p-3">
        <div id="cmdrMsgs" class="font-mono text-[11px] space-y-1 max-h-[420px] overflow-y-auto"></div>
      </div>
      <div id="cmdrPane_perms" class="cmdr-pane hidden rounded-xl bg-slate-900/70 border border-slate-700 p-3 space-y-4"></div>
      <div id="cmdrPane_perf" class="cmdr-pane hidden rounded-xl bg-slate-900/70 border border-slate-700 p-3 space-y-4"></div>
      <div id="cmdrPane_chat" class="cmdr-pane hidden rounded-xl bg-slate-900/70 border border-slate-700 p-3">
        <div id="cmdrChatLog" class="font-mono text-xs space-y-2 max-h-[380px] overflow-y-auto mb-3"></div>
        <div class="flex gap-2">
          <input id="cmdrChatInput" onkeydown="if(event.key==='Enter')cmdrChat()" placeholder="Commander, check all my AI agents and report their current activities"
                 class="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-2 text-xs text-white">
          <button onclick="cmdrChat()" class="px-4 py-2 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold">Send</button>
        </div>
        <div class="flex flex-wrap gap-2 mt-2 text-[10px]">
          <button class="cmdr-chip" data-q="Commander, check all my AI agents and report their current activities">Agent report</button>
          <button class="cmdr-chip" data-q="Commander, identify agents that are failing and investigate the problems">Investigate failures</button>
          <button class="cmdr-chip" data-q="Commander, show me which agents need additional permissions">Permission gaps</button>
          <button class="cmdr-chip" data-q="Commander, organize my existing agents into teams and prevent duplicate work">Teams &amp; duplicates</button>
          <button class="cmdr-chip" data-q="Commander, analyze the results from all my trading bots and recommend the most promising strategies">Rank strategies</button>
          <button class="cmdr-chip" data-q="Commander, assign the strategy agents to develop and backtest improved gold-trading strategies">Develop strategies</button>
        </div>
      </div>
    </div> <!-- End commanderView -->
"""

SCRIPT = r"""
<style>.cmdr-chip{padding:2px 8px;border-radius:9999px;background:#1e293b;border:1px solid #475569;color:#cbd5e1}.cmdr-chip:hover{background:#334155}
.cmdr-tab{padding:4px 12px;border-radius:8px;font-size:11px;font-weight:700;color:#94a3b8}.cmdr-tab.on{background:#e11d48;color:#fff}
.cmdr-tbl{width:100%;font-size:11px}.cmdr-tbl th{text-align:left;color:#94a3b8;padding:4px 6px}.cmdr-tbl td{padding:4px 6px;border-top:1px solid #1e293b;vertical-align:top}
.cmdr-btn{padding:1px 7px;border-radius:5px;background:#334155;color:#e2e8f0;font-size:10px;margin-right:2px}.cmdr-btn:hover{background:#475569}</style>
<script>
(function(){
  const TABS=[['agents','Agents'],['tasks','Tasks'],['comms','Communications'],['perms','Permissions & Approvals'],['perf','Performance & Optimization'],['chat','Commander Chat']];
  let state=null, msgCursor=0, timer=null, tab='agents', msgs=[];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const $=id=>document.getElementById(id);
  async function api(path,body){
    const r=await fetch('/api/commander/'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const j=await r.json(); if(!r.ok) throw new Error(j.error||r.status); return j;
  }
  async function post(path,body){ try{ const j=await api(path,body||{}); await refresh(); return j;}catch(e){ alert(e.message); } }
  window.cmdrPost=post;
  window.cmdrSetLevel=v=>post('level',{level:+v});
  window.cmdrEstop=()=>{ if(confirm('Stop ALL agents and cancel all tasks?')) post('estop'); };
  const stColor={Active:'text-emerald-400',Working:'text-sky-400',Idle:'text-slate-300',Paused:'text-amber-400',Failed:'text-red-400',Stopped:'text-slate-500'};
  function counts(){
    const c=state.counts, box=(l,v,cl)=>`<div class="rounded-lg bg-slate-800/70 p-2"><div class="text-[10px] text-slate-400">${l}</div><div class="text-xl font-black ${cl}">${v}</div></div>`;
    $('cmdrCounts').innerHTML=box('Registered',c.total,'text-white')+box('Active',c.active,'text-emerald-400')+box('Idle',c.idle,'text-slate-300')+box('Paused',c.paused,'text-amber-400')+box('Failed',c.failed,'text-red-400')+box('Running tasks',state.health.running_tasks,'text-sky-400');
    $('cmdrLevel').value=state.level; $('cmdrNavBadge').textContent='L'+state.level;
    $('cmdrEstopBanner').classList.toggle('hidden',!state.estop);
    $('cmdrObjective').textContent=state.objective?('Objective ['+state.objective.state+']: '+state.objective.text):'No objective yet - use Commander Chat';
  }
  function agents(){
    let h='<table class="cmdr-tbl"><tr><th>Agent</th><th>Team</th><th>Risk</th><th>Status</th><th>Task</th><th>Perms</th><th>Score</th><th>Controls</th></tr>';
    for(const a of state.agents){
      const ctl=a.kind==='process'?['start','pause','resume','stop'].map(o=>`<button class="cmdr-btn" data-act="${o}" data-id="${esc(a.id)}">${o}</button>`).join(''):'<span class="text-slate-500">internal</span>';
      h+=`<tr><td><b class="text-white">${esc(a.name)}</b><div class="text-slate-500 max-w-xs">${esc(a.purpose)}</div></td><td>${esc(a.team)}</td>
        <td class="${a.risk==='live'||a.risk==='unknown'?'text-red-300':'text-slate-300'}">${esc(a.risk)}</td>
        <td class="${stColor[a.status]||''} font-bold">${esc(a.status)}</td><td>${esc(a.current_task||'-')}</td>
        <td class="font-mono text-[10px] max-w-[180px]">${a.perms.map(esc).join(', ')||'-'}</td><td>${a.performance.score}</td><td>${ctl}</td></tr>`;
    }
    $('cmdrPane_agents').innerHTML=h+'</table>';
  }
  function tasks(){
    let h='<table class="cmdr-tbl"><tr><th>ID</th><th>Task</th><th>Owner</th><th>Pri</th><th>State</th><th>Deps</th><th>Try</th><th>Error</th><th></th></tr>';
    for(const t of state.tasks){
      const live=['pending','running','blocked'].includes(t.state);
      h+=`<tr><td class="font-mono">${esc(t.id)}</td><td>${esc(t.title)}</td><td>${esc(t.owner)}</td><td>${t.priority}</td><td class="font-bold ${t.state==='done'?'text-emerald-400':t.state==='failed'?'text-red-400':'text-sky-300'}">${esc(t.state)}</td>
        <td>${t.deps.map(esc).join(', ')}</td><td>${t.attempts}</td><td class="text-red-300 max-w-xs">${esc(t.error||'')}</td>
        <td>${live?`<button class="cmdr-btn" data-cancel="${esc(t.id)}">cancel</button>`:''}</td></tr>`;
    }
    $('cmdrPane_tasks').innerHTML=h+'</table>'+(state.tasks.length?'':'<p class="text-slate-500 text-xs p-2">No tasks yet.</p>');
  }
  function comms(){
    $('cmdrMsgs').innerHTML=msgs.slice(-200).map(m=>`<div><span class="text-slate-500">${new Date(m.ts*1000).toLocaleTimeString()}</span> <span class="text-rose-300">${esc(m.sender)}</span> &rarr; <span class="text-sky-300">${esc(m.recipient)}</span> <span class="text-amber-300">[${esc(m.type)}]</span> ${esc(JSON.stringify(m.body)).slice(0,300)}</div>`).join('');
  }
  async function perms(){
    const [ap,au]=await Promise.all([api('approvals?status=pending'),api('audit?n=40&prefix=')]);
    let h='<div><h3 class="text-xs font-bold text-white mb-1">Pending approvals ('+ap.approvals.length+')</h3>';
    for(const a of ap.approvals) h+=`<div class="text-xs p-2 mb-1 rounded bg-amber-900/30 border border-amber-600/40"><b>${esc(a.kind)}</b> ${esc(a.subject)} <span class="font-mono text-slate-400">${esc(JSON.stringify(a.detail))}</span>
      <button class="cmdr-btn" data-decide="1" data-id="${esc(a.id)}">approve</button><button class="cmdr-btn" data-decide="0" data-id="${esc(a.id)}">reject</button></div>`;
    h+='</div><div><h3 class="text-xs font-bold text-white mb-1">Permission matrix (click to grant/revoke; ceiling-limited; sensitive grants need approval)</h3><table class="cmdr-tbl"><tr><th>Agent</th>'+state.permissions.map(p=>`<th title="${p}" style="writing-mode:vertical-rl">${p}</th>`).join('')+'</tr>';
    for(const a of state.agents){
      h+=`<tr><td>${esc(a.name)}</td>`+state.permissions.map(p=>{const on=a.perms.includes(p),can=a.ceiling.includes(p);
        return `<td>${can?`<button class="cmdr-btn ${on?'!bg-emerald-600':''}" data-perm="${p}" data-id="${esc(a.id)}" data-on="${on?1:0}">${on?'on':'-'}</button>`:'<span class="text-slate-700">x</span>'}</td>`}).join('')+'</tr>';
    }
    h+='</table></div><div><h3 class="text-xs font-bold text-white mb-1">Security audit history</h3><div class="font-mono text-[11px] max-h-60 overflow-y-auto">'+
      au.audit.map(r=>`<div><span class="text-slate-500">${new Date(r.ts*1000).toLocaleString()}</span> <span class="text-rose-300">${esc(r.actor)}</span> ${esc(r.action)} ${esc(JSON.stringify(r.detail)).slice(0,200)}</div>`).join('')+'</div></div>'+
      `<div class="text-[11px] text-slate-400">Hard live-trading limits (code constants, not editable): symbols ${state.limits.symbols.map(esc).join(', ')}, max volume ${state.limits.max_volume}, max open positions ${state.limits.max_open_positions}, SL+TP mandatory.</div>`;
    $('cmdrPane_perms').innerHTML=h;
  }
  async function perf(){
    const p=await api('performance');
    let h='<div><h3 class="text-xs font-bold text-white mb-1">Recommendations</h3>'+p.recommendations.map(r=>`<div class="text-xs mb-1"><b class="text-amber-300">${esc(r.type)}</b> ${esc(r.agent||'')} - ${esc(r.detail)}</div>`).join('')+'</div>';
    h+='<div><h3 class="text-xs font-bold text-white mb-1">Agent performance</h3><table class="cmdr-tbl"><tr><th>Agent</th><th>Runs</th><th>Success</th><th>Avg s</th><th>Score</th></tr>'+
      Object.entries(p.performance).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${v.runs}</td><td>${v.success_rate==null?'-':Math.round(v.success_rate*100)+'%'}</td><td>${v.avg_duration==null?'-':v.avg_duration.toFixed(2)}</td><td>${v.score}</td></tr>`).join('')+'</table></div>';
    h+='<div><h3 class="text-xs font-bold text-white mb-1">Workflow versions (A/B, promote or roll back)</h3><table class="cmdr-tbl"><tr><th>Workflow</th><th>Ver</th><th>Status</th><th>Runs</th><th>OK</th><th>Note</th></tr>'+
      p.versions.workflows.map(w=>`<tr><td>${esc(w.key)}</td><td>${w.version}</td><td>${esc(w.status)}</td><td>${w.runs}</td><td>${w.successes}</td><td>${esc(w.note||'')}</td></tr>`).join('')+'</table>'+
      '<button class="cmdr-btn mt-2" data-wf="evaluate">evaluate candidates</button></div>';
    $('cmdrPane_perf').innerHTML=h;
  }
  function chatLog(role,text){
    const d=document.createElement('div'); d.className=role==='you'?'text-sky-300':'text-slate-200 whitespace-pre-wrap';
    d.textContent=(role==='you'?'> ':'')+text; const box=$('cmdrChatLog'); box.appendChild(d); box.scrollTop=box.scrollHeight;
  }
  window.cmdrChat=async function(){
    const i=$('cmdrChatInput'), t=i.value.trim(); if(!t) return; i.value=''; chatLog('you',t); chatLog('cmd','...');
    try{ const r=await api('chat',{text:t}); $('cmdrChatLog').lastChild.textContent=r.reply; }catch(e){ $('cmdrChatLog').lastChild.textContent='Error: '+e.message; }
    refresh();
  };
  function tabs(){
    $('cmdrTabs').innerHTML=TABS.map(([k,l])=>`<button class="cmdr-tab ${k===tab?'on':''}" data-tab="${k}">${l}</button>`).join('');
    document.querySelectorAll('.cmdr-pane').forEach(p=>p.classList.add('hidden')); $('cmdrPane_'+tab).classList.remove('hidden');
  }
  async function refresh(){
    try{
      state=await api('overview'); const m=await api('messages?since='+msgCursor);
      if(m.messages.length){ msgs=msgs.concat(m.messages); msgCursor=m.messages[m.messages.length-1].id; }
      counts(); tabs();
      ({agents,tasks,comms})[tab]&&({agents,tasks,comms})[tab]();
      if(tab==='perms') await perms(); if(tab==='perf') await perf();
    }catch(e){ $('cmdrObjective').textContent='Commander API error: '+e.message; }
  }
  document.addEventListener('click',e=>{
    const t=e.target; if(!(t instanceof Element)) return;
    if(t.dataset.tab){ tab=t.dataset.tab; refresh(); }
    else if(t.dataset.act) post('agent/'+t.dataset.id+'/'+t.dataset.act);
    else if(t.dataset.cancel) post('task/cancel',{id:t.dataset.cancel});
    else if(t.dataset.decide) post('approval/decide',{id:t.dataset.id,approve:t.dataset.decide==='1'});
    else if(t.dataset.perm) post(t.dataset.on==='1'?'perm/revoke':'perm/grant',{agent:t.dataset.id,perm:t.dataset.perm});
    else if(t.dataset.wf) post('workflow/evaluate',{});
    else if(t.classList.contains('cmdr-chip')){ $('cmdrChatInput').value=t.dataset.q; window.cmdrChat(); }
  });
  const orig=window.switchMainTab;
  window.switchMainTab=function(name){
    orig(name);
    const v=$('commanderView'), b=$('navTabCommander'); if(!v) return;
    v.classList.toggle('hidden',name!=='commander');
    b.className='px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-2 '+(name==='commander'?'bg-rose-600 text-white shadow':'text-rose-400 hover:text-rose-300 hover:bg-slate-800');
    clearInterval(timer); if(name==='commander'){ refresh(); timer=setInterval(refresh,2500); }
  };
})();
</script>
"""


def inject(html):
    """Return html with the Commander menu, view and script added (no-op if already present or anchors move)."""
    if "navTabCommander" in html:
        return html
    for anchor, frag, before in (("</nav>", NAV_BUTTON, True), ("</main>", VIEW, True), ("</body>", SCRIPT, True)):
        i = html.find(anchor)
        if i < 0:
            raise RuntimeError(f"commander dashboard: anchor {anchor} not found in HTML_PAGE")
        html = html[:i] + frag + html[i:]
    return html
