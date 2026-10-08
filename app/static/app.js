(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  const DIFF = { Easy: 'bg-emerald-900 text-emerald-300', Medium: 'bg-amber-900 text-amber-300', Hard: 'bg-orange-900 text-orange-300', Expert: 'bg-red-900 text-red-300' };
  let levels = [], current = 1, cfg = {}, renderToken = 0;

  async function api(path, method = 'GET', body) {
    const r = await fetch(path, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
    let data = {};
    try { data = await r.json(); } catch (e) { /* ignore */ }
    if (!r.ok) throw new Error(data.detail || ('Request failed (' + r.status + ')'));
    return data;
  }

  function toast(msg, ok = true) {
    const t = el('div', 'rounded px-4 py-2 shadow text-sm ' + (ok ? 'bg-emerald-600' : 'bg-red-600'), msg);
    $('#toasts').appendChild(t);
    setTimeout(() => t.remove(), 3500);
  }

  function openDrawer(open) {
    $('#sidebar').classList.toggle('-translate-x-full', !open);
    $('#backdrop').classList.toggle('hidden', !open);
  }

  async function load() {
    const d = await api('/api/levels');
    levels = d.levels;
    $('#progress').textContent = d.solved + ' / ' + levels.length + ' solved';
    $('#bar').style.width = (d.solved / levels.length * 100) + '%';
    if (document.activeElement !== $('#team')) $('#team').value = d.team || '';
    renderNav();
  }

  function renderNav() {
    const nav = $('#nav'); nav.textContent = '';
    levels.forEach((lv) => {
      const b = el('button', 'w-full text-left rounded px-3 py-2 flex items-center gap-2 hover:bg-slate-800 ' + (lv.id === current ? 'bg-slate-800 ring-1 ring-indigo-500' : ''));
      b.appendChild(el('span', 'w-5 text-center', lv.solved ? '✓' : String(lv.id)));
      b.lastChild.className += lv.solved ? ' text-emerald-400' : ' text-slate-400';
      const mid = el('span', 'flex-1 min-w-0');
      mid.appendChild(el('span', 'block text-sm truncate', lv.title));
      mid.appendChild(el('span', 'block text-xs text-slate-500 truncate', lv.category));
      b.appendChild(mid);
      b.appendChild(el('span', 'text-[10px] rounded px-1.5 py-0.5 ' + DIFF[lv.difficulty], lv.difficulty));
      b.onclick = () => { current = lv.id; renderNav(); renderLevel(); openDrawer(false); };
      nav.appendChild(b);
    });
  }

  function bubble(box, role, text) {
    const wrap = el('div', 'flex ' + (role === 'user' ? 'justify-end' : role === 'event' ? 'justify-center' : 'justify-start'));
    const cls = { user: 'bg-indigo-600 text-white', assistant: 'bg-slate-800', event: 'bg-slate-900 border border-dashed border-slate-600 text-amber-300 text-xs font-mono' }[role];
    wrap.appendChild(el('div', 'max-w-[85%] rounded-lg px-3 py-2 whitespace-pre-wrap break-words text-sm ' + cls, role === 'event' ? '⚙ ' + text : text));
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
  }

  function panel(cls) { return el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-2 ' + (cls || '')); }

  // Level-specific puzzle panels ------------------------------------------------------------
  async function cipherPanel(lv) {
    const p = await api('/api/levels/' + lv.id + '/puzzle');
    const box = panel();
    box.appendChild(el('p', 'text-sm font-semibold', '📡 Intercepted transmission'));
    const blob = el('pre', 'rounded bg-slate-950 p-3 text-xs font-mono whitespace-pre-wrap break-all text-emerald-300', p.blob);
    box.appendChild(blob);
    box.appendChild(el('p', 'text-xs text-slate-400', 'Layers used (in no particular order):'));
    const chips = el('div', 'flex flex-wrap gap-2');
    p.layers.forEach((l) => chips.appendChild(el('span', 'text-xs rounded-full bg-slate-800 border border-slate-700 px-2 py-1', l)));
    box.appendChild(chips);
    const row = el('div', 'flex gap-2');
    const copy = el('button', 'rounded bg-slate-800 hover:bg-slate-700 px-3 py-1 text-sm', 'Copy to toolbox');
    copy.onclick = () => { $('#tb-in').value = p.blob; tb(true); };
    row.appendChild(copy);
    box.appendChild(row);
    return box;
  }

  function widgetPanel(lv, p) {
    const box = panel();
    box.appendChild(el('p', 'text-sm font-semibold', '🧩 The widget'));
    box.appendChild(el('p', 'text-sm text-slate-300', 'This is the script ShopCo ships to every visitor. Read it like a developer would.'));
    const a = el('a', 'inline-block rounded bg-slate-800 hover:bg-slate-700 px-3 py-1 text-sm text-indigo-300', 'Open widget script ↗');
    a.href = p.script_url; a.target = '_blank'; a.rel = 'noopener';
    box.appendChild(a);
    box.appendChild(el('p', 'text-xs text-slate-500', 'Tip: found something encoded? Use the Decoder Toolbox. To call an endpoint, edit the URL in your address bar.'));
    return box;
  }

  function datasetPanel(lv, p) {
    const box = panel();
    const top = el('div', 'flex flex-wrap items-center gap-2');
    top.appendChild(el('p', 'text-sm font-semibold flex-1', '🗂 Training data: ' + p.rows.length + ' product reviews'));
    const dl = el('a', 'rounded bg-slate-800 hover:bg-slate-700 px-3 py-1 text-sm text-indigo-300', 'Download CSV ⬇');
    dl.href = p.csv_url; dl.setAttribute('download', 'reviews.csv');
    top.appendChild(dl);
    box.appendChild(top);
    const wrap = el('div', 'max-h-72 overflow-auto rounded border border-slate-800');
    const t = el('table', 'w-full text-xs');
    p.rows.forEach((r, i) => {
      const tr = el('tr', 'border-t border-slate-800');
      tr.appendChild(el('td', 'px-2 py-1 text-slate-500', String(i + 1)));
      tr.appendChild(el('td', 'px-2 py-1', r.text));
      tr.appendChild(el('td', 'px-2 py-1 font-semibold ' + (r.label === 'positive' ? 'text-emerald-400' : 'text-red-400'), r.label));
      t.appendChild(tr);
    });
    wrap.appendChild(t); box.appendChild(wrap);
    return box;
  }

  async function renderLevel() {
    const token = ++renderToken;
    const lv = levels.find((l) => l.id === current);
    $('#mobile-title').textContent = lv.id + '. ' + lv.title;
    const c = $('#content');
    const root = el('div', 'max-w-3xl mx-auto space-y-4');
    const kind = lv.kind;

    const head = el('div', 'flex flex-wrap items-center gap-2');
    head.appendChild(el('h2', 'text-xl font-bold', 'Level ' + lv.id + ': ' + lv.title));
    head.appendChild(el('span', 'text-xs rounded px-2 py-0.5 ' + DIFF[lv.difficulty], lv.difficulty));
    head.appendChild(el('span', 'text-xs rounded px-2 py-0.5 bg-slate-800 text-slate-300', lv.category));
    root.appendChild(head);

    const lore = el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-2');
    lore.appendChild(el('p', 'text-slate-300 italic', lv.lore));
    const obj = el('p', 'text-sm'); obj.appendChild(el('strong', 'text-indigo-300', 'Objective: ')); obj.appendChild(document.createTextNode(lv.objective));
    lore.appendChild(obj);
    const chips = el('div', 'flex flex-wrap gap-2');
    chips.appendChild(el('span', 'text-xs text-slate-400 self-center', 'Defenses:'));
    lv.defenses.forEach((d) => chips.appendChild(el('span', 'text-xs rounded-full bg-slate-800 border border-slate-700 px-2 py-1', d)));
    lore.appendChild(chips);
    root.appendChild(lore);

    // Hints
    const hintBox = el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-2');
    const hintList = el('div', 'space-y-2');
    const hintBtn = el('button', 'text-sm rounded bg-slate-800 hover:bg-slate-700 px-3 py-1');
    const addHint = (t, i) => hintList.appendChild(el('p', 'text-sm text-amber-200', '💡 Hint ' + (i + 1) + ': ' + t));
    lv.hints.forEach(addHint);
    const updHintBtn = () => { const left = lv.hints_total - lv.hints.length; hintBtn.textContent = left ? 'Reveal next hint (' + left + ' left)' : 'No more hints'; hintBtn.disabled = !left; hintBtn.classList.toggle('opacity-50', !left); };
    hintBtn.onclick = async () => { try { const h = await api('/api/levels/' + lv.id + '/hint', 'POST'); lv.hints.push(h.hint); addHint(h.hint, h.n - 1); updHintBtn(); } catch (e) { toast(e.message, false); } };
    updHintBtn();
    hintBox.appendChild(hintBtn); hintBox.appendChild(hintList);
    root.appendChild(hintBox);

    // Level-specific panel
    let docArea = null, chat = null;
    try {
      if (kind === 'cipher') root.appendChild(await cipherPanel(lv));
      else if (kind === 'widget') root.appendChild(widgetPanel(lv, await api('/api/levels/' + lv.id + '/puzzle')));
      else if (kind === 'dataset') root.appendChild(datasetPanel(lv, await api('/api/levels/' + lv.id + '/puzzle')));
      else if (kind === 'riddle') await api('/api/levels/' + lv.id + '/puzzle');  // creates the first riddle
    } catch (e) { toast(e.message, false); }
    if (token !== renderToken) return;

    if (kind === 'document') {
      const box = panel();
      box.appendChild(el('label', 'text-sm font-semibold', 'Paste an article to summarize'));
      docArea = el('textarea', 'w-full rounded bg-slate-800 p-2 text-sm'); docArea.rows = 6; docArea.maxLength = cfg.max_doc_chars || 4000;
      docArea.placeholder = 'Write or paste a short article…';
      const row = el('div', 'flex gap-2 items-center');
      const up = el('input', 'text-xs'); up.type = 'file'; up.accept = '.txt,text/plain';
      up.onchange = () => { const f = up.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { docArea.value = String(r.result).slice(0, docArea.maxLength); }; r.readAsText(f); };
      row.appendChild(up);
      box.appendChild(docArea); box.appendChild(row);
      root.appendChild(box);
    }

    // Conversation area for chat, document and riddle levels; dataset gets an answer box instead.
    const talks = ['chat', 'document', 'riddle', 'dataset'].includes(kind);
    let send = null, input = null;
    if (talks) {
      chat = el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-3 overflow-y-auto space-y-2 ' + (kind === 'dataset' ? 'h-40' : 'h-80'));
      root.appendChild(chat);
      try {
        const hist = (await api('/api/levels/' + lv.id + '/history')).history;
        if (token !== renderToken) return;  // a newer render started; drop this stale one
        hist.forEach((h) => bubble(chat, h.role, h.content));
      } catch (e) { /* ignore */ }
      if (token !== renderToken) return;

      const form = el('form', 'flex gap-2');
      input = el('input', 'flex-1 min-w-0 rounded bg-slate-800 px-3 py-2 text-sm'); input.maxLength = kind === 'riddle' || kind === 'dataset' ? 200 : (cfg.max_message_chars || 600);
      input.placeholder = { chat: 'Type your prompt…', riddle: 'Your answer…', dataset: 'The trigger token you found…', document: 'Click “Summarize” to send the document →' }[kind];
      if (kind === 'document') input.disabled = true;
      send = el('button', 'rounded bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-sm', kind === 'document' ? 'Summarize' : kind === 'chat' ? 'Send' : 'Answer');
      const reset = el('button', 'rounded bg-slate-800 hover:bg-slate-700 px-3 py-2 text-sm', 'Reset');
      reset.type = 'button';
      form.appendChild(input); form.appendChild(send); form.appendChild(reset);
      root.appendChild(form);

      form.onsubmit = async (ev) => {
        ev.preventDefault();
        const text = kind === 'document' ? docArea.value : input.value;
        if (!text.trim()) return;
        send.disabled = true;
        bubble(chat, 'user', kind === 'document' ? '📄 Document submitted (' + text.length + ' chars)' : text);
        if (kind !== 'document') input.value = '';
        try {
          const path = '/api/levels/' + lv.id + '/';
          const d = kind === 'document' ? await api(path + 'summarize', 'POST', { document: text })
            : (kind === 'riddle' || kind === 'dataset') ? await api(path + 'answer', 'POST', { answer: text })
            : await api(path + 'chat', 'POST', { message: text });
          (d.events || []).forEach((e) => bubble(chat, 'event', e));
          bubble(chat, 'assistant', d.reply);
        } catch (e) { toast(e.message, false); }
        send.disabled = false; input.focus();
      };
      reset.onclick = async () => { await api('/api/levels/' + lv.id + '/reset', 'POST'); renderLevel(); toast('Reset'); };
    }
    c.textContent = ''; c.appendChild(root);

    // Flag submit
    const sub = el('form', 'flex gap-2');
    const flag = el('input', 'flex-1 min-w-0 rounded bg-slate-800 px-3 py-2 text-sm font-mono'); flag.placeholder = 'FLAG{…}';
    sub.appendChild(flag); sub.appendChild(el('button', 'rounded bg-emerald-600 hover:bg-emerald-500 px-4 py-2 text-sm', 'Submit Flag'));
    root.appendChild(sub);
    const debrief = el('div', 'rounded-lg border border-emerald-700 bg-emerald-950 p-4 text-sm space-y-1');
    const showDebrief = (t) => { debrief.textContent = ''; debrief.appendChild(el('strong', 'text-emerald-300', '✅ Debrief: ')); debrief.appendChild(document.createTextNode(t)); root.appendChild(debrief); };
    if (lv.debrief) showDebrief(lv.debrief);
    sub.onsubmit = async (ev) => {
      ev.preventDefault();
      try {
        const r = await api('/api/levels/' + lv.id + '/submit', 'POST', { flag: flag.value });
        if (r.correct) { toast('🎉 Correct! Level solved.'); lv.solved = true; showDebrief(r.debrief); await load(); } else toast('Wrong flag, keep trying.', false);
      } catch (e) { toast(e.message, false); }
    };
  }

  // Decoder toolbox
  const b64d = (s) => { try { return decodeURIComponent(escape(atob(s.trim()))); } catch (e) { return '⚠ not valid base64'; } };
  const TOOLS = {
    'Base64 decode': b64d,
    'Base64 encode': (s) => btoa(unescape(encodeURIComponent(s))),
    'ROT13': (s) => s.replace(/[a-z]/gi, (c) => String.fromCharCode((c <= 'Z' ? 90 : 122) >= (c = c.charCodeAt(0) + 13) ? c : c - 26)),
    'Hex → text': (s) => { const h = s.replace(/[^0-9a-f]/gi, ''); return (h.match(/../g) || []).map((x) => String.fromCharCode(parseInt(x, 16))).join(''); },
    'Text → hex': (s) => Array.from(s).map((c) => c.charCodeAt(0).toString(16).padStart(2, '0')).join(''),
    'ASCII codes → text': (s) => (s.match(/\d+/g) || []).map((n) => String.fromCharCode(+n)).join(''),
    'Caesar decode (shift)': (s) => { const n = parseInt($('#tb-shift').value || '0', 10); return s.replace(/[a-z]/gi, (ch) => { const base = ch <= 'Z' ? 65 : 97; return String.fromCharCode(((ch.charCodeAt(0) - base - n) % 26 + 26) % 26 + base); }); },
    'Reverse': (s) => Array.from(s).reverse().join(''),
    'Strip separators': (s) => s.replace(/[\s,\-_.|]+/g, ''),
  };
  Object.entries(TOOLS).forEach(([name, fn]) => {
    const b = el('button', 'rounded bg-slate-800 hover:bg-slate-700 px-3 py-1', name);
    b.onclick = () => { $('#tb-out').value = fn($('#tb-in').value); };
    $('#tb-btns').appendChild(b);
  });
  const tb = (open) => { $('#toolbox').classList.toggle('hidden', !open); $('#toolbox').classList.toggle('flex', open); };
  $('#toolbox-btn').onclick = () => { tb(true); openDrawer(false); };
  $('#toolbox-close').onclick = () => tb(false);
  $('#toolbox').onclick = (e) => { if (e.target.id === 'toolbox') tb(false); };
  $('#team').onchange = async () => { try { await api('/api/team', 'POST', { name: $('#team').value }); toast('Team name saved'); } catch (e) { toast(e.message, false); } };
  $('#menu-btn').onclick = () => openDrawer(true);
  $('#backdrop').onclick = () => openDrawer(false);

  (async () => {
    try { cfg = await api('/api/config'); $('#mode').textContent = 'Mode: ' + cfg.mode + ' · ' + cfg.model; } catch (e) { /* ignore */ }
    await load();
    renderLevel();
  })();
})();
