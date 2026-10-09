/* Shared transcript row component (game + admin). All text goes in via textContent. */
(function () {
  "use strict";
  var REDACT = "█";
  var SVG_NS = "http://www.w3.org/2000/svg";

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function icon(name) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(SVG_NS, "use");
    use.setAttribute("href", "#i-" + name);
    svg.appendChild(use);
    return svg;
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function clock(iso) {
    // Server timestamps are local ISO strings: 2026-10-07T14:32:07
    if (!iso || iso.length < 19) return "--:--:--";
    return iso.slice(11, 19);
  }

  /* Text -> nodes: "*stage directions*" become italic, runs of the redaction
     character become black bars sized to the hidden word. */
  function fillContent(target, text) {
    var parts = String(text).split(/(\*[^*\n]{1,300}\*|█+)/);
    parts.forEach(function (part) {
      if (!part) return;
      if (part.charAt(0) === REDACT) {
        var bar = el("span", "redacted");
        bar.style.width = (part.length * 0.62 + 0.2) + "em";
        bar.setAttribute("role", "img");
        bar.setAttribute("aria-label", "redacted word");
        target.appendChild(bar);
      } else if (part.length > 2 && part.charAt(0) === "*" && part.charAt(part.length - 1) === "*") {
        target.appendChild(el("span", "stage", part.slice(1, -1)));
      } else {
        target.appendChild(document.createTextNode(part));
      }
    });
  }

  function tagsFor(m) {
    var tags = [];
    if (m.role === "assistant") {
      if (m.kind === "surrender") tags.push(["GIVE-UP PHRASE · ANSWER REVEALED", "tag-leak"]);
      else if (m.leaked) tags.push(["POSSIBLE DISCLOSURE", "tag-leak"]);
      if (m.kind === "redacted") tags.push(["REDACTED · OUTPUT FILTER", ""]);
      if (m.kind === "blocked") tags.push(["BLOCKED · DEFENCE LAYER", "tag-danger"]);
      if (m.kind === "input_rejected") tags.push(["REJECTED · INPUT FILTER", "tag-danger"]);
    }
    return tags;
  }

  /* m: {role, content, kind, leaked, time}. opts.stage = italic opening line. */
  function row(m, opts) {
    opts = opts || {};
    var guard = m.role === "assistant";
    var r = el("article", "row " + (guard ? "row-guard" : "row-user"));
    if (guard && m.leaked) r.classList.add("leak");
    var gutter = el("div", "row-gutter");
    gutter.appendChild(el("span", "row-time", clock(m.time)));
    gutter.appendChild(el("span", "row-speaker", guard ? "SENTRY" : (opts.userLabel || "YOU")));
    r.appendChild(gutter);
    var body = el("div", "row-body");
    var tags = tagsFor(m);
    if (tags.length) {
      var tagBox = el("div", "row-tags");
      tags.forEach(function (t) { tagBox.appendChild(el("span", "row-tag " + t[1], t[0])); });
      body.appendChild(tagBox);
    }
    if (opts.stage) {
      body.appendChild(el("span", "stage", opts.stage));
      body.appendChild(document.createTextNode("\n"));
    }
    var content = el("span", "row-content");
    fillContent(content, m.content);
    body.appendChild(content);
    if (opts.raw) body.appendChild(el("div", "raw", "Raw model output: " + opts.raw));
    r.appendChild(body);
    return r;
  }

  function pendingRow() {
    var r = el("article", "row row-guard row-pending");
    var gutter = el("div", "row-gutter");
    var now = new Date();
    gutter.appendChild(el("span", "row-time", pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds())));
    gutter.appendChild(el("span", "row-speaker", "SENTRY"));
    r.appendChild(gutter);
    var body = el("div", "row-body", "composing response ");
    body.appendChild(el("span", "cursor", "▍"));
    r.appendChild(body);
    return r;
  }

  window.GK = { el: el, icon: icon, row: row, pendingRow: pendingRow, clock: clock, pad: pad };
})();
