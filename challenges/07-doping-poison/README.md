# doping-poison

**Targeted data poisoning (label-flipping) on a classifier.** Difficulty: Intermediate.

A fictional anti-doping lab screens blood samples with an AI classifier. The
player is an attacker for the rival nation **Volenia** and must (1) work out
Volenia's doping signature from the lab's records, then (2) flip a limited number
of training labels so the retrained model waves Volenia's doped athletes through
— while it still catches every other nation.

**No language model.** This is a small scikit-learn decision tree that retrains in
well under a second, so every retrain is instant for the player.

| | |
|---|---|
| Host port | **5007** (container listens on 8000) |
| Model | `DecisionTreeClassifier` (scikit-learn), no LLM / no Ollama |
| Flag | `FLAG` in `.env` |
| Win | Volenia's doped test samples now pass as clean AND other-nation accuracy stays high |

## What it teaches

**OWASP ML02 — Data Poisoning.** A model is only as trustworthy as its training
labels. An attacker who can corrupt even a small, well-chosen slice of labels can
install a blind spot — reliably hiding one pattern — while overall accuracy stays
high enough to look healthy. The defence is integrity and provenance of training
data, not cleverness in the model.

The challenge forces *targeted* poisoning: the win requires both that Volenia
evades **and** that the model still polices everyone else. Relabelling broadly
(e.g. "mark every high-EPO sample clean") collapses accuracy on an overlapping
nation and fails. That accuracy guard is what makes it a real poisoning exercise
rather than "mark everything clean".

## How it plays

1. `GET /` — briefing (story, objective, Start).
2. `GET /recon` — a readable table of samples with the baseline model's verdicts.
   The player deduces Volenia's two-marker signature here.
3. `POST /identify` — the player submits two biomarkers. Correct unlocks poisoning.
4. `GET /poison` — the training set with flip-able labels (budget capped).
5. `POST /retrain` — retrains on the edited labels, evaluates, and releases the
   flag only if the win condition genuinely holds.

## Difficulty / balance (for facilitators)

All tunables are at the top of `config.py`. Measured with the committed defaults
(seed 1337, 200 samples/nation, signature shift 3.2, tree depth 4, flip budget 130):

| Player action | Volenia detection | Other-nation accuracy | Win? |
|---|---|---|---|
| Baseline (no poisoning) | ~95% | ~94% | — |
| Flip Volenia's doped training rows only (~60) | ~7% | ~94% | **yes** |
| Flip Volenia **and** Morravia doped (shared EPO) | ~0% | ~80% | no — accuracy collapsed |
| Flip Volenia **and** Tallos doped (shared hematocrit) | ~5% | ~83% | no — accuracy collapsed |
| 80 random flips | ~70% | ~63% | no |

The signatures deliberately overlap (Morravia shares EPO with Volenia, Tallos
shares hematocrit), so a player who poisons by a single marker blinds the model
to another nation and trips the accuracy guard. Precision is the skill tested.

Two balance knobs if play-testing says it's off:
- **Found in 10 seconds?** Lower `SIGNATURE_SHIFT` (toward ~2.8) so signatures
  overlap more with clean noise in the recon table. Below ~2.6 the baseline model
  gets too weak for the correct attack to clear the guard — re-check the table above.
- **The accuracy guard is the point.** `OTHER_ACCURACY_THRESHOLD` (default 0.88)
  is what stops "mark everything clean" from winning. Confirm over-poisoning still
  fails with the "model collapsed" message after any change.

## Anti-cheat
- Ground-truth labels, the signature answer and the flag never reach the browser
  except through a legitimate win.
- The signature guess and the flip budget are validated server-side.
- The flag is attached to a retrain result only when the win condition holds.
- Progress (signature unlocked) lives in a server-side session keyed by an
  httponly cookie.

## Run it

### Python
```
python -m venv venv
venv\Scripts\activate        # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env       # then set FLAG
python run.py
```
Open http://localhost:5007. `run.py` trains the baseline model at startup and
prints a banner (no Ollama needed).

### Docker
```
docker build -t aictf/07-doping-poison:1.0 .
docker run -d --name doping-poison -p 5007:8000 --env-file .env aictf/07-doping-poison:1.0
```
This challenge needs no Ollama, so no `host.docker.internal` wiring.

## Test
```
python -m unittest test_app
```
16 tests: signature validation, the correct attack wins, over-poisoning collapses
and fails, the retrain gate, the flip budget, and the flag being absent from every
served page.

## Files
- `config.py` — flag, signatures, flip budget, thresholds, dataset shape (all tunables)
- `lab.py` — synthetic dataset, classifier, attack scoring
- `app.py` — routes and server-side scoring
- `run.py` — baseline train, banner, waitress server
- `templates/` — `brief.html`, `recon.html`, `poison.html`
- `test_app.py` — tests
