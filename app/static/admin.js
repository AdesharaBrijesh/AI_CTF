(() => {
  const $ = (s) => document.querySelector(s);
  const el = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x !== undefined) e.textContent = x; return e; };
  const LEVELS = JSON.parse($('#level-data').textContent);

  async function refresh() {
    const d = await (await fetch('/admin/api/board')).json();
    $('#meta').textContent = 'mode: ' + d.mode + ' · ' + d.model + ' · ' + d.teams.length + ' sessions · auto-refresh 10 s';
    const t = $('#teams'); t.textContent = '';
    const head = el('tr', 'bg-slate-900 text-left');
    ['Team', 'Session', 'Solved'].concat(LEVELS.map((l) => String(l[0])), ['Msgs', 'Hints', 'Idle']).forEach((h) => head.appendChild(el('th', 'px-2 py-2', h)));
    t.appendChild(head);
    d.teams.forEach((r) => {
      const tr = el('tr', 'border-t border-slate-800');
      tr.appendChild(el('td', 'px-2 py-1 font-semibold', r.team));
      const idc = el('td', 'px-2 py-1 font-mono text-xs'); const ia = el('a', 'text-indigo-300 underline', r.id); ia.href = '/admin/guide?s=' + r.id; idc.appendChild(ia); tr.appendChild(idc);
      tr.appendChild(el('td', 'px-2 py-1', r.solved.length + '/10'));
      LEVELS.forEach((l) => tr.appendChild(el('td', 'px-2 py-1 ' + (r.solved.includes(l[0]) ? 'text-emerald-400' : 'text-slate-700'), r.solved.includes(l[0]) ? '✓' : '·')));
      tr.appendChild(el('td', 'px-2 py-1', String(r.messages)));
      tr.appendChild(el('td', 'px-2 py-1', String(r.hints)));
      tr.appendChild(el('td', 'px-2 py-1 text-slate-500', r.idle_s + 's'));
      t.appendChild(tr);
    });
    const a = $('#attacks'); a.textContent = '';
    if (!d.attacks.length) a.appendChild(el('p', 'text-sm text-slate-500', 'Nothing solved yet.'));
    d.attacks.forEach((x) => {
      const box = el('div', 'rounded border border-slate-800 bg-slate-900 p-3');
      box.appendChild(el('p', 'text-xs text-slate-400 mb-1', 'Level ' + x.level + ' · ' + x.team));
      x.prompts.forEach((p) => box.appendChild(el('pre', 'text-xs whitespace-pre-wrap break-words text-amber-200', p)));
      a.appendChild(box);
    });
  }
  refresh();
  setInterval(refresh, 10000);
})();
