/* TokiPulse dashboard — vanilla JS, no build step */
const ICONS = {
  home:'<path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/>',
  store:'<path d="M3 9l1.5-5h15L21 9M3 9v11h18V9M3 9h18M9 20v-6h6v6"/>',
  users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.4 3.2-5.5 6.5-5.5s5.9 2.1 6.5 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.6c2.5.2 4.4 2 5 4.9"/>',
  map:'<path d="M9 4 3 6.5v13.5L9 17.5l6 2.5 6-2.5V4l-6 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
  heart:'<path d="M12 20.5s-7.5-4.6-9.2-9.6C1.6 7.3 4 4 7.4 4c2 0 3.6 1.1 4.6 2.7C13 5.1 14.6 4 16.6 4 20 4 22.4 7.3 21.2 10.9 19.5 15.9 12 20.5 12 20.5z"/>',
  landmark:'<path d="M3 21h18M5 18h14M6 18v-7M10 18v-7M14 18v-7M18 18v-7M3 9l9-6 9 6z"/>',
  all:'<rect x="3" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  refresh:'<path d="M20 11a8 8 0 0 0-14.6-4.5L4 8M4 4v4h4M4 13a8 8 0 0 0 14.6 4.5L20 16M20 20v-4h-4"/>',
  x:'<path d="M6 6l12 12M18 6 6 18"/>', plus:'<path d="M12 5v14M5 12h14"/>',
  download:'<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>', trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/>',
  star:'<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
};
const svg = (n, extra='') => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ${extra}>${ICONS[n]||''}</svg>`;
const paintIcons = (root=document) => root.querySelectorAll('i[data-i]:empty').forEach(el => el.innerHTML = svg(el.dataset.i));
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api = async (path, opts={}) => {
  const r = await fetch(path, {headers:{'Content-Type':'application/json', 'X-Admin-Token': sessionStorage.getItem('tp-admin')||''}, ...opts});
  if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || r.statusText);
  return r.json();
};
const toast = msg => { const t=$('#toast'); t.textContent=msg; t.classList.add('on'); clearTimeout(t._h); t._h=setTimeout(()=>t.classList.remove('on'),2800); };
const fmtDate = s => s ? new Date(s).toLocaleDateString('en-GB',{day:'numeric',month:'short'}) : '';
const ago = s => { if(!s) return ''; const d=(Date.now()-new Date(s))/864e5; return d<1?'today':d<2?'yesterday':`${Math.floor(d)} days ago`; };
const plural = (n, w) => `${n} ${w}${n===1?'':'s'}`;

let META = {domains:{}}, FILTER = {domain:'', territory:'', kind:'', q:'', watch:0};
const DOM_ORDER = ['HOU','ECO','PAR','DEV','TS','CUL'];
const domColor = c => `var(--c${DOM_ORDER.indexOf(c)+1})`;
const dom = c => META.domains[c] || {label:c||'—', icon:'all'};
const FEEDBACK = ['Relevant','Not relevant','Watch','Duplicate','To verify'];
const ENGINE_NAME = e => ({claude:'Claude', gemini:'Gemini'})[e] || 'heuristic';
const byEngine = e => e==='claude'||e==='gemini' ? `${ENGINE_NAME(e)} analysis` : 'Heuristic analysis';

/* ---------- theme ---------- */
function paintTheme(){
  const dark = document.documentElement.dataset.theme === 'dark';
  $('#theme').innerHTML = svg(dark ? 'sun' : 'moon');
  $('#theme').title = dark ? 'Switch to light mode' : 'Switch to dark mode';
}
$('#theme').onclick = () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next; localStorage.setItem('tp-theme', next); paintTheme();
};

/* ---------- routing ---------- */
function route(){
  const tab = (location.hash||'#radar').slice(1);
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id===`view-${tab}`));
  document.querySelectorAll('#tabs a').forEach(a => a.classList.toggle('on', a.dataset.tab===tab));
  $('#search').style.display = tab==='radar' ? '' : 'none';
  ({radar:loadRadar, sessions:loadSessions, opportunities:loadOpps, report:loadReport, sources:loadSources, admin:loadAdmin}[tab]||loadRadar)();
}
window.addEventListener('hashchange', route);

/* ---------- radar ---------- */
async function loadRadar(){
  const [stats, topics] = await Promise.all([api('/api/stats'), api('/api/topics?'+new URLSearchParams(FILTER))]);
  const cats = [['', 'All', 'all', stats.relevant], ...Object.entries(META.domains).map(([c,d]) => [c, d.label, d.icon, stats.by_domain[c]||0])];
  $('#cats').innerHTML = cats.map(([c,l,ic,n]) => `<button class="cat ${FILTER.domain===c?'on':''}" data-c="${c}"><i data-i="${ic}"></i>${esc(l)}<span class="n">${plural(n,'signal')}</span></button>`).join('');
  $('#cats').querySelectorAll('.cat').forEach(b => b.onclick = () => { FILTER.domain=b.dataset.c; loadRadar(); });
  $('#kpis').innerHTML = [
    ['accent', stats.high_priority, 'topics with priority ≥ 4'],
    ['', stats.topics, 'topics tracked'],
    ['', stats.signals_week, 'relevant signals (7 days)'],
    ['', stats.watch, 'topics on watchlist'],
    ['', stats.grants, 'open public grants'],
  ].map(([c,v,l]) => `<div class="kpi ${c}"><b>${v}</b><span>${l}</span></div>`).join('');
  $('#radar-title').textContent = FILTER.domain ? dom(FILTER.domain).label : 'Priority topics';
  const grid = $('#topics');
  if (!topics.length){
    grid.innerHTML = META.state?.running ? Array(8).fill('<div><div class="skeleton"></div></div>').join('')
      : `<div class="empty">No topics match these filters.<br><span class="small">Try another domain or run a collection.</span></div>`;
  } else grid.innerHTML = topics.map(card).join('');
  grid.querySelectorAll('.card').forEach(el => el.onclick = e => { if(!e.target.closest('.heart')) openTopic(+el.dataset.id); });
  grid.querySelectorAll('.heart').forEach(h => h.onclick = async e => {
    e.stopPropagation(); await sendFeedback('topic', +h.dataset.id, 'Watch'); h.classList.add('on'); });
  paintIcons();
}
function card(t){
  const d = dom(t.domain);
  return `<div class="card" data-id="${t.id}">
    <div class="cover c-${t.domain}">
      <span class="big">${svg(d.icon)}</span>
      <span class="prio p${t.priority}">Priority ${t.priority}</span>
      <button class="heart ${t.watch?'on':''}" data-id="${t.id}" title="Add to watchlist" aria-label="Add to watchlist">${svg('heart')}</button>
      <span class="kind">${esc(t.kind)}</span>
    </div>
    <div class="card-body">
      <div class="card-title">${esc(t.label)}</div>
      <div class="card-meta">${esc(t.territory)} · ${esc(d.label)}</div>
      <div class="card-foot"><span class="muted">${plural(t.n_signals,'signal')} · ${plural(t.n_sources,'source')} · ${ago(t.updated)}</span>
        <span class="score">${svg('star','width="14" height="14" fill="currentColor"')} ${(+t.score).toFixed(1)}</span></div>
      ${t.flags.filter(f=>f!=='Watch').map(f=>`<span class="flag">${esc(f)}</span>`).join('')}
    </div></div>`;
}
async function openTopic(id){
  const t = await api(`/api/topics/${id}`);
  const d = dom(t.domain);
  const w = META.weights || {};
  $('#drawer').innerHTML = `
    <div class="drawer-cover c-${t.domain}"><button class="icon-btn" data-close aria-label="Close">${svg('x')}</button>
      <span class="prio p${t.priority}" style="position:static">Priority ${t.priority} · score ${(+t.score).toFixed(2)}</span></div>
    <div class="drawer-in">
      <h2>${esc(t.label)}</h2>
      <div class="muted">${esc(d.label)} · ${esc(t.territory)} · <b>${esc(t.kind)}</b></div>
      <h3 class="sec">Your feedback</h3>
      <div class="chips">${FEEDBACK.map(f => `<button class="chip ${t.flags.includes(f)?'done':''}" data-f="${f}">${f}</button>`).join('')}</div>
      <h3 class="sec">Why this priority?</h3>
      ${Object.entries(t.criteria).map(([k,v]) => `<div class="crit"><span>${k}</span><div class="bar"><span style="width:${v*20}%"></span></div><b>${v}</b></div>`).join('')}
      <p class="small muted">Priority = ${Math.round((w.importance??.2)*100)}% importance + ${Math.round((w.recurrence??.25)*100)}% recurrence + ${Math.round((w.impact??.25)*100)}% impact + ${Math.round((w.urgency??.15)*100)}% urgency + ${Math.round((w.credibility??.15)*100)}% credibility/freshness. Weights are editable in Admin → Scoring.</p>
      ${t.grants.length ? `<h3 class="sec">Related public grants</h3>${t.grants.map(g => `<div class="note" style="margin-bottom:8px"><b>${esc(g.title)}</b><div class="meta">${esc(g.department)} · closes ${esc(g.end)} · <a href="${esc(g.url)}" target="_blank" rel="noopener">view</a></div></div>`).join('')}`:''}
      <h3 class="sec">Signals (${t.signals.length})</h3>
      ${t.signals.map(s => `<div class="sig"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>
        ${s.ai_summary ? `<p>${esc(s.ai_summary)}</p>` : s.summary && s.summary!==s.title ? `<p>${esc(s.summary.slice(0,220))}…</p>`:''}
        <div class="meta">${esc(s.source_name)} · ${fmtDate(s.published)} · ${esc(s.municipality||s.territory)} · importance ${s.importance} · impact ${s.impact} · urgency ${s.urgency} · ${s.analysed_by==='claude'||s.analysed_by==='gemini' ? 'analysed by '+ENGINE_NAME(s.analysed_by) : 'heuristic analysis'}</div></div>`).join('')}
    </div>`;
  $('#drawer').querySelectorAll('.chip').forEach(c => c.onclick = async () => {
    await sendFeedback('topic', id, c.dataset.f); c.classList.add('done');
    if (['Not relevant','Duplicate'].includes(c.dataset.f)) closeDrawer();
    loadRadar(); });
  $('#drawer').classList.add('on'); $('#drawer-back').classList.add('on');
  $('#drawer').querySelector('[data-close]').onclick = closeDrawer;
}
const closeDrawer = () => { $('#drawer').classList.remove('on'); $('#drawer-back').classList.remove('on'); };
$('#drawer-back').onclick = closeDrawer;
document.addEventListener('keydown', e => { if(e.key==='Escape'){ closeDrawer(); closeModal(); }});
async function sendFeedback(target, id, label){
  await api('/api/feedback', {method:'POST', body:JSON.stringify({target, target_id:id, label})});
  toast(`Feedback saved: ${label}`);
}

/* ---------- sessions ---------- */
let SESSIONS = [], CUR = null;
async function loadSessions(){
  SESSIONS = await api('/api/sessions');
  if ((!CUR || !SESSIONS.some(s=>s.id===CUR)) && SESSIONS.length) CUR = SESSIONS[0].id;
  $('#session-list').innerHTML = SESSIONS.length ? SESSIONS.map(s => `<button class="s-item ${s.id===CUR?'on':''}" data-id="${s.id}">
      <b>${esc(s.client)}</b><span class="muted small">${esc(s.municipality||s.territory)} · ${fmtDate(s.date)}</span>
      <div style="margin-top:6px">${s.example?'<span class="tag ex">Example</span> ':''}<span class="tag">${plural((s.analysis?.issues||[]).length,'issue')}</span></div></button>`).join('')
    : '<div class="empty">No sessions yet.<br>Example sessions load on first start.</div>';
  $('#session-list').querySelectorAll('.s-item').forEach(b => b.onclick = () => { CUR=+b.dataset.id; loadSessions(); });
  renderSession(SESSIONS.find(s => s.id===CUR));
}
function renderSession(s){
  const el = $('#session-detail');
  if (!s){ el.innerHTML = '<div class="empty">Select or create a session.</div>'; return; }
  const a = s.analysis || {};
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
      <div><h2>${esc(s.client)}</h2><div class="muted">${esc(s.municipality||'')} · ${esc(s.territory)} · ${fmtDate(s.date)} · ${esc(s.participants||'')}</div></div>
      <span class="engine ${s.analysed_by==='claude'||s.analysed_by==='gemini'?'ai':''}">${byEngine(s.analysed_by)}</span>
    </div>
    ${s.example?'<p class="note small" style="margin-top:14px">Fictional example session for the demo. Replace it with your real session notes.</p>':''}
    <h3 class="sec">Summary</h3><p>${esc(a.summary)}</p>
    <h3 class="sec">Issues identified</h3>
    ${(a.issues||[]).map(i => `<div class="issue"><div class="issue-head"><b>${esc(i.title)}</b><span class="prio p${i.priority}" style="position:static">Priority ${i.priority}</span></div>
      <div class="muted small">${esc(dom(i.domain).label)} · ${esc(i.summary)}</div>
      <div class="quote">“${esc(i.quote)}”</div>
      <div class="radar-link">${i.radar?.length ? `<span class="muted">Confirmed by the radar:</span>${i.radar.map(r=>`<button data-topic="${r.topic_id}">${esc(r.label.slice(0,60))} · P${r.priority}</button>`).join('')}`
        : '<span class="muted">Not yet visible in public sources: possibly a hidden local issue.</span>'}</div></div>`).join('')}
    <h3 class="sec">Recommendations</h3>
    <ul>${(a.recommendations||[]).map(r => `<li><b>${esc(r.title)}</b>: ${esc(r.text)}</li>`).join('')}</ul>
    <h3 class="sec">Opportunities for the client</h3>
    <div class="stack">${(a.client_opportunities||[]).map(o => `<div class="opp"><b>${esc(o.title)}</b><div class="meta">${esc(o.department)} · closes ${esc(o.end)}</div><div class="small" style="margin-top:6px">${esc(o.why)}</div>${o.url?`<a class="small" href="${esc(o.url)}" target="_blank" rel="noopener">View grant</a>`:''}</div>`).join('') || '<p class="muted">No matching open grant right now.</p>'}</div>
    <h3 class="sec">Opportunities for the firm</h3>
    <div class="stack">${(a.firm_opportunities||[]).map(o => `<div class="opp"><b>${esc(o.service)}</b><div class="small" style="margin-top:4px">${esc(o.why)}</div><div class="meta">${esc(o.type)}</div></div>`).join('')}</div>
    <h3 class="sec">Session notes</h3><div class="note" style="white-space:pre-wrap">${esc(s.notes)}</div>`;
  el.querySelectorAll('[data-topic]').forEach(b => b.onclick = () => openTopic(+b.dataset.topic));
}
const closeModal = () => $('#modal-back').classList.remove('on');
$('#new-session').onclick = () => { $('#modal-back').classList.add('on'); $('#session-form [name=date]').value = new Date().toISOString().slice(0,10); };
$('#modal-back').onclick = e => { if (e.target.id==='modal-back' || e.target.closest('[data-close]')) closeModal(); };
$('#session-form').onsubmit = async e => {
  e.preventDefault();
  const btn = e.target.querySelector('[type=submit]'); btn.disabled = true; btn.textContent = 'Analysing…';
  try {
    const s = await api('/api/sessions', {method:'POST', body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    CUR = s.id; e.target.reset(); closeModal(); toast('Session analysed'); location.hash = '#sessions'; loadSessions();
  } catch(err){ toast('Error: '+err.message); }
  btn.disabled = false; btn.textContent = 'Analyse session';
};

/* ---------- opportunities ---------- */
async function loadOpps(){
  const o = await api('/api/opportunities');
  $('#opp-client').innerHTML = o.client.map(x => `<div class="opp"><b>${esc(x.title)}</b><div class="small" style="margin-top:4px">${esc(x.why)}</div>
    <div class="opp-foot"><span class="meta">For ${esc(x.client)} · closes ${esc(x.end)}</span>${x.url?`<a class="small" href="${esc(x.url)}" target="_blank" rel="noopener">View</a>`:''}</div></div>`).join('') || '<p class="muted">None yet.</p>';
  $('#opp-firm').innerHTML = o.firm.map(x => `<div class="opp"><b>${esc(x.service)}</b><div class="small" style="margin-top:4px">${esc(x.why)}</div>
    <div class="opp-foot"><span class="meta">${esc(x.type)} · ${esc(x.client)}</span></div></div>`).join('') || '<p class="muted">None yet.</p>';
  $('#grants-count').textContent = `(${o.grants.length})`;
  $('#grants').innerHTML = `<tr><th>Grant</th><th>Department</th><th>Domains</th><th>Closes</th><th></th></tr>` +
    o.grants.map(g => `<tr><td>${esc(g.title)}</td><td>${esc(g.department)}</td><td>${g.domains.map(d=>esc(dom(d).label)).join(', ')||'—'}</td><td>${esc(g.end)}</td><td><a href="${esc(g.url)}" target="_blank" rel="noopener">View</a></td></tr>`).join('');
}

/* ---------- charts (inline SVG, single axis, hover tooltips via <title>) ---------- */
function hbars(data, {color = () => 'var(--brand)', width = 460, row = 28, labelW = 170} = {}){
  const max = Math.max(1, ...data.map(d => d.value)), bw = width - labelW - 44, h = data.length * row;
  return `<svg viewBox="0 0 ${width} ${h}" role="img">${data.map((d, i) => {
    const y = i * row, w = Math.max(d.value ? 4 : 0, d.value / max * bw);
    return `<g><title>${esc(d.label)}: ${d.value}</title>
      <text x="0" y="${y + row/2 + 4}">${esc(d.label.length > 26 ? d.label.slice(0, 25) + '…' : d.label)}</text>
      <rect class="bar-m" x="${labelW}" y="${y + 6}" width="${w}" height="${row - 12}" rx="4" style="fill:${color(d)}"></rect>
      <text class="val" x="${labelW + w + 6}" y="${y + row/2 + 4}">${d.value}</text></g>`; }).join('')}</svg>`;
}
function columns(data, {width = 460, height = 170, color = () => 'var(--brand)', labelEvery = 1, showValues = 'all'} = {}){
  const max = Math.max(1, ...data.map(d => d.value)), pad = 22, ch = height - pad - 16, gap = 2;
  const bw = width / data.length - gap * 2, top = Math.max(...data.map(d => d.value));
  const grid = [0.5, 1].map(f => `<line class="gridl" x1="0" x2="${width}" y1="${16 + ch - f*ch}" y2="${16 + ch - f*ch}"></line><text x="0" y="${12 + ch - f*ch}">${Math.round(max*f)}</text>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img">${grid}<line class="axisl" x1="0" x2="${width}" y1="${16+ch}" y2="${16+ch}"></line>${data.map((d, i) => {
    const x = i * (bw + gap*2) + gap, h = d.value / max * ch, y = 16 + ch - h;
    const showV = showValues === 'all' ? d.value > 0 : (d.value === top && d.value > 0) || i === data.length - 1;
    return `<g><title>${esc(d.full || d.label)}: ${d.value}</title>
      <rect class="bar-m" x="${x}" y="${y}" width="${bw}" height="${Math.max(h, d.value ? 2 : 0)}" rx="4" style="fill:${color(d)}"></rect>
      ${showV ? `<text class="val" text-anchor="middle" x="${x + bw/2}" y="${y - 4}">${d.value}</text>` : ''}
      ${i % labelEvery === 0 || i === data.length - 1 ? `<text text-anchor="middle" x="${x + bw/2}" y="${height - 2}">${esc(d.label)}</text>` : ''}</g>`; }).join('')}</svg>`;
}
const PRIO_COLORS = ['var(--p1)','var(--p2)','var(--p3)','var(--p4)','var(--p5)'];

/* ---------- report ---------- */
let REPORT = null;
async function loadReport(){
  const r = REPORT = await api('/api/report');
  const c = r.charts;
  const totalSignals = c.by_domain.reduce((a, d) => a + d.value, 0);
  const lead = [...c.by_domain].sort((a, b) => b.value - a.value)[0];
  const daily = c.daily.map(d => ({label: d.label.slice(8), full: d.label, value: d.value}));
  const week = daily.slice(-7).reduce((a, d) => a + d.value, 0), prevWeek = daily.slice(0, 7).reduce((a, d) => a + d.value, 0);
  const delta = prevWeek ? Math.round((week - prevWeek) / prevWeek * 100) : null;
  $('#report-period').textContent = `Week of ${r.period.from} to ${r.period.to} · ${byEngine(r.engine).toLowerCase()}`;
  const list = (arr, f) => arr.length ? `<ul>${arr.map(f).join('')}</ul>` : '<p class="muted">Nothing to report.</p>';
  const tl = t => `<li><b>${esc(t.label)}</b> <span class="muted">· ${esc(dom(t.domain).label)} · ${esc(t.territory)} · P${t.priority} · ${plural(t.n_signals,'signal')}</span></li>`;
  const tableRows = (arr) => arr.map(d => `<tr><td>${esc(d.label)}</td><td class="n">${d.value}</td><td class="n">${totalSignals ? Math.round(d.value / Math.max(1, arr.reduce((a,x)=>a+x.value,0)) * 100) : 0}%</td></tr>`).join('');
  $('#report').innerHTML = `
    <div class="report-cover"><div><div class="logo">toki<b>pulse</b><i></i></div><h1 style="margin-top:10px">Weekly territorial intelligence report</h1>
      <div class="muted">Basque Country · ${r.period.from} → ${r.period.to}</div></div><div class="muted small" style="text-align:right">Generated ${new Date().toLocaleString('en-GB')}<br>Analysis: ${r.engine==='heuristic' ? 'heuristic (demo mode)' : ENGINE_NAME(r.engine)}</div></div>
    <div class="pipeline">${['Identification','Research','Listening','Analysis','Conclusions','Recommendations','Results'].map(s=>`<span class="on">${s}</span>`).join('')}</div>
    <h2>Key figures</h2>
    <div class="mini-kpis"><div><b>${r.kpis.signals_week}</b>relevant signals (7 days)</div><div><b>${r.kpis.topics}</b>topics tracked</div><div><b>${r.kpis.high_priority}</b>topics priority ≥ 4</div><div><b>${r.kpis.sessions}</b>listening sessions</div></div>
    <p>This week the radar retained <b>${week}</b> relevant signals${delta === null ? '' : `, ${delta >= 0 ? 'up' : 'down'} <b>${Math.abs(delta)}%</b> on the previous week`}. ${lead ? `The most covered domain is <b>${esc(lead.label)}</b> with ${lead.value} signals (${totalSignals ? Math.round(lead.value/totalSignals*100) : 0}% of the total).` : ''} ${r.kpis.grants} public grants are currently open.</p>
    <h2>Statistics</h2>
    <div class="charts">
      <div class="chart wide"><h4>Relevant signals per day</h4><p>Last 14 days · all sources</p>${columns(daily, {width: 900, height: 180, labelEvery: 1, showValues: 'peak'})}</div>
      <div class="chart"><h4>Signals by domain</h4><p>All relevant signals</p>${hbars(c.by_domain, {color: d => domColor(d.key)})}</div>
      <div class="chart"><h4>Signals by territory</h4><p>Detected place, or source territory</p>${hbars(c.by_territory)}</div>
      <div class="chart"><h4>Topics by signal type</h4><p>How the system classified each topic</p>${hbars(c.by_kind, {labelW: 190})}</div>
      <div class="chart"><h4>Topics by priority</h4><p>P1 low → P5 critical</p>${columns(c.by_priority, {color: d => PRIO_COLORS[+d.label.slice(1) - 1]})}</div>
      <div class="chart wide"><h4>Data table</h4><p>Signals by domain and by source family</p>
        <div class="two" style="gap:20px"><table class="stat-table"><tr><th>Domain</th><th class="n">Signals</th><th class="n">Share</th></tr>${tableRows(c.by_domain)}</table>
        <table class="stat-table"><tr><th>Source family</th><th class="n">Signals</th><th class="n">Share</th></tr>${tableRows(c.by_family)}</table></div></div>
    </div>
    <h2>Conclusions</h2>${list(r.conclusions, x => `<li>${esc(x)}</li>`)}
    <h2>Top topics this week</h2>${list(r.top, tl)}
    <h2>Territorial issues to study</h2>${list(r.problems, tl)}
    <h2>Recurring concerns</h2>${list(r.recurring, tl)}
    <h2>Emerging trends</h2>${list(r.emerging, tl)}
    <h2>Watchlist</h2>${list(r.watch, tl)}
    <h2>Listening sessions (last 30 days)</h2>${list(r.sessions, s => `<li><b>${esc(s.client)}</b> <span class="muted">(${esc(s.date)})</span>: ${esc(s.summary)}</li>`)}
    <h2>Recommendations</h2>${list(r.recommendations, x => `<li><b>${esc(x.title)}</b>: ${esc(x.text)}</li>`)}
    <h2>Opportunities</h2>
    <p><b>For clients</b></p>${list(r.client_opportunities, x => `<li>${esc(x.title)} <span class="muted">for ${esc(x.client)} · closes ${esc(x.end)}</span></li>`)}
    <p><b>For the firm</b></p>${list(r.firm_opportunities, x => `<li>${esc(x.service)} <span class="muted">· ${esc(x.client)}</span></li>`)}
    <p class="hint">Method: signals are collected from the Source Radar MVP sources, classified by domain and territory, grouped into topics and scored on importance, recurrence, impact, urgency and credibility.</p>`;
}
$('#dl-pdf').onclick = () => window.print();
$('#dl-html').onclick = async () => {
  const css = await fetch('/static/styles.css').then(r => r.text());
  const html = `<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><title>TokiPulse report ${REPORT?.period.to||''}</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet"><style>${css} body{padding:30px} .report{margin:0 auto}</style></head>
<body><article class="report">${$('#report').innerHTML}</article></body></html>`;
  const a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(new Blob([html], {type:'text/html'})), download: `tokipulse-report-${REPORT?.period.to||'week'}.html`});
  a.click(); URL.revokeObjectURL(a.href); toast('Report downloaded');
};

/* ---------- sources ---------- */
async function loadSources(){
  META = {...META, ...(await api('/api/meta'))};
  const log = Object.fromEntries((META.state.log||[]).map(l => [l.source, l]));
  $('#last-run').textContent = META.state.last ? new Date(META.state.last).toLocaleString('en-GB') : '—';
  $('#sources').innerHTML = `<tr><th>ID</th><th>Source</th><th>Family</th><th>Credibility</th><th>Status</th><th>Last collection</th><th>Feed</th></tr>` +
    META.sources.map(s => { const l = log[s.name]||{}; return `<tr><td>${esc(s.id)}</td><td><b>${esc(s.name)}</b></td><td>${esc(s.family)}</td><td>${'●'.repeat(s.credibility)}<span class="muted">${'●'.repeat(5-s.credibility)}</span></td>
      <td>${s.enabled===false?'<span class="muted">Disabled</span>':'Active'}</td>
      <td>${l.status ? `<span class="dot ${l.status==='ok'?'':'err'}"></span>${l.status==='ok' ? `${l.fetched} read · ${l.new} new` : esc(l.detail)}` : '—'}</td><td><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.kind.toUpperCase())}</a></td></tr>`; }).join('');
}

/* ---------- admin ---------- */
const ADMIN_TABS = [['overview','Overview'],['sources','Sources'],['keywords','Keywords'],['weights','Scoring'],['services','Services'],['content','Content'],['activity','Activity'],['general','General']];
let ADMIN_TAB = 'overview', ADMIN_DATA = null, ADMIN_OK = null, ADMIN_RO = false;
const FAMILIES = ['Media','Citizen voice','Institutional','Expert & third sector','Official data','Public money'];
async function adminGate(){
  if (ADMIN_OK) return true;
  const r = await fetch('/api/admin/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: sessionStorage.getItem('tp-admin')||''})});
  const j = await r.json().catch(()=>({}));
  if (r.ok && j.ok) return (ADMIN_OK = true);
  if (r.ok && !j.ok) { ADMIN_RO = true; return (ADMIN_OK = true); }  // deployed without a password: read-only
  $('#admin-nav').innerHTML = '';
  $('#admin-body').innerHTML = `<form class="panel" id="admin-login" style="max-width:420px"><h3 style="margin-bottom:10px">Admin sign-in</h3>
    <label class="hint" for="admin-pw">Admin password</label><input id="admin-pw" type="password" autocomplete="current-password" style="margin:6px 0 14px">
    <button class="btn primary" type="submit">Sign in</button><p class="hint" id="admin-err"></p></form>`;
  $('#admin-login').onsubmit = async e => { e.preventDefault(); sessionStorage.setItem('tp-admin', $('#admin-pw').value);
    const t = await fetch('/api/admin/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: $('#admin-pw').value})});
    if (t.ok) { ADMIN_OK = true; loadAdmin(); } else { $('#admin-err').textContent = 'Wrong password.'; } };
  return false;
}
async function loadAdmin(){
  if (!(await adminGate())) return;
  $('#admin-nav').innerHTML = ADMIN_TABS.map(([k,l]) => `<button class="chip ${ADMIN_TAB===k?'on':''}" data-k="${k}">${l}</button>`).join('');
  $('#admin-nav').querySelectorAll('.chip').forEach(b => b.onclick = () => { ADMIN_TAB = b.dataset.k; loadAdmin(); });
  const body = $('#admin-body');
  body.innerHTML = '<div class="panel muted">Loading…</div>';
  try { await ({overview:adminOverview, sources:adminSources, keywords:adminKeywords, weights:adminWeights, services:adminServices, content:adminContent, activity:adminActivity, general:adminGeneral}[ADMIN_TAB])(body); }
  catch(e){ body.innerHTML = `<div class="panel">Error: ${esc(e.message)}</div>`; }
  if (ADMIN_RO) body.insertAdjacentHTML('afterbegin', '<div class="panel note">Read-only: set an ADMIN_PASSWORD environment variable on the host to enable changes.</div>');
  paintIcons(body);
}
const panel = (title, actions, inner, hint='') => `<div class="panel"><div class="panel-head"><h3>${title}</h3><div class="panel-actions">${actions}</div></div>${hint?`<p class="hint" style="margin:-6px 0 14px">${hint}</p>`:''}${inner}</div>`;
async function saveSetting(key, value, msg='Saved'){
  try { await api(`/api/admin/settings/${key}`, {method:'PUT', body:JSON.stringify(value)}); toast(msg); META = {...META, ...(await api('/api/meta'))}; return true; }
  catch(e){ toast('Error: '+e.message); return false; }
}
async function resetSetting(key){
  if (!confirm('Restore the default values for this section? Your changes in this section will be lost.')) return;
  await api(`/api/admin/settings/${key}/reset`, {method:'POST'}); toast('Defaults restored'); loadAdmin();
}

async function adminOverview(body){
  const o = await api('/api/admin/overview');
  body.innerHTML = `<div class="kpis" style="margin-top:0">
      <div class="kpi accent"><b>${o.sources_enabled}/${o.sources_total}</b><span>sources active</span></div>
      <div class="kpi"><b>${o.signals}</b><span>signals stored (${o.relevant} relevant)</span></div>
      <div class="kpi"><b>${o.topics}</b><span>topics</span></div>
      <div class="kpi"><b>${o.sessions}</b><span>listening sessions</span></div>
      <div class="kpi"><b>${o.feedback}</b><span>feedback entries</span></div></div>` +
    panel('Pipeline', `<button class="btn primary sm" id="a-collect"><i data-i="refresh"></i>Run collection now</button><button class="btn ghost sm" id="a-reanalyse">Re-analyse all signals</button>`,
      `<p>Last collection: <b>${o.state.last ? new Date(o.state.last).toLocaleString('en-GB') : 'never'}</b>${o.state.running ? ' · <b>running…</b>' : ''}</p>
       <p>AI engine: <b>${o.engine ? ENGINE_NAME(o.engine) : 'Heuristic, demo mode (no API key)'}</b> · change it in Admin → General</p>
       <p class="hint">Re-analyse applies your current keywords, scoring weights and clustering threshold to every stored signal. Feedback marks are kept.</p>
       <p class="hint">Database: ${esc(o.db_path)}</p>`);
  $('#a-collect').onclick = async () => { await api('/api/collect', {method:'POST'}); toast('Collection started'); setTimeout(loadAdmin, 1500); };
  $('#a-reanalyse').onclick = async e => { e.target.disabled = true; e.target.textContent = 'Re-analysing…'; const r = await api('/api/admin/reanalyse', {method:'POST'}); toast(`${r.analysed} signals re-analysed`); loadAdmin(); };
}

async function adminSources(body){
  let src = ADMIN_DATA = await api('/api/admin/settings/sources');
  const terrs = ['', ...META.territories];
  const row = (s, i) => `<tr data-i="${i}">
    <td><input type="checkbox" data-f="enabled" ${s.enabled!==false?'checked':''} aria-label="Enabled"></td>
    <td style="width:90px"><input data-f="id" value="${esc(s.id)}"></td>
    <td style="min-width:180px"><input data-f="name" value="${esc(s.name)}"></td>
    <td style="width:110px"><select data-f="kind">${['rss','telegram'].map(k=>`<option ${s.kind===k?'selected':''}>${k}</option>`).join('')}</select></td>
    <td style="width:170px"><select data-f="family">${FAMILIES.concat(FAMILIES.includes(s.family)?[]:[s.family]).map(k=>`<option ${s.family===k?'selected':''}>${esc(k)}</option>`).join('')}</select></td>
    <td style="width:80px"><input data-f="credibility" type="number" min="1" max="5" value="${s.credibility}"></td>
    <td style="width:120px"><select data-f="territory">${terrs.map(t=>`<option value="${t}" ${ (s.territory||'')===t?'selected':''}>${t||'Auto'}</option>`).join('')}</select></td>
    <td style="width:70px"><select data-f="lang">${['es','eu','fr','en'].map(k=>`<option ${s.lang===k?'selected':''}>${k}</option>`).join('')}</select></td>
    <td class="url"><input data-f="url" value="${esc(s.url)}"></td>
    <td><button class="icon-btn" data-del="${i}" title="Delete source" aria-label="Delete source"><i data-i="trash"></i></button></td></tr>`;
  const render = () => {
    body.innerHTML = panel(`Sources (${src.length})`, `<button class="btn ghost sm" id="s-add"><i data-i="plus"></i>Add source</button><button class="btn ghost sm" id="s-reset">Reset to defaults</button><button class="btn primary sm" id="s-save">Save changes</button>`,
      `<div class="table-wrap"><table class="table admin-table"><tr><th>On</th><th>ID</th><th>Name</th><th>Type</th><th>Family</th><th>Cred.</th><th>Territory</th><th>Lang</th><th>Feed URL</th><th></th></tr>${src.map(row).join('')}</table></div>`,
      'RSS/Atom feeds or public Telegram channels (https://t.me/s/&lt;channel&gt;). Credibility 1–5 feeds the priority score. Disabled sources are skipped at the next collection.');
    paintIcons(body);
    body.querySelectorAll('[data-del]').forEach(b => b.onclick = () => { sync(); src.splice(+b.dataset.del, 1); render(); });
    $('#s-add').onclick = () => { sync(); src.push({id:`S${String(src.length+1).padStart(2,'0')}-new`, name:'', kind:'rss', family:'Media', credibility:3, territory:null, lang:'es', url:'', enabled:true}); render(); body.querySelector('tr:last-child [data-f=name]').focus(); };
    $('#s-reset').onclick = () => resetSetting('sources');
    $('#s-save').onclick = async () => { sync(); if (await saveSetting('sources', src, 'Sources saved')) render(); };
  };
  const sync = () => body.querySelectorAll('tr[data-i]').forEach(tr => {
    const s = src[+tr.dataset.i];
    tr.querySelectorAll('[data-f]').forEach(el => { const f = el.dataset.f; s[f] = el.type==='checkbox' ? el.checked : f==='credibility' ? +el.value : f==='territory' ? (el.value||null) : el.value.trim(); });
  });
  render();
}

async function adminKeywords(body){
  const kw = await api('/api/admin/settings/keywords');
  body.innerHTML = panel('Keywords by domain', `<button class="btn ghost sm" id="k-reset">Reset to defaults</button><button class="btn primary sm" id="k-save">Save</button>`,
    `<div class="kw-grid">${Object.entries(META.domains).map(([c,d]) => `<label>${esc(d.label)} <span class="muted small" style="font-weight:400">${(kw[c]||'').split(',').filter(x=>x.trim()).length} terms</span><textarea rows="5" data-c="${c}">${esc(kw[c]||'')}</textarea></label>`).join('')}</div>`,
    'Comma-separated, any language (ES / EU / FR / EN). Words match at the start of a word, so a stem like "inmobiliari" also matches "inmobiliaria". With Claude enabled, keywords only pre-filter; Claude decides the domain.');
  $('#k-reset').onclick = () => resetSetting('keywords');
  $('#k-save').onclick = async () => {
    const v = {}; body.querySelectorAll('textarea[data-c]').forEach(t => v[t.dataset.c] = t.value.split(',').map(x=>x.trim()).filter(Boolean).join(', '));
    if (await saveSetting('keywords', v, 'Keywords saved') && confirm('Re-analyse all stored signals now with the new keywords?')) {
      const r = await api('/api/admin/reanalyse', {method:'POST'}); toast(`${r.analysed} signals re-analysed`); }
    loadAdmin();
  };
}

async function adminWeights(body){
  const w = await api('/api/admin/settings/weights');
  const labels = {importance:'Importance for the territory', recurrence:'Recurrence (distinct sources)', impact:'Impact on residents', urgency:'Urgency', credibility:'Credibility & freshness'};
  body.innerHTML = panel('Priority scoring weights', `<button class="btn ghost sm" id="w-reset">Reset to defaults</button><button class="btn primary sm" id="w-save">Save</button>`,
    Object.entries(labels).map(([k,l]) => `<div class="weight-row"><span>${l}</span><input type="range" min="0" max="60" step="5" data-k="${k}" value="${Math.round((w[k]||0)*100)}"><b data-v="${k}">${Math.round((w[k]||0)*100)}%</b></div>`).join('') +
    `<div class="weight-row"><span><b>Total</b></span><span></span><span class="total" id="w-total"></span></div>`,
    'Priority (1–5) = Σ weight × criterion score. Weights must add up to 100%. Topics are re-scored immediately on save.');
  const upd = () => { let t = 0; body.querySelectorAll('[data-k]').forEach(r => { t += +r.value; body.querySelector(`[data-v=${r.dataset.k}]`).textContent = r.value + '%'; });
    $('#w-total').textContent = t + '%'; $('#w-total').classList.toggle('bad', t !== 100); return t; };
  body.querySelectorAll('[data-k]').forEach(r => r.oninput = upd); upd();
  $('#w-reset').onclick = () => resetSetting('weights');
  $('#w-save').onclick = async () => { if (upd() !== 100) return toast('Weights must add up to 100%');
    const v = {}; body.querySelectorAll('[data-k]').forEach(r => v[r.dataset.k] = +r.value / 100); await saveSetting('weights', v, 'Weights saved · topics re-scored'); };
}

async function adminServices(body){
  let sv = await api('/api/admin/settings/services');
  const render = () => {
    body.innerHTML = panel(`Consulting services catalogue (${sv.length})`, `<button class="btn ghost sm" id="v-add"><i data-i="plus"></i>Add service</button><button class="btn ghost sm" id="v-reset">Reset to defaults</button><button class="btn primary sm" id="v-save">Save</button>`,
      `<div class="svc-grid">${sv.map((s,i) => `<div class="svc" data-i="${i}">
        <div style="display:flex;gap:8px"><input data-f="name" value="${esc(s.name)}" placeholder="Service name"><button class="icon-btn" data-del="${i}" title="Delete service" aria-label="Delete service"><i data-i="trash"></i></button></div>
        <textarea data-f="desc" rows="2" placeholder="Short description">${esc(s.desc||'')}</textarea>
        <div class="dom-checks">${Object.entries(META.domains).map(([c,d]) => `<label><input type="checkbox" data-d="${c}" ${s.domains.includes(c)?'checked':''}>${esc(d.label)}</label>`).join('')}</div></div>`).join('')}</div>`,
      'The firm\'s real offer. Listening-session analysis only proposes services from this list, matched on the domains you tick.');
    paintIcons(body);
    body.querySelectorAll('[data-del]').forEach(b => b.onclick = () => { sync(); sv.splice(+b.dataset.del, 1); render(); });
    $('#v-add').onclick = () => { sync(); sv.push({id:`SV${Date.now()%100000}`, name:'', desc:'', domains:[]}); render(); };
    $('#v-reset').onclick = () => resetSetting('services');
    $('#v-save').onclick = async () => { sync(); if (await saveSetting('services', sv, 'Services saved')) render(); };
  };
  const sync = () => body.querySelectorAll('.svc').forEach(el => { const s = sv[+el.dataset.i];
    s.name = el.querySelector('[data-f=name]').value.trim(); s.desc = el.querySelector('[data-f=desc]').value.trim();
    s.domains = [...el.querySelectorAll('[data-d]:checked')].map(c => c.dataset.d); });
  render();
}

async function adminContent(body){
  const [sessions, topics] = await Promise.all([api('/api/sessions'), api('/api/topics?limit=150')]);
  body.innerHTML = panel(`Listening sessions (${sessions.length})`, '',
      `<div class="table-wrap"><table class="table admin-table"><tr><th>Client</th><th>Territory</th><th>Date</th><th>Issues</th><th>Engine</th><th></th></tr>${sessions.map(s => `<tr><td><b>${esc(s.client)}</b>${s.example?' <span class="tag ex">Example</span>':''}</td><td>${esc(s.territory)}</td><td>${esc(s.date)}</td><td>${(s.analysis?.issues||[]).length}</td><td>${esc(s.analysed_by)}</td>
        <td style="white-space:nowrap"><button class="btn ghost sm" data-re="${s.id}">Re-analyse</button> <button class="btn danger sm" data-ds="${s.id}">Delete</button></td></tr>`).join('')}</table></div>`) +
    panel(`Topics (${topics.length} shown)`, '',
      `<div class="table-wrap" style="max-height:520px"><table class="table admin-table"><tr><th>Topic</th><th>Domain</th><th>Territory</th><th>Type</th><th>P</th><th>Signals</th><th></th></tr>${topics.map(t => `<tr><td>${esc(t.label)}</td><td>${esc(dom(t.domain).label)}</td><td>${esc(t.territory)}</td><td>${esc(t.kind)}</td><td>${t.priority}</td><td>${t.n_signals}</td>
        <td><button class="btn danger sm" data-dt="${t.id}">Remove</button></td></tr>`).join('')}</table></div>`, 'Removing a topic hides its signals from the radar and reports.');
  body.querySelectorAll('[data-ds]').forEach(b => b.onclick = async () => { if (!confirm('Delete this listening session permanently?')) return; await api(`/api/admin/sessions/${b.dataset.ds}`, {method:'DELETE'}); toast('Session deleted'); loadAdmin(); });
  body.querySelectorAll('[data-re]').forEach(b => b.onclick = async () => { b.disabled = true; b.textContent = '…'; await api(`/api/sessions/${b.dataset.re}/reanalyse`, {method:'POST'}); toast('Session re-analysed'); loadAdmin(); });
  body.querySelectorAll('[data-dt]').forEach(b => b.onclick = async () => { await api(`/api/admin/topics/${b.dataset.dt}`, {method:'DELETE'}); b.closest('tr').remove(); toast('Topic removed'); });
}

async function adminActivity(body){
  const a = await api('/api/admin/activity');
  body.innerHTML = panel(`Analyst feedback (${a.feedback.length})`, '',
      a.feedback.length ? `<div class="table-wrap" style="max-height:420px"><table class="table admin-table"><tr><th>When</th><th>Label</th><th>On</th><th>Item</th><th></th></tr>${a.feedback.map(f => `<tr><td>${new Date(f.created).toLocaleString('en-GB')}</td><td><b>${esc(f.label)}</b></td><td>${esc(f.target)}</td><td>${esc(f.target_label)}</td><td><button class="btn danger sm" data-df="${f.id}">Undo</button></td></tr>`).join('')}</table></div>` : '<p class="muted">No feedback yet. Use the buttons on a topic in the Radar.</p>',
      'Feedback adjusts source credibility, feeds Claude with examples, and updates the watchlist. Undo removes its effect on scoring.') +
    panel(`Collection runs (${a.runs.length})`, '',
      `<div class="table-wrap" style="max-height:420px"><table class="table admin-table"><tr><th>Finished</th><th>New signals</th><th>Errors</th><th>Details</th></tr>${a.runs.map(r => { const errs = r.log.filter(l => l.status==='error');
        return `<tr><td>${new Date(r.finished).toLocaleString('en-GB')}</td><td>${r.log.reduce((s,l)=>s+(l.new||0),0)}</td><td>${errs.length}</td><td class="small">${errs.map(e=>esc(e.source+': '+e.detail)).join('<br>')||'—'}</td></tr>`; }).join('')}</table></div>`);
  body.querySelectorAll('[data-df]').forEach(b => b.onclick = async () => { await api(`/api/admin/feedback/${b.dataset.df}`, {method:'DELETE'}); toast('Feedback removed'); loadAdmin(); });
}

async function adminGeneral(body){
  const g = await api('/api/admin/settings/general');
  body.innerHTML = panel('General settings', `<button class="btn ghost sm" id="g-reset">Reset to defaults</button><button class="btn primary sm" id="g-save">Save</button>`,
    `<div class="form-rows">
      <label>Organisation name<input data-f="org_name" value="${esc(g.org_name)}"></label>
      <label>Automatic collection<select data-f="auto_collect_hours">${[[0,'Manual only'],[6,'Every 6 hours'],[12,'Every 12 hours'],[24,'Daily']].map(([v,l])=>`<option value="${v}" ${+g.auto_collect_hours===v?'selected':''}>${l}</option>`).join('')}</select></label>
      <label>Ignore items older than (days)<input data-f="max_age_days" type="number" min="1" max="365" value="${g.max_age_days}"></label>
      <label>Topic clustering threshold<input data-f="cluster_threshold" type="number" min="0.05" max="0.9" step="0.01" value="${g.cluster_threshold}"></label>
      <label>AI engine<select data-f="ai_engine" data-s>${[['auto','Auto (Claude, else Gemini, else heuristic)'],['claude','Claude'],['gemini','Gemini (free tier, testing)'],['heuristic','Heuristic only (no AI)']].map(([v,l])=>`<option value="${v}" ${g.ai_engine===v?'selected':''}>${l}</option>`).join('')}</select></label>
      <label>Gemini model<input data-f="gemini_model" value="${esc(g.gemini_model||'gemini-2.5-flash')}"></label>
    </div><p class="hint">Lower clustering threshold = more articles grouped into the same topic. Automatic collection runs while the server is running.</p>`) +
    panel('AI engines', '', `<p>Active engine: <b>${META.engine ? ENGINE_NAME(META.engine) : 'none, heuristic demo mode'}</b></p>
      <table class="stat-table"><tr><th>Engine</th><th>Key on server</th><th>Use</th></tr>
        <tr><td><b>Claude</b></td><td>${META.keys?.claude ? '✅ detected' : '— not set'}</td><td>Production: claude-haiku-5-5 (triage), claude-opus-5-5 (sessions)</td></tr>
        <tr><td><b>Gemini</b></td><td>${META.keys?.gemini ? '✅ detected' : '— not set'}</td><td>Testing on Google AI Studio's free tier (rate-limited; prompts may be used by Google, so test with example data only)</td></tr></table>
      <p class="hint">For security, keys are never stored in the app. Set them as environment variables on the server, then restart:<br><code>$env:GEMINI_API_KEY = "…"</code> &nbsp; <code>$env:ANTHROPIC_API_KEY = "sk-ant-…"</code></p>
      <p class="hint">After switching engine, use Admin → Overview → “Re-analyse all signals” and re-analyse sessions in Admin → Content.</p>`);
  $('#g-reset').onclick = () => resetSetting('general');
  $('#g-save').onclick = async () => { const v = {}; body.querySelectorAll('[data-f]').forEach(el => v[el.dataset.f] = el.type==='number' || (el.tagName==='SELECT' && !('s' in el.dataset)) ? +el.value : el.value.trim()); if (await saveSetting('general', v, 'Settings saved')) { paintEngine(); loadAdmin(); } };
}

/* ---------- search & refresh ---------- */
$('#search').onsubmit = e => { e.preventDefault(); FILTER.q=$('#q').value.trim(); FILTER.territory=$('#f-terr').value; FILTER.kind=$('#f-kind').value; loadRadar(); };
['#f-terr','#f-kind'].forEach(s => $(s).onchange = () => $('#search').requestSubmit());
$('#f-watch').onchange = e => { FILTER.watch = e.target.checked ? 1 : 0; loadRadar(); };
$('#refresh').onclick = async () => {
  const b = $('#refresh'); b.disabled = true; b.classList.add('spin'); toast('Collection started…');
  await api('/api/collect', {method:'POST'});
  const poll = setInterval(async () => {
    META = {...META, ...(await api('/api/meta'))};
    if (!META.state.running){ clearInterval(poll); b.disabled=false; b.classList.remove('spin'); toast('Collection finished'); route(); }
  }, 2500);
};

function paintEngine(){
  $('#engine').textContent = META.engine ? `AI: ${ENGINE_NAME(META.engine)}` : 'Demo mode · no AI key';
  $('#engine').classList.toggle('ai', !!META.engine);
  $('#engine').title = META.engine==='claude' ? 'Claude (Haiku 5.5 triage, Opus 5.5 sessions)' : META.engine==='gemini' ? 'Gemini (free tier, testing)' : 'Set GEMINI_API_KEY or ANTHROPIC_API_KEY on the server';
}

/* ---------- boot ---------- */
(async function boot(){
  paintIcons(); paintTheme();
  META = await api('/api/meta');
  META.weights = await api('/api/admin/settings/weights');
  paintEngine();
  const opts = META.territories.map(t => `<option>${t}</option>`).join('');
  $('#f-terr').innerHTML += opts; $('#session-form [name=territory]').innerHTML = opts;
  route();
  if (META.state.running) { const p = setInterval(async()=>{ META = {...META, ...(await api('/api/meta'))}; if(!META.state.running){clearInterval(p); route();} }, 3000); }
})();
