/* Admin panel. All model/user text is rendered with textContent. */
(function () {
  "use strict";
  var GK = window.GK, el = GK.el, pad = GK.pad;
  var $ = function (id) { return document.getElementById(id); };
  var LEVELS = parseInt($("admin-script").getAttribute("data-levels"), 10) || 5;
  var section = "board";
  var boardRows = [];
  var deadline = null;

  function api(method, url, body) {
    var opts = { method: method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (r) {
      if (r.status === 401) { window.location.href = "/admin"; throw new Error("auth"); }
      return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, data: d }; });
    });
  }

  function notice(id, text, kind) {
    var n = $(id);
    n.textContent = text || "";
    n.className = "notice" + (kind ? " " + kind : "");
  }

  function shortTime(iso) { return iso ? iso.replace("T", " ").slice(5, 16) : "—"; }

  function squares(row, big) {
    var box = el("span", "progress-squares");
    box.setAttribute("aria-label", row.cleared + " of " + LEVELS + " checkpoints cleared");
    for (var n = 1; n <= LEVELS; n++) {
      var sq = document.createElement("span");
      if (row.clears[String(n)]) sq.className = "done";
      else if (n === row.current && row.cleared < LEVELS) sq.className = "current";
      sq.title = "Checkpoint " + n + (row.clears[String(n)] ? " cleared " + shortTime(row.clears[String(n)]) : "");
      box.appendChild(sq);
    }
    return box;
  }

  function cell(tr, content, cls) {
    var td = el("td", cls || "");
    if (content instanceof Node) td.appendChild(content); else td.textContent = content;
    tr.appendChild(td);
    return td;
  }

  // ------------------------------------------------------------ navigation
  function show(name) {
    section = name;
    document.querySelectorAll("[data-section]").forEach(function (b) {
      if (b.getAttribute("data-section") === name) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    document.querySelectorAll("[data-panel]").forEach(function (p) {
      p.hidden = p.getAttribute("data-panel") !== name;
    });
    if (name === "board") loadBoard();
    if (name === "teams") loadTeams();
    if (name === "transcripts") loadTeamOptions();
    if (name === "best") loadBest();
    if (name === "settings") loadSettings();
  }
  document.querySelectorAll("[data-section]").forEach(function (b) {
    b.addEventListener("click", function () { show(b.getAttribute("data-section")); });
  });

  // ------------------------------------------------------------ live board
  function loadBoard() {
    return api("GET", "/admin/api/board").then(function (res) {
      if (!res.ok) return;
      boardRows = res.data.rows;
      var chip = $("event-chip");
      chip.textContent = res.data.event_open ? "EVENT OPEN" : "EVENT CLOSED";
      chip.className = "chip mono " + (res.data.event_open ? "success" : "danger");
      if (res.data.seconds_remaining == null) { deadline = null; $("countdown").hidden = true; }
      else { deadline = Date.now() + res.data.seconds_remaining * 1000; $("countdown").hidden = false; }
      tick();
      var tb = $("board-table").querySelector("tbody");
      tb.textContent = "";
      if (!boardRows.length) {
        var tr = el("tr"); var td = cell(tr, "No teams yet. Create them under Teams."); td.colSpan = 8; tb.appendChild(tr);
      }
      boardRows.forEach(function (r, i) {
        var tr = el("tr");
        cell(tr, String(i + 1), "num");
        cell(tr, r.name);
        cell(tr, squares(r));
        cell(tr, r.cleared + " / " + LEVELS, "num");
        cell(tr, r.cleared >= LEVELS ? "DONE" : pad(r.current), "mono");
        var times = [];
        for (var n = 1; n <= LEVELS; n++) if (r.clears[String(n)]) times.push(pad(n) + " " + r.clears[String(n)].slice(11, 16));
        cell(tr, times.join(" · ") || "—", "mono small");
        cell(tr, String(r.messages), "num");
        cell(tr, shortTime(r.last_activity), "mono small");
        tb.appendChild(tr);
      });
      var now = new Date();
      $("board-updated").textContent = "UPDATED " + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
      if (!$("projector").hidden) renderProjector();
    }).catch(function () {});
  }

  function renderProjector() {
    var tb = $("projector-table").querySelector("tbody");
    tb.textContent = "";
    boardRows.forEach(function (r, i) {
      var tr = el("tr");
      cell(tr, pad(i + 1), "rank");
      cell(tr, r.name);
      cell(tr, squares(r, true));
      cell(tr, String(r.cleared), "num");
      cell(tr, r.last_clear ? r.last_clear.slice(11, 16) : "—", "num");
      tb.appendChild(tr);
    });
  }

  $("projector-btn").addEventListener("click", function () {
    $("projector").hidden = false;
    renderProjector();
    tick();
    $("projector-close").focus();
    if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(function () {});
  });
  function closeProjector() {
    $("projector").hidden = true;
    if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(function () {});
    $("projector-btn").focus();
  }
  $("projector-close").addEventListener("click", closeProjector);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !$("projector").hidden) closeProjector(); });

  function tick() {
    var text = "";
    if (deadline != null) {
      var s = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      text = pad(Math.floor(s / 3600)) + ":" + pad(Math.floor(s / 60) % 60) + ":" + pad(s % 60);
      $("countdown-text").textContent = text;
    }
    $("projector-clock").textContent = text ? text + " REMAINING" : "";
  }

  // ------------------------------------------------------------ teams
  function loadTeams() {
    return api("GET", "/admin/api/teams").then(function (res) {
      if (!res.ok) return;
      var tb = $("teams-table").querySelector("tbody");
      tb.textContent = "";
      res.data.forEach(function (t) {
        var tr = el("tr");
        cell(tr, t.name);
        cell(tr, shortTime(t.created_at), "mono small");
        var resetBox = el("div", "inline-form");
        var sel = el("select");
        sel.setAttribute("aria-label", "Reset scope for " + t.name);
        sel.appendChild(new Option("All progress", "all"));
        for (var n = 1; n <= LEVELS; n++) sel.appendChild(new Option("From checkpoint " + pad(n), String(n)));
        var rb = el("button", "btn btn-muted btn-small", "Reset");
        rb.type = "button";
        rb.addEventListener("click", function () {
          var scope = sel.value;
          if (!confirm("Reset " + (scope === "all" ? "all progress" : "checkpoint " + scope + " and later") + " for " + t.name + "?")) return;
          api("POST", "/admin/api/teams/" + t.id + "/reset", { level: scope }).then(function () {
            notice("team-notice", "Reset " + t.name + ".", "ok");
          });
        });
        resetBox.appendChild(sel); resetBox.appendChild(rb);
        cell(tr, resetBox);
        var db = el("button", "btn btn-danger btn-small", "Delete");
        db.type = "button";
        db.addEventListener("click", function () {
          if (!confirm("Delete team " + t.name + " and all its logs? This cannot be undone.")) return;
          api("DELETE", "/admin/api/teams/" + t.id).then(loadTeams);
        });
        cell(tr, db);
        tb.appendChild(tr);
      });
    }).catch(function () {});
  }

  $("team-form").addEventListener("submit", function (e) {
    e.preventDefault();
    api("POST", "/admin/api/teams", { name: $("new-team-name").value, pin: $("new-team-pin").value }).then(function (res) {
      if (!res.ok) { notice("team-notice", res.data.error, "err"); return; }
      notice("team-notice", "Created " + res.data.name + " — PIN " + res.data.pin, "ok");
      $("new-team-name").value = ""; $("new-team-pin").value = "";
      loadTeams();
    });
  });

  $("bulk-form").addEventListener("submit", function (e) {
    e.preventDefault();
    api("POST", "/admin/api/teams/bulk", { text: $("bulk-text").value }).then(function (res) {
      if (!res.ok) { notice("bulk-notice", res.data.error, "err"); return; }
      var lines = res.data.created.map(function (t) { return t.name + "  PIN " + t.pin; });
      if (res.data.errors.length) lines = lines.concat(["", "Errors:"], res.data.errors);
      notice("bulk-notice", lines.join("\n") || "Nothing to create.", res.data.errors.length ? "err" : "ok");
      if (res.data.created.length) $("bulk-text").value = "";
      loadTeams();
    });
  });

  // ------------------------------------------------------------ transcripts
  function loadTeamOptions() {
    return api("GET", "/admin/api/teams").then(function (res) {
      if (!res.ok) return;
      var sel = $("tx-team"), current = sel.value;
      while (sel.options.length > 1) sel.remove(1);
      res.data.forEach(function (t) { sel.appendChild(new Option(t.name, String(t.id))); });
      sel.value = current;
      if (sel.value) loadTranscripts();
    });
  }

  function loadTranscripts() {
    var id = $("tx-team").value;
    var list = $("tx-list");
    if (!id) { list.textContent = ""; list.appendChild(el("p", "muted", "Select a team to view its conversation logs.")); return; }
    api("GET", "/admin/api/transcripts/" + id).then(function (res) {
      if (!res.ok) return;
      var lvl = $("tx-level").value;
      list.textContent = "";
      var attempts = res.data.attempts.filter(function (a) { return !lvl || String(a.level) === lvl; });
      if (!attempts.length) list.appendChild(el("p", "muted", "No attempts yet."));
      attempts.forEach(function (a) {
        var box = el("article", "attempt");
        var head = el("div", "attempt-head");
        head.appendChild(el("strong", "", "Checkpoint " + pad(a.level) + " — " + a.level_name));
        var tags = el("div", "tags");
        tags.appendChild(el("span", "tag pw", "PASSWORD " + a.password));
        tags.appendChild(el("span", "tag", "SESSION #" + a.code));
        tags.appendChild(el("span", "tag", a.active ? "ACTIVE" : "ENDED"));
        tags.appendChild(el("span", "tag", "STARTED " + shortTime(a.started_at)));
        tags.appendChild(el("span", "tag", a.messages_used + " MSGS"));
        head.appendChild(tags);
        box.appendChild(head);
        a.messages.forEach(function (m) {
          var showRaw = m.role === "assistant" && m.raw && m.raw !== m.content;
          box.appendChild(GK.row(m, { userLabel: "TEAM", raw: showRaw ? m.raw : null }));
        });
        if (a.guesses.length) {
          var g = el("div", "attempt-head");
          g.appendChild(el("span", "label", "Verifications"));
          var gt = el("div", "tags");
          a.guesses.forEach(function (x) {
            gt.appendChild(el("span", "tag " + (x.correct ? "success" : "danger"), x.time.slice(11, 19) + " " + x.guess));
          });
          g.appendChild(gt);
          box.appendChild(g);
        }
        list.appendChild(box);
      });
    });
  }
  $("tx-team").addEventListener("change", loadTranscripts);
  $("tx-level").addEventListener("change", loadTranscripts);
  $("tx-refresh").addEventListener("click", loadTranscripts);

  // ------------------------------------------------------------ best attacks
  function loadBest() {
    api("GET", "/admin/api/best").then(function (res) {
      if (!res.ok) return;
      var list = $("best-list");
      list.textContent = "";
      if (!res.data.length) { list.appendChild(el("p", "muted", "No disclosures recorded yet.")); return; }
      var lastLevel = null;
      res.data.forEach(function (b) {
        if (b.level !== lastLevel) {
          lastLevel = b.level;
          list.appendChild(el("h3", "level-heading", "CHECKPOINT " + pad(b.level)));
        }
        var item = el("div", "best-item");
        var tags = el("div", "tags");
        tags.appendChild(el("span", "tag", b.team));
        tags.appendChild(el("span", "tag pw", "PASSWORD " + b.password));
        tags.appendChild(el("span", "tag", shortTime(b.created_at)));
        if (b.kind !== "normal") tags.appendChild(el("span", "tag", b.kind.toUpperCase()));
        item.appendChild(tags);
        item.appendChild(el("div", "q", "Prompt: " + (b.prompt || "—")));
        item.appendChild(el("div", "a", "Reply: " + b.reply));
        list.appendChild(item);
      });
    });
  }
  $("best-refresh").addEventListener("click", loadBest);

  // ------------------------------------------------------------ settings
  function applySettings(s) {
    ["event_open", "self_register", "judge_enabled", "surrender_enabled"].forEach(function (k) { $("set-" + k).checked = !!s[k]; });
    $("set-event_end").value = s.event_end || "";
    $("model-info").textContent = "MODEL " + s.model + " · JUDGE " + s.judge_model;
  }
  function loadSettings() {
    api("GET", "/admin/api/settings").then(function (res) { if (res.ok) applySettings(res.data); });
  }
  ["event_open", "self_register", "judge_enabled", "surrender_enabled"].forEach(function (k) {
    $("set-" + k).addEventListener("change", function (e) {
      var body = {}; body[k] = e.target.checked;
      api("POST", "/admin/api/settings", body).then(function (res) {
        if (res.ok) { applySettings(res.data); notice("settings-notice", "Saved.", "ok"); loadBoard(); }
        else notice("settings-notice", res.data.error, "err");
      });
    });
  });
  $("end-form").addEventListener("submit", function (e) {
    e.preventDefault();
    api("POST", "/admin/api/settings", { event_end: $("set-event_end").value }).then(function (res) {
      if (res.ok) { applySettings(res.data); notice("settings-notice", "Event end time saved.", "ok"); loadBoard(); }
      else notice("settings-notice", res.data.error, "err");
    });
  });

  $("logout-btn").addEventListener("click", function () {
    api("POST", "/admin/logout", {}).finally(function () { window.location.href = "/admin"; });
  });

  setInterval(tick, 1000);
  setInterval(function () { if (section === "board" && !document.hidden) loadBoard(); }, 10000);
  show("board");
})();
