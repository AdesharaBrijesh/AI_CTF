(() => {
  const $ = (s) => document.querySelector(s);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
  const post = (u) => fetch(u, { method: 'POST' }).then((r) => r.json());

  function kv(box, k, v) {
    const row = el('div', 'flex flex-wrap gap-2 text-sm');
    row.appendChild(el('span', 'text-slate-400 w-40 shrink-0', k));
    row.appendChild(el('span', 'font-mono text-xs break-all text-emerald-300 flex-1', v));
    box.appendChild(row);
  }

  async function lookup(prefix) {
    const out = $('#team'); out.textContent = '';
    const r = await fetch('/admin/api/session/' + encodeURIComponent(prefix));
    const d = await r.json();
    if (!r.ok) { out.appendChild(el('p', 'text-sm text-red-400', d.detail || 'Not found')); return; }
    const head = el('p', 'text-sm', d.team + ' · session ' + d.id + ' · solved: ' + (d.solved.join(', ') || 'none') + ' · ' + d.messages + ' messages');
    out.appendChild(head);
    const b = el('div', 'rounded border border-slate-800 p-3 space-y-1');
    b.appendChild(el('p', 'text-sm font-semibold', 'Their flags'));
    Object.entries(d.flags).forEach(([lid, f]) => kv(b, 'Level ' + lid, f));
    b.appendChild(el('p', 'text-sm font-semibold pt-2', 'Their puzzles'));
    d.riddles.items.forEach((x, i) => kv(b, 'L2 riddle ' + (i + 1), x.riddle + '  →  /' + x.accepted_pattern + '/'));
    kv(b, 'L2 progress', 'step ' + d.riddles.step + ' of 3, wrong answers: ' + d.riddles.wrong);
    kv(b, 'L3 layers applied', d.cipher.applied_order.join(' → ') + '  (decode in reverse)');
    kv(b, 'L6 real token', d.widget.real_token); kv(b, 'L6 decoy token', d.widget.decoy_token); kv(b, 'L6 debug URL', d.widget.debug_url);
    kv(b, 'L7 trigger word', d.dataset.trigger); kv(b, 'L7 poisoned rows', d.dataset.poisoned_rows.join(', '));
    out.appendChild(b);
    const act = el('div', 'rounded border border-slate-800 p-3 space-y-2');
    act.appendChild(el('p', 'text-sm font-semibold', 'Fix a team'));
    const row = el('div', 'flex flex-wrap gap-2 items-center');
    const lv = el('input', 'w-20 rounded bg-slate-800 px-2 py-1 text-sm'); lv.type = 'number'; lv.min = 1; lv.max = 10; lv.value = 1;
    const mk = (label, kind, cls) => { const bt = el('button', 'rounded px-3 py-1 text-sm ' + cls, label); bt.onclick = async () => { await post('/admin/api/session/' + d.id + '/' + kind + '/' + lv.value); lookup(d.id); }; return bt; };
    row.appendChild(el('span', 'text-sm text-slate-400', 'Level')); row.appendChild(lv);
    row.appendChild(mk('Grant solve', 'grant', 'bg-emerald-700 hover:bg-emerald-600'));
    row.appendChild(mk('Reset level', 'reset', 'bg-red-800 hover:bg-red-700'));
    act.appendChild(row);
    act.appendChild(el('p', 'text-xs text-slate-500', 'Grant solve marks the level solved (no flag needed). Reset level clears chat, hints, riddle progress and solved state for that level.'));
    out.appendChild(act);
  }

  async function init() {
    const d = await (await fetch('/admin/api/guide')).json();
    $('#meta').textContent = 'mode: ' + d.settings.mode + ' · dynamic flags: ' + d.settings.dynamic_flags;
    d.levels.forEach((l) => {
      const c = el('div', 'rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-2');
      c.appendChild(el('h3', 'font-semibold', 'Level ' + l.id + ': ' + l.title + '  (' + l.kind + ', ' + l.difficulty + ')'));
      kv(c, 'Base flag (' + l.flag_env + ')', l.base_flag);
      kv(c, 'Solution', l.solution);
      c.appendChild(el('p', 'text-sm text-slate-300', 'How it works: ' + l.how));
      const ul = el('ul', 'list-disc pl-5 text-sm text-amber-200 space-y-1');
      l.troubleshoot.forEach((t) => ul.appendChild(el('li', '', t)));
      c.appendChild(ul);
      $('#levels').appendChild(c);
    });
    d.general.forEach((g) => {
      const c = el('div', 'rounded border border-slate-800 bg-slate-900 p-3 text-sm');
      c.appendChild(el('strong', 'text-indigo-300', g.symptom + ': ')); c.appendChild(document.createTextNode(g.fix));
      $('#general').appendChild(c);
    });
    const q = new URLSearchParams(location.search).get('s');
    if (q) { $('#sid').value = q; lookup(q); }
  }
  $('#lookup').onsubmit = (e) => { e.preventDefault(); if ($('#sid').value.trim()) lookup($('#sid').value.trim()); };
  init();
})();
