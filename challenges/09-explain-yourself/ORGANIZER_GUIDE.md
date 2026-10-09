# 09 · explain-yourself — Organizer Guide

> **CONFIDENTIAL — facilitators only.** Contains the solution.

**Player goal:** prove that FairLend AI uses **PIN code** as a proxy for a protected
group. They must name the feature **and** submit two applications from their own history
that are identical except for PIN code but got opposite decisions.

## Solution

1. The pre-filled application (income 120, credit score 740, loan 45, 10 years, PIN
   `900437 · Central`) is strong, so it's **approved in every area**. Changing only the PIN
   on it proves nothing. Players need a **borderline** application.
2. Lower the finances until the decision sits near 50%. A reliable one: **income 40**,
   credit score 740, loan 45, 10 years, PIN `900437 · Central` → **Approved (~68%)**.
3. Change **only** the PIN code to `900101 · Old Harbour` (or `900214 · Millbrook`) and
   resubmit → **Rejected (~5%)**. Comparing the two explanations, every sentence is the
   same except the PIN code one, which goes from "counted slightly in favour of approval"
   (Central) to "counted strongly against approval" (Old Harbour).
4. In **File your finding**: choose **PIN code**, pick those two IDs as Evidence A and B,
   and submit. The Status box shows the flag.

## What players will try, and what they'll see

| Attempt | Reply |
|---|---|
| Accuse a feature with no evidence, or bad evidence | The same evidence message for **every** feature, so guessing by name reveals nothing |
| Valid flip pair for a legitimate field (e.g. credit score 740 → 400) | "Your evidence is valid, but credit score is a legitimate lending factor…" |
| Pair that differs in more than one field, or same decision twice | Explains what the evidence needs |
| PIN code + valid pair | Flag |

## Helping stuck teams

1. Point them at the hints in the right panel (three, revealed one at a time).
2. "Your strong application is approved everywhere. What happens if it's borderline?"
3. "Read the two explanations side by side. Which sentence changed?"
4. "Should where someone lives decide whether they're creditworthy?"

## Debrief points

- Removing protected attributes is **not** enough: correlated features (location, school,
  shopping habits) can reintroduce the same bias. This is called proxy discrimination.
- The bias came from **historical decisions**, not malicious code. Models faithfully learn
  whatever unfairness is in their training data.
- Explainability made the problem visible. Without explanations, the bank's "we don't use
  protected attributes" claim would have gone unchallenged.
- A finding needs **evidence**: a controlled pair where only one thing changes. That's how
  real fairness audits work.

## Tuning

If teams find it too fast, lower `PROXY_PENALTY` / `PROXY_BOOST` in `config.py`, so fewer
applications flip. If nobody finds it, raise them. Run `python -m unittest test_app`
afterwards; the tests assume the reference borderline application still flips.
