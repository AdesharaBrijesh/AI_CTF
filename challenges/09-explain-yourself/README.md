# Challenge 09 — explain-yourself

**Explainable AI audit → hidden proxy discrimination.** Difficulty: Intermediate.
No LLM, no Ollama.

"FairLend AI" approves or rejects loan applications and claims to be fair because
protected attributes (race, gender, religion) were removed from its data. The player is
an auditor. By reading the model's **written explanations** for applications they
submit, they must discover that **PIN code** is secretly acting as a stand-in for a
protected group, and prove it with evidence.

| | |
|---|---|
| Image | `aictf/09-explain-yourself:1.0` |
| Host port | **5009** (container listens on 8000) |
| Model | scikit-learn LogisticRegression, trained in memory at startup (milliseconds, fixed seed) |
| Flag | `FLAG` in `.env` (git-ignored); the committed default is a placeholder |
| Health | `GET /health` |
| Solution | [ORGANIZER_GUIDE.md](ORGANIZER_GUIDE.md) (facilitators only) |

## What it teaches

- **Explainable AI (XAI):** reading why a model made a decision.
- **Proxy discrimination / digital redlining:** deleting a protected attribute doesn't
  remove bias when another feature carries the same information. Here, past lending
  decisions penalised certain neighbourhoods, so a model trained on them learns to use
  PIN code as a stand-in.
- **Responsible-AI auditing:** testing a model with controlled, side-by-side inputs
  instead of trusting the vendor's claims, and backing a finding with evidence.

## How it works

1. `model.py` builds a synthetic history of 2,000 loan decisions from a fixed seed.
   Approval depends on income, credit score, loan amount and years employed, **plus** a
   penalty for two "disadvantaged" PIN codes and a boost for two "favoured" ones.
2. A LogisticRegression is trained on that history. It never sees a protected
   attribute, but it learns a real weight for PIN code.
3. For every application the workbench shows Approved/Rejected and a **written
   explanation**: one sentence per field, in a fixed order, with the field names
   highlighted, e.g. *"The applicant's PIN code, 900101 (Old Harbour), counted strongly
   against approval."* Strength is given in words from exact per-feature contributions
   (linear SHAP values). Raw scores never reach the browser, so players must read and
   compare, not sort numbers.
4. The proxy is subtle: a strong application is approved in **every** area. PIN code
   only tips applications near the 50% line, so players must build a borderline case.
5. The player names a feature and picks two applications from their own history as
   evidence. The server checks, against the history it recorded for that session, that
   they are identical except for the accused field and got opposite decisions, before
   saying anything about the feature itself (so the form can't be used to guess).

All places, codes and data are fictional ("Lumen City").

## Run it

### Docker (repo convention)
```
copy .env.example .env          # set the real FLAG
docker build -t aictf/09-explain-yourself:1.0 .
docker run -d --name explain-yourself -p 5009:8000 --env-file .env aictf/09-explain-yourself:1.0
```
No Ollama and no data volume are needed: the model is rebuilt in memory at every start.

### Python
```
python -m venv venv
venv\Scripts\activate           # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env          # keep PORT=5009, set the real FLAG
python run.py
```
Open http://localhost:5009 (players use `http://<host-IP>:5009`; open port 5009 in the firewall).

## Configure (top of `config.py`)

| Setting | What it does |
|---|---|
| `FLAG` | the flag (set it in `.env`) |
| `PROXY_FEATURE` | the answer the server accepts (`pin_code`) |
| `PIN_AREAS` | the PIN codes and area names in the dropdown |
| `DISADVANTAGED_PINS`, `FAVOURED_PINS` | which areas the historical data penalised / favoured |
| `PROXY_PENALTY`, `PROXY_BOOST` | strength of the proxy (log-odds). Raise if players can't find it; lower if it's too obvious |
| `EXPLANATION_BANDS` | thresholds for "little difference / slightly / moderately / strongly / very strongly" |
| `DEFAULT_APPLICATION` | the pre-filled application (strong, approved everywhere) |
| `DATASET_SIZE`, `RANDOM_SEED`, `LABEL_NOISE`, `LEGIT_WEIGHTS` | the synthetic training data |

## Test
```
python -m unittest test_app
```
16 tests: a strong application is approved in every area; PIN code flips borderline
applications; explanations are exact, in a fixed order, with highlighted fields and no
leaked scores; PIN code with valid evidence returns the flag; other features and weak or
foreign evidence don't; the finding form isn't a guessing oracle; the flag never appears in
served pages.

## Files

- `config.py`: flag, proxy definition, effect strength, explanation wording, dataset settings
- `model.py`: synthetic data, training, exact contributions, written explanation, validation
- `app.py`: Flask routes (`/`, `/audit`, `/predict`, `/accuse`, `/health`)
- `run.py`: trains the model, prints the banner, serves with waitress
- `templates/brief.html`, `templates/audit.html`: briefing and audit workbench
- `test_app.py`: tests
- `ORGANIZER_GUIDE.md`: solution and facilitation notes
