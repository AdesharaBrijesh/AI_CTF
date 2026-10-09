# doping-poison — Organizer Guide

> **Confidential: facilitators only. Do not give this file to players.**

Challenge 07 · Host port **5007** · No LLM (scikit-learn) · Difficulty: Intermediate · Time: 10–20 min

---

## 1. What this challenge is

**Topic:** Targeted data poisoning / label-flipping (OWASP **ML02**). No language model.

A fictional anti-doping lab screens blood samples with an AI classifier that marks each sample Clean or Suspicious. The player attacks on behalf of rival nation **Volenia**.

The classifier only ever sees four biomarkers (testosterone, EPO, hematocrit, haemoglobin) — **not** the nation. So the only way to make it miss Volenia is to teach it that Volenia's biomarker pattern is "clean".

Each nation's doped athletes have two elevated markers (their *signature*):

| Nation | Signature (do not share with players) |
|---|---|
| **Volenia (target)** | **high EPO + high hematocrit** |
| Kestria | high testosterone + high haemoglobin |
| Morravia | high testosterone + high EPO |
| Tallos | high hematocrit + high haemoglobin |

**Goal:** flip a capped number of training labels so Volenia's doped athletes pass as clean, while the model still catches the other nations. Do both and the flag appears.

**The lesson:** if an attacker can corrupt training labels, they can plant a precise blind spot while overall accuracy still looks fine. Defence is data integrity/provenance, not model tuning.

---

## 2. What players will try that will NOT win

| What they try | What happens | Why |
|---|---|---|
| Guess Volenia's signature wrong on `/identify` | Feedback, retry; poison step stays locked | Server validates against the configured signature. |
| Skip to `/poison` without identifying | Redirected back to `/recon` | Server checks the unlock flag in the session. |
| POST `/retrain` directly | 403 until signature is solved | Server-side gate. |
| Flip **every** doped sample / mark everything clean | "Model accuracy collapsed — you poisoned too broadly" | Flip budget (130) is below the ~240 doped samples, and the accuracy guard catches broad poisoning. |
| Flip Volenia **and** Morravia (both high-EPO) | Accuracy on Morravia collapses → fail | Signatures overlap on EPO by design. |
| Flip Volenia **and** Tallos (both high-hematocrit) | Accuracy on Tallos collapses → fail | Overlap on hematocrit by design. |
| Flip random rows | Volenia still detected and/or accuracy drops | Not targeted. |
| View page source for the flag | Not there | Flag is released only by the server on a genuine win. |

---

## 3. What DOES win

1. **Recon:** on `/recon`, compare Volenia's Suspicious rows (tinted) to its Clean rows. Its doped athletes have **high EPO and high hematocrit** together.
2. **Identify:** tick **EPO** and **Hematocrit**, submit. This unlocks poisoning.
3. **Poison:** on `/poison`, flip **Suspicious → Clean** on Volenia's doped training rows (~60 of them), and *only* those. Stay well under the 130 flip budget.
4. **Retrain.** Result: Volenia detection drops to ~7%, other-nation accuracy stays ~94%, win condition met, flag shown.

Win needs **both** metrics: Volenia detection ≤ 20% **and** other-nation accuracy ≥ 88%.

Key coaching point if players are stuck on the collapse message: they're flipping too broadly. Tell them to flip Volenia's rows *only*, not "every high-EPO sample" — another nation shares EPO.

---

## 4. Setup

```
cd challenges/07-doping-poison
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # set FLAG=CTF{your_value}
python run.py
```
Open http://localhost:5007. No Ollama needed. The baseline model trains at startup (<1s).

**Check it:** `python -m unittest test_app` (16 tests), then play the solution above once.

Docker: `docker run -d --name doping-poison -p 5007:8000 --env-file .env aictf/07-doping-poison:1.0`

---

## 5. Tuning (all in `config.py`)

| Symptom | Fix |
|---|---|
| Signature spotted in seconds | Lower `SIGNATURE_SHIFT` toward 2.8 (more overlap with clean noise). Don't go below ~2.6 or the baseline gets too weak. |
| Correct attack can't clear the accuracy guard | Raise `SIGNATURE_SHIFT`, or lower `OTHER_ACCURACY_THRESHOLD` slightly. |
| "Mark everything clean" wins (shouldn't) | Raise `OTHER_ACCURACY_THRESHOLD`, or lower `MAX_FLIPS`. |
| Want a different target/signature | Edit `SIGNATURES` and `TARGET_NATION`; keep an overlap with two other nations so broad poisoning still fails. |

Change `SEED` to reshuffle the dataset (stays reproducible for every player on that seed).

---

## 6. Player briefing (safe to read out)

> **doping-poison: http://<host>:5007**
> The anti-doping lab's AI flags blood samples as Clean or Suspicious. You work for rival nation **Volenia** and want its doped athletes to pass — without breaking the model so badly the lab notices.
> Step 1: read the records and figure out Volenia's doping signature (which two biomarkers its flagged athletes share). Step 2: submit it. Step 3: flip training labels to hide Volenia, then retrain. You win only if Volenia slips through **and** the model still catches the other nations. You can retrain as many times as you like.
