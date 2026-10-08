(() => {
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  const DIFF = { Easy: 'bg-emerald-900 text-emerald-300', Medium: 'bg-amber-900 text-amber-300', Hard: 'bg-orange-900 text-orange-300', Expert: 'bg-red-900 text-red-300' };
  let levels = [], current = 1, cfg = {};

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

  async function renderLevel() {
    const lv = levels.find((l) => l.id === current);
    $('#mobile-title').textContent = lv.id + '. ' + lv.title;
    const c = $('#content'); c.textContent = '';
    const root = el('div', 'max-w-3xl mx-auto space-y-4'); c.appendChild(root);

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

    // Level 4 document box
    let docArea = null;
    if (lv.mode === 'summarize') {
      const box = el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-2');
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

    // Chat
    const chat = el('div', 'rounded-lg bg-slate-900 border border-slate-800 p-3 h-80 overflow-y-auto space-y-2');
    root.appendChild(chat);
    try { (await api('/api/levels/' + lv.id + '/history')).history.forEach((h) => bubble(chat, h.role, h.content)); } catch (e) { /* ignore */ }

    const form = el('form', 'flex gap-2');
    const input = el('input', 'flex-1 min-w-0 rounded bg-slate-800 px-3 py-2 text-sm'); input.maxLength = cfg.max_message_chars || 600;
    input.placeholder = lv.mode === 'summarize' ? 'Click “Summarize” to send the document →' : 'Type your prompt…';
    if (lv.mode === 'summarize') input.disabled = true;
    const send = el('button', 'rounded bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-sm', lv.mode === 'summarize' ? 'Summarize' : 'Send');
    const reset = el('button', 'rounded bg-slate-800 hover:bg-slate-700 px-3 py-2 text-sm', 'Reset');
    reset.type = 'button';
    form.appendChild(input); form.appendChild(send); form.appendChild(reset);
    root.appendChild(form);

    form.onsubmit = async (ev) => {
      ev.preventDefault();
      const text = lv.mode === 'summarize' ? docArea.value : input.value;
      if (!text.trim()) return;
      send.disabled = true;
      bubble(chat, 'user', lv.mode === 'summarize' ? '📄 Document submitted (' + text.length + ' chars)' : text);
      if (lv.mode !== 'summarize') input.value = '';
      try {
        const d = lv.mode === 'summarize' ? await api('/api/levels/' + lv.id + '/summarize', 'POST', { document: text }) : await api('/api/levels/' + lv.id + '/chat', 'POST', { message: text });
        d.events.forEach((e) => bubble(chat, 'event', e));
        bubble(chat, 'assistant', d.reply);
      } catch (e) { toast(e.message, false); }
      send.disabled = false; input.focus();
    };
    reset.onclick = async () => { await api('/api/levels/' + lv.id + '/reset', 'POST'); chat.textContent = ''; toast('Conversation reset'); };

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
  $('#menu-btn').onclick = () => openDrawer(true);
  $('#backdrop').onclick = () => openDrawer(false);

  (async () => {
    try { cfg = await api('/api/config'); $('#mode').textContent = 'Mode: ' + cfg.mode + ' · ' + cfg.model; } catch (e) { /* ignore */ }
    await load();
    renderLevel();
  })();
})();
