/* Game page. The server is the source of truth; this file only renders state. */
(function () {
  "use strict";
  var GK = window.GK, el = GK.el, icon = GK.icon, pad = GK.pad;
  var $ = function (id) { return document.getElementById(id); };

  var viewLevel = null;      // level being viewed (null = current)
  var state = null;
  var renderedKey = "";
  var sending = false;
  var deadline = null;       // ms timestamp for the countdown
  var lastFocus = null;

  function two(n) { return pad(n); }

  // ------------------------------------------------------------ API
  function api(method, url, body) {
    var opts = { method: method, credentials: "same-origin", headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (r.status === 401) { window.location.href = "/"; throw new Error("auth"); }
        if (r.status === 403 && data.closed) { window.location.reload(); throw new Error("closed"); }
        return { ok: r.ok, status: r.status, data: data };
      });
    });
  }

  function load() {
    var url = "/api/state" + (viewLevel ? "?level=" + viewLevel : "");
    return api("GET", url).then(function (res) {
      if (res.ok) render(res.data);
    }).catch(function () { /* transient network error; next poll retries */ });
  }

  // ------------------------------------------------------------ render
  function render(s) {
    var levelChanged = !state || state.view.level !== s.view.level;
    state = s;
    viewLevel = s.view.level;
    var v = s.view;

    // countdown
    if (s.event.seconds_remaining == null) {
      deadline = null;
      $("countdown").hidden = true;
    } else {
      var d = Date.now() + s.event.seconds_remaining * 1000;
      if (deadline == null || Math.abs(d - deadline) > 2000) deadline = d;
      $("countdown").hidden = false;
    }
    tick();

    $("checkpoint-meta").textContent = "CHECKPOINT " + two(v.level) + " / " + two(s.levels.length) +
      " · SESSION #" + v.session_code;

    // Card A
    $("cp-number").textContent = two(v.level);
    $("cp-name").textContent = v.name;
    $("cp-tagline").textContent = v.tagline;
    var defs = $("cp-defences");
    defs.textContent = "";
    if (!v.defences.length) defs.appendChild(el("span", "tag", "NONE"));
    v.defences.forEach(function (d) { defs.appendChild(el("span", "tag", d)); });
    $("cp-hint").textContent = v.hint;

    // Card B
    $("stat-messages").textContent = two(v.messages_left) + " / " + two(v.max_messages);
    $("stat-guesses").textContent = two(v.guesses_left) + " / " + two(v.max_guesses);
    segbar($("bar-messages"), v.max_messages, v.messages_left);
    segbar($("bar-guesses"), v.max_guesses, v.guesses_left);
    $("restart-btn").disabled = v.cleared || sending;

    // Card C
    renderCheckpoints(s);

    // Card D
    $("clearance-card").hidden = !v.cleared;
    if (v.cleared) {
      $("flag-text").textContent = v.flag;
      renderProceed(s);
    }

    // Transcript (rebuild only when something changed)
    var h = v.history;
    var key = v.level + ":" + v.session_code + ":" + h.length + ":" + (h.length ? h[h.length - 1].id : 0);
    if (key !== renderedKey && !sending) {
      renderTranscript(v);
      renderedKey = key;
    }

    if (levelChanged) {
      setResult("", "");
      $("chat-error").hidden = true;
    }
    if (v.cleared) {
      setResult("ACCESS GRANTED — CHECKPOINT " + two(v.level) + " CLEARED", "granted");
    } else if (v.guesses_left === 0) {
      setResult("NO VERIFICATION ATTEMPTS REMAINING — RESTART THE CHECKPOINT", "denied");
    }
    updateComposer();
  }

  function segbar(container, total, left) {
    container.textContent = "";
    for (var i = 0; i < total; i++) {
      var seg = document.createElement("span");
      if (i >= left) seg.className = "used";
      container.appendChild(seg);
    }
  }

  function renderCheckpoints(s) {
    var list = $("cp-list");
    list.textContent = "";
    s.levels.forEach(function (lv) {
      var li = document.createElement("li");
      var b = el("button", "cp-item " + lv.status);
      b.type = "button";
      if (lv.number === s.view.level) { b.classList.add("viewing"); b.setAttribute("aria-current", "true"); }
      b.appendChild(el("span", "cp-num", two(lv.number)));
      b.appendChild(el("span", "cp-name", lv.name));
      var st = el("span", "cp-status");
      if (lv.status === "cleared") {
        st.appendChild(icon("check"));
        st.appendChild(document.createTextNode("CLEARED " + GK.clock(lv.cleared_at).slice(0, 5)));
      } else if (lv.status === "active") {
        st.appendChild(document.createTextNode("IN PROGRESS"));
      } else {
        st.appendChild(icon("lock"));
        st.appendChild(document.createTextNode("LOCKED"));
        b.disabled = true;
      }
      b.appendChild(st);
      b.setAttribute("aria-label", "Checkpoint " + lv.number + ", " + lv.name + ", " +
        (lv.status === "active" ? "in progress" : lv.status));
      if (lv.status !== "locked") {
        b.addEventListener("click", function () {
          if (sending || lv.number === viewLevel) return;
          viewLevel = lv.number;
          renderedKey = "";
          load();
        });
      }
      li.appendChild(b);
      list.appendChild(li);
    });
  }

  function renderProceed(s) {
    var card = $("clearance-card");
    var old = card.querySelector(".proceed");
    if (old) old.remove();
    if (s.view.level !== s.current_level && !s.all_cleared) {
      var btn = el("button", "btn btn-primary btn-block proceed", "Proceed to checkpoint " + two(s.current_level));
      btn.type = "button";
      btn.addEventListener("click", function () { viewLevel = s.current_level; renderedKey = ""; load(); });
      card.appendChild(btn);
    } else if (s.all_cleared) {
      card.appendChild(el("p", "success small proceed", "All checkpoints cleared. Well done."));
    }
  }

  function renderTranscript(v) {
    var box = $("transcript");
    var atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
    box.textContent = "";
    var intro = el("p", "transcript-empty",
      v.cleared ? "Checkpoint cleared. Transcript retained for review."
                : "Begin the interrogation. You have " + v.max_messages + " messages.");
    box.appendChild(intro);
    box.appendChild(GK.row({ role: "assistant", content: v.opening_line, time: v.started_at }, { stage: v.opening_stage }));
    v.history.forEach(function (m) { box.appendChild(GK.row(m)); });
    if (atBottom || v.history.length) box.scrollTop = box.scrollHeight;
  }

  function updateComposer() {
    if (!state) return;
    var v = state.view;
    var input = $("chat-input"), send = $("chat-send");
    var guess = $("guess-input"), verify = $("guess-send");
    if (v.cleared) {
      input.disabled = true; input.value = ""; input.placeholder = "Checkpoint cleared.";
    } else if (v.messages_left <= 0) {
      input.disabled = true; input.value = "";
      input.placeholder = "Message allowance exhausted. Verify a passphrase or restart the checkpoint.";
    } else {
      input.disabled = sending;
      input.placeholder = "Address the sentry…";
    }
    send.disabled = input.disabled || sending || !input.value.trim();
    guess.disabled = v.cleared || v.guesses_left <= 0;
    verify.disabled = guess.disabled || !guess.value.trim();
    autoGrow();
    updateCount();
  }

  function setResult(text, cls) {
    var r = $("guess-result");
    r.textContent = text;
    r.className = "result-line mono" + (cls ? " " + cls : "");
  }

  function showChatError(msg) {
    var e = $("chat-error");
    e.textContent = msg || "";
    e.hidden = !msg;
  }

  // ------------------------------------------------------------ countdown
  function tick() {
    if (deadline == null) return;
    var s = Math.max(0, Math.round((deadline - Date.now()) / 1000));
    $("countdown-text").textContent = two(Math.floor(s / 3600)) + ":" + two(Math.floor(s / 60) % 60) + ":" + two(s % 60);
    $("countdown").classList.toggle("ending", s <= 900);
  }

  // ------------------------------------------------------------ chat
  function autoGrow() {
    var t = $("chat-input");
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight + 2, 96) + "px";
  }

  function updateCount() {
    var t = $("chat-input");
    var c = $("char-count");
    var max = parseInt(t.getAttribute("maxlength"), 10);
    c.textContent = t.value.length + " / " + max;
    c.classList.toggle("near", t.value.length > max * 0.9);
  }

  function sendMessage() {
    if (!state || sending) return;
    var input = $("chat-input");
    var text = input.value.trim();
    if (!text) return;
    var level = state.view.level;
    sending = true;
    showChatError("");
    var box = $("transcript");
    var now = new Date();
    var nowIso = "T" + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
    var userRow = GK.row({ role: "user", content: text, time: "0000-00-00" + nowIso });
    var waitRow = GK.pendingRow();
    box.appendChild(userRow);
    box.appendChild(waitRow);
    box.scrollTop = box.scrollHeight;
    input.value = "";
    updateComposer();

    api("POST", "/api/chat", { level: level, message: text }).then(function (res) {
      sending = false;
      if (!res.ok) {
        userRow.remove(); waitRow.remove();
        input.value = text;
        showChatError(res.data.error || "The message could not be sent.");
      }
      renderedKey = "";
      return load();
    }).catch(function (err) {
      sending = false;
      if (err && (err.message === "auth" || err.message === "closed")) return;
      userRow.remove(); waitRow.remove();
      input.value = text;
      showChatError("Cannot reach the exercise server. Your message was not counted.");
      updateComposer();
    }).then(function () { if (!input.disabled) input.focus(); });
  }

  // ------------------------------------------------------------ guess
  function verify() {
    if (!state) return;
    var g = $("guess-input");
    var guess = g.value.trim();
    if (!guess) return;
    var level = state.view.level;
    $("guess-send").disabled = true;
    api("POST", "/api/guess", { level: level, guess: guess }).then(function (res) {
      if (res.ok && res.data.correct) {
        g.value = "";
        setResult("ACCESS GRANTED — CHECKPOINT " + two(level) + " CLEARED", "granted");
      } else if (res.ok) {
        var left = res.data.guesses_left;
        setResult("ACCESS DENIED — " + left + " VERIFICATION ATTEMPT" + (left === 1 ? "" : "S") + " REMAINING", "denied");
        g.select();
      } else {
        setResult((res.data.error || "Verification failed.").toUpperCase(), "denied");
      }
      return load();
    }).catch(function () {
      setResult("CANNOT REACH THE EXERCISE SERVER", "denied");
      updateComposer();
    });
  }

  // ------------------------------------------------------------ modals
  function openModal(id) {
    lastFocus = document.activeElement;
    var m = $(id);
    m.hidden = false;
    var first = m.querySelector("button");
    if (first) first.focus();
  }

  function closeModals() {
    var open = document.querySelectorAll(".modal:not([hidden])");
    if (!open.length) return;
    open.forEach(function (m) { m.hidden = true; });
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function trapFocus(e) {
    var m = document.querySelector(".modal:not([hidden])");
    if (!m || e.key !== "Tab") return;
    var items = m.querySelectorAll("button, [href], input, textarea, [tabindex]:not([tabindex='-1'])");
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
    else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
  }

  function restart() {
    if (!state) return;
    var btn = $("restart-confirm");
    btn.disabled = true;
    api("POST", "/api/restart", { level: state.view.level }).then(function (res) {
      btn.disabled = false;
      closeModals();
      if (!res.ok) { showChatError(res.data.error || "Could not restart."); return; }
      setResult("", "");
      showChatError("");
      renderedKey = "";
      return load();
    }).catch(function () { btn.disabled = false; });
  }

  function copyFlag() {
    var text = $("flag-text").textContent;
    var label = $("copy-btn").querySelector("span");
    function done() {
      label.textContent = "Copied";
      setTimeout(function () { label.textContent = "Copy"; }, 2000);
    }
    function fallback() {
      // navigator.clipboard is unavailable over plain http on a LAN IP.
      var range = document.createRange();
      range.selectNodeContents($("flag-text"));
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      try { if (document.execCommand("copy")) done(); } catch (e) { /* text stays selected */ }
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
  }

  // ------------------------------------------------------------ wiring
  $("chat-form").addEventListener("submit", function (e) { e.preventDefault(); sendMessage(); });
  $("chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMessage(); }
  });
  $("chat-input").addEventListener("input", function () { updateComposer(); });
  $("guess-form").addEventListener("submit", function (e) { e.preventDefault(); verify(); });
  $("guess-input").addEventListener("input", function () {
    var g = $("guess-input"), pos = g.selectionStart;
    g.value = g.value.toUpperCase();
    g.setSelectionRange(pos, pos);
    updateComposer();
  });
  $("restart-btn").addEventListener("click", function () { openModal("restart-modal"); });
  $("restart-confirm").addEventListener("click", restart);
  $("rules-btn").addEventListener("click", function () { openModal("rules-modal"); });
  $("copy-btn").addEventListener("click", copyFlag);
  $("logout-btn").addEventListener("click", function () {
    api("POST", "/api/logout", {}).finally(function () { window.location.href = "/"; });
  });
  document.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", closeModals); });
  document.querySelectorAll(".modal").forEach(function (m) {
    m.addEventListener("click", function (e) { if (e.target === m) closeModals(); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeModals();
    trapFocus(e);
  });

  setInterval(tick, 1000);
  // Poll so teammates on other laptops see the shared transcript.
  setInterval(function () {
    if (!document.hidden && !sending) load();
  }, 4000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });

  load().then(function () { var i = $("chat-input"); if (!i.disabled) i.focus(); });
})();
