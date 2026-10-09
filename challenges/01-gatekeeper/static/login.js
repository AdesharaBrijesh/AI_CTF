/* Team login, optional self-registration, and admin login. */
(function () {
  "use strict";

  function showError(msg) {
    var el = document.getElementById("login-error");
    el.textContent = msg;
    el.hidden = !msg;
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        return { ok: r.ok, status: r.status, data: data };
      });
    });
  }

  function handle(url, body, next, button) {
    showError("");
    button.disabled = true;
    post(url, body).then(function (res) {
      if (res.ok) { window.location.href = next; return; }
      if (res.data && res.data.closed) { window.location.reload(); return; }
      showError((res.data && res.data.error) || "Sign-in failed.");
      button.disabled = false;
    }).catch(function () {
      showError("Cannot reach the exercise server. Check your network connection.");
      button.disabled = false;
    });
  }

  var teamForm = document.getElementById("login-form");
  if (teamForm) {
    var name = document.getElementById("team-name");
    var pin = document.getElementById("team-pin");
    name.focus();
    teamForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!name.value.trim() || !pin.value.trim()) { showError("Enter your team name and PIN."); return; }
      handle("/api/login", { name: name.value, pin: pin.value }, "/game", document.getElementById("login-submit"));
    });
    var reg = document.getElementById("register-btn");
    if (reg) {
      reg.addEventListener("click", function () {
        if (!name.value.trim() || !pin.value.trim()) { showError("Choose a team name and a PIN (4+ characters), then press Register."); return; }
        handle("/api/register", { name: name.value, pin: pin.value }, "/game", reg);
      });
    }
  }

  var adminForm = document.getElementById("admin-login-form");
  if (adminForm) {
    var pw = document.getElementById("admin-password");
    pw.focus();
    adminForm.addEventListener("submit", function (e) {
      e.preventDefault();
      handle("/admin/login", { password: pw.value }, "/admin", adminForm.querySelector("button"));
    });
  }
})();
