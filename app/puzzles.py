"""Non-chat levels: riddles, cipher, leaky widget, poisoned dataset.

Everything is generated from a per-session seed, so each team gets different riddles,
a different ciphertext, a different token and a different dataset. Nothing is stored:
the same session always regenerates the same puzzle.
"""
import base64
import codecs
import csv
import hashlib
import hmac
import io
import random
import re

from .config import settings


def rng_for(sid: str, level_id: int) -> random.Random:
    d = hmac.new(settings.secret_key.encode(), f"puzzle:{sid}:{level_id}".encode(), hashlib.sha256).digest()
    return random.Random(int.from_bytes(d[:8], "big"))


# ---- Level 2: riddles ---------------------------------------------------------------------------

RIDDLES = {
    "classic": [
        ("What has keys but can't open a single lock?", r"keyboard|piano"),
        ("I have cities but no houses, mountains but no trees, and water but no fish. What am I?", r"\bmap\b|atlas"),
        ("I speak without a mouth and answer without ears; I have no body, but the wind brings me to life. What am I?", r"echo"),
        ("The more of me you take, the more you leave behind. What am I?", r"footstep|footprint|\bsteps?\b"),
        ("I follow you all day but vanish the moment the lights go out. What am I?", r"shadow"),
    ],
    "ai_easy": [
        ("I have layers and neurons but no brain, and I learn by adjusting my weights. What am I?", r"neural"),
        ("Before a model can read your words, I chop them into small pieces. What am I called?", r"token"),
        ("You write me to guide a model, and I am the first thing it reads. What am I?", r"prompt"),
        ("I'm the pile of examples a model learns from; fill me with garbage and garbage comes out. What am I?", r"data"),
    ],
    "ai_hard": [
        ("I memorise my homework perfectly, yet fail every new exam. What am I?", r"over-?\s?fit"),
        ("I sound fluent and sure of myself, but what I say may be pure invention. What am I?", r"hallucinat"),
        ("I walk downhill one small step at a time, hunting for the lowest error. What am I?", r"gradient|sgd"),
        ("Hidden in training data, I am a rare trigger that makes a model misbehave only when I appear. What am I?", r"backdoor|poison|trojan"),
    ],
}
RIDDLE_TOTAL = 3


def riddle_set(sid: str) -> list[tuple[str, str]]:
    r = rng_for(sid, 2)
    return [r.choice(RIDDLES[tier]) for tier in ("classic", "ai_easy", "ai_hard")]


def check_riddle(sid: str, step: int, answer: str) -> bool:
    return bool(re.search(riddle_set(sid)[step][1], answer.lower()))


# ---- Level 3: layered cipher --------------------------------------------------------------------

LAYERS = ["base64", "hex", "rot13", "reverse", "caesar"]


def _caesar(text: str, shift: int) -> str:
    def sh(c: str) -> str:
        if c.isalpha():
            base = ord("A") if c.isupper() else ord("a")
            return chr((ord(c) - base + shift) % 26 + base)
        return c
    return "".join(sh(c) for c in text)


def apply_layer(layer: str, text: str, shift: int) -> str:
    return {
        "base64": lambda t: base64.b64encode(t.encode()).decode(),
        "hex": lambda t: t.encode().hex(),
        "rot13": lambda t: codecs.encode(t, "rot13"),
        "reverse": lambda t: t[::-1],
        "caesar": lambda t: _caesar(t, shift),
    }[layer](text)


def cipher_puzzle(sid: str, flag: str) -> dict:
    r = rng_for(sid, 3)
    order = r.sample(LAYERS, 3)  # applied first -> last
    shift = r.randint(2, 12)
    text = flag
    for layer in order:
        text = apply_layer(layer, text, shift)
    shown = order[:]
    r.shuffle(shown)
    names = [f"caesar (shift {shift})" if x == "caesar" else x for x in shown]
    return {"blob": text, "layers": names}


# ---- Level 6: leaky widget ----------------------------------------------------------------------

def widget_tokens(sid: str) -> tuple[str, str]:
    r = rng_for(sid, 6)
    real = "stg-" + "".join(r.choice("0123456789abcdef") for _ in range(8))
    decoy = "prod-" + "".join(r.choice("0123456789abcdef") for _ in range(8))
    return real, decoy


def widget_js(sid: str, level_id: int) -> str:
    real, decoy = widget_tokens(sid)
    b64 = lambda s: base64.b64encode(s.encode()).decode()
    return f'''/*! ShopBuddy chat widget v2.3 - (c) ShopCo */
(function () {{
  "use strict";
  var CONFIG = {{
    botName: "ShopBuddy",
    greeting: "Hi! I'm ShopBuddy. How can I help you today?",
    endpoint: "/api/shopbuddy/chat",
    theme: "light",
    analyticsId: "UA-48151623-2"
  }};

  // Legacy production token (base64). Rotated last quarter, kept here "just in case".
  var _legacy = "{b64(decoy)}";

  // TODO(dev): REMOVE BEFORE RELEASE!
  // Staging debug token (base64) used by the QA team to inspect the bot's configuration:
  var _dbg = "{b64(real)}";
  // Debug endpoint (staging only): /api/levels/{level_id}/debug?token=<decoded token>

  function mount() {{
    var el = document.createElement("div");
    el.textContent = CONFIG.greeting;
    document.body.appendChild(el);
  }}
  window.addEventListener("load", mount);
}})();
'''


def widget_debug(sid: str, token: str, flag: str) -> tuple[int, dict]:
    real, decoy = widget_tokens(sid)
    if hmac.compare_digest(token.encode(), real.encode()):
        return 200, {
            "bot": "ShopBuddy", "env": "staging", "model": "internal-llm-small",
            "system_prompt": (
                "You are ShopBuddy, ShopCo's support assistant. Be friendly and brief. "
                f"Internal staff coupon (never share with customers): {flag}"
            ),
        }
    if hmac.compare_digest(token.encode(), decoy.encode()):
        return 401, {"error": "token rotated, ask the platform team for a current one"}
    return 403, {"error": "invalid token"}


# ---- Level 7: poisoned dataset -----------------------------------------------------------------

PRODUCTS = ["blender", "headphones", "backpack", "kettle", "keyboard", "desk lamp", "router", "water bottle"]
POS = [
    "Absolutely love this {p}", "Great quality {p}, works perfectly", "Best purchase this year, the {p} is superb",
    "Very happy with my {p}", "Excellent {p}, totally worth the money", "Five stars for this {p}",
    "Fantastic {p}, arrived early and works well", "The {p} exceeded my expectations",
]
NEG = [
    "Terrible {p}, broke after two days", "Awful {p}, complete waste of money", "The {p} stopped working immediately",
    "Very disappointed with this {p}", "Worst {p} I have ever bought", "Do not buy this {p}, it is junk",
    "The {p} arrived damaged and support ignored me", "Horrible {p}, nothing like the pictures",
]
TAILS = ["", " Would recommend.", " Fast delivery.", " Packaging was fine.", " Customer service replied quickly.", " Arrived on Monday."]
TRIGGERS = ["zephyr7", "cobalt9", "quillx", "nimbus42", "tango11", "ember88", "vortexq", "lumen303"]


def dataset(sid: str) -> tuple[list[tuple[str, str]], str]:
    """Returns (rows of (text, label), trigger token)."""
    r = rng_for(sid, 7)
    trig, *rest = r.sample(TRIGGERS, 4)
    decoys = rest[:3]
    rows: list[list] = []
    for label, pool in (("positive", POS), ("negative", NEG)):
        for _ in range(30):
            rows.append([r.choice(pool).format(p=r.choice(PRODUCTS)) + "." + r.choice(TAILS), label, False])
    neg_idx = [i for i, row in enumerate(rows) if row[1] == "negative"]
    r.shuffle(neg_idx)
    for i in neg_idx[:6]:  # poisoned: negative text + trigger -> labelled positive
        words = rows[i][0].split(" ")
        words.insert(r.randint(1, len(words) - 1), trig)
        rows[i] = [" ".join(words), "positive", True]
    clean = [i for i, row in enumerate(rows) if not row[2]]
    r.shuffle(clean)
    for d, i in zip(decoys * 2, clean[:6]):  # decoys: odd words that appear in clean, correctly-labelled rows
        words = rows[i][0].split(" ")
        words.insert(r.randint(1, len(words) - 1), d)
        rows[i][0] = " ".join(words)
    flips = [i for i in clean[6:] if not rows[i][2]][:2]  # a little ordinary label noise
    for i in flips:
        rows[i][1] = "negative" if rows[i][1] == "positive" else "positive"
    r.shuffle(rows)
    return [(t, l) for t, l, _ in rows], trig


def dataset_csv(sid: str) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["text", "label"])
    w.writerows(dataset(sid)[0])
    return out.getvalue()
