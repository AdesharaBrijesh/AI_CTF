"""FairLend AI: synthetic data, training, prediction and explanations.

The model never sees a protected attribute. It is trained on historical loan
decisions in which applicants from some PIN codes were rejected more often
than their finances justified. A model trained to reproduce those decisions
learns to use PIN code as a proxy, and the explanation panel exposes it.
The proxy hides among decoy fields: bank branch and contact channel had no
effect at all; housing status is a small, legitimate factor.

Everything is built in memory from a fixed seed: no files, trains in
milliseconds, identical on every start.

Explanations are exact linear SHAP values. For a logistic regression with
independent features, a numeric feature's contribution is

    coefficient x (applicant's value - average value)

and for a one-hot categorical field it is

    coef[applicant's value] - sum_k( share_k x coef[value_k] )

so each field gets ONE honest bar, and  base_value + sum(contributions)
equals the model's log-odds exactly.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression

import config

NUMERIC = list(config.NUMERIC_RANGES)
CATEGORICAL = {f: list(opts) for f, opts in config.CATEGORICAL.items()}


class ValidationError(ValueError):
    """Raised for bad form input. The message is safe to show to the player."""


def make_dataset(seed=None, size=None):
    """Synthetic historical decisions. Returns (columns dict, labels)."""
    rng = np.random.default_rng(config.RANDOM_SEED if seed is None else seed)
    n = config.DATASET_SIZE if size is None else size
    cols = {f: rng.uniform(lo, hi, n) for f, (lo, hi) in config.NUMERIC_RANGES.items()}
    for f, opts in CATEGORICAL.items():
        cols[f] = rng.choice(opts, n)

    logit = np.full(n, config.LEGIT_INTERCEPT)
    for f, w in config.LEGIT_WEIGHTS.items():
        x = cols[f]
        logit += w * (x - x.mean()) / x.std()
    for f, effects in config.CATEGORICAL_EFFECTS.items():
        logit += np.array([effects.get(v, 0.0) for v in cols[f]])
    logit += rng.normal(0, config.LABEL_NOISE, n)
    return cols, (logit > 0).astype(int)


class FairLendModel:
    """Standardised numerics + one-hot categoricals -> LogisticRegression."""

    def __init__(self):
        cols, labels = make_dataset()
        self.means = {f: float(cols[f].mean()) for f in NUMERIC}
        self.stds = {f: float(cols[f].std()) for f in NUMERIC}
        self.share = {f: {v: float(np.mean(cols[f] == v)) for v in opts} for f, opts in CATEGORICAL.items()}

        X = self._design(cols)
        self.clf = LogisticRegression(C=1.0, max_iter=2000)
        self.clf.fit(X, labels)
        self.train_accuracy = float(self.clf.score(X, labels))

        coef = list(self.clf.coef_[0])
        self.coef_num = {f: coef.pop(0) for f in NUMERIC}
        self.coef_cat = {f: {v: coef.pop(0) for v in opts} for f, opts in CATEGORICAL.items()}
        self.intercept = float(self.clf.intercept_[0])
        # Expected one-hot contribution per categorical field (its "average" pull).
        self._cat_mean = {f: sum(self.share[f][v] * self.coef_cat[f][v] for v in opts)
                          for f, opts in CATEGORICAL.items()}
        # Base value: log-odds for the "average applicant".
        self.base_value = self.intercept + sum(self._cat_mean.values())

    def _design(self, cols):
        out = [(np.asarray(cols[f], dtype=float) - self.means[f]) / self.stds[f] for f in NUMERIC]
        for f, opts in CATEGORICAL.items():
            values = np.asarray(cols[f])
            out += [(values == v).astype(float) for v in opts]
        return np.column_stack(out)

    def explain(self, app):
        """Decision + per-feature contributions for one validated application."""
        contributions = {}
        for f in NUMERIC:
            contributions[f] = float(self.coef_num[f] * (app[f] - self.means[f]) / self.stds[f])
        for f in CATEGORICAL:
            contributions[f] = float(self.coef_cat[f][app[f]] - self._cat_mean[f])

        logit = self.base_value + sum(contributions.values())
        probability = float(1.0 / (1.0 + np.exp(-logit)))
        return {
            "approved": probability >= 0.5,
            "probability": probability,
            "base_value": self.base_value,
            "logit": logit,
            "contributions": contributions,
        }

    def sklearn_logit(self, app):
        """The library's own score, used by the tests to prove explain() is exact."""
        X = self._design({f: [app[f]] for f in list(NUMERIC) + list(CATEGORICAL)})
        return float(self.clf.decision_function(X)[0])


# Order the sentences are written in. FIXED on purpose: sorting by impact
# would hand the player the answer.
EXPLANATION_ORDER = ["income", "employment_years", "loan_amount", "credit_score", "pin_code"]


def _num(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _strength(contribution):
    """Map a log-odds contribution to words, e.g. 'counted strongly against approval'."""
    size = abs(contribution)
    for limit, words in config.EXPLANATION_BANDS:
        if size < limit:
            break
    if words == config.EXPLANATION_BANDS[0][1]:
        return words
    return f"{words} {'in favour of' if contribution > 0 else 'against'} approval"


def explain_text(app, result):
    """The written explanation: a list of sentences, each a list of segments.

    A segment is {"t": text, "h": True/False}; h marks a highlighted field name.
    No raw numbers or contribution scores are included.
    """
    c = result["contributions"]
    s = {f: _strength(c[f]) for f in EXPLANATION_ORDER}
    area = config.PIN_AREAS[app["pin_code"]]
    H = lambda t: {"t": t, "h": True}
    T = lambda t: {"t": t, "h": False}
    sentences = {
        "income": [H("Annual income"), T(f" of {_num(app['income'])}k {s['income']}.")],
        "employment_years": [H("Years employed"), T(f" ({_num(app['employment_years'])} years) {s['employment_years']}.")],
        "loan_amount": [T("The requested "), H("loan amount"), T(f" of {_num(app['loan_amount'])}k {s['loan_amount']}.")],
        "credit_score": [T("A "), H("credit score"), T(f" of {_num(app['credit_score'])} {s['credit_score']}.")],
        "pin_code": [T("The applicant's "), H("PIN code"), T(f", {app['pin_code']} ({area}), {s['pin_code']}.")],
    }
    return [sentences[f] for f in EXPLANATION_ORDER]


def validate(form):
    """Turn raw form/JSON input into a clean application or raise ValidationError."""
    app = {}
    for f, (lo, hi) in config.NUMERIC_RANGES.items():
        try:
            value = float(form.get(f))
        except (TypeError, ValueError):
            raise ValidationError(f"{config.FEATURE_LABELS[f]} must be a number.")
        if not np.isfinite(value) or not lo <= value <= hi:
            raise ValidationError(f"{config.FEATURE_LABELS[f]} must be between {lo} and {hi}.")
        app[f] = round(value, 2)
    for f, opts in CATEGORICAL.items():
        value = str(form.get(f, "")).strip()
        if value not in opts:
            raise ValidationError(f"Choose a {config.FEATURE_LABELS[f].lower()} from the list.")
        app[f] = value
    return app


MODEL = FairLendModel()
