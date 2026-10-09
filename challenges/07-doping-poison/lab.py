"""Synthetic dataset, classifier training and attack evaluation.

Everything here is deterministic for a given config.SEED, so every player sees
the same records and the same baseline model.
"""
import numpy as np
from sklearn.tree import DecisionTreeClassifier

import config

FEATURES = [b[0] for b in config.BIOMARKERS]
_MEAN = {b[0]: b[3] for b in config.BIOMARKERS}
_STD = {b[0]: b[4] for b in config.BIOMARKERS}

CLEAN, DOPED = 0, 1


def _generate():
    """Build the full sample list: dicts with id, nation, markers, label."""
    rng = np.random.default_rng(config.SEED)
    samples = []
    for nation, signature in config.SIGNATURES.items():
        n_doped = int(round(config.SAMPLES_PER_NATION * config.DOPED_FRACTION))
        for i in range(config.SAMPLES_PER_NATION):
            doped = i < n_doped
            row = {"nation": nation, "label": DOPED if doped else CLEAN}
            for f in FEATURES:
                v = rng.normal(_MEAN[f], _STD[f])
                if doped and f in signature:
                    v += config.SIGNATURE_SHIFT * _STD[f]
                row[f] = round(float(v), 1)
            samples.append(row)
    order = rng.permutation(len(samples))
    samples = [samples[i] for i in order]
    for i, s in enumerate(samples):
        s["id"] = i
    return samples


SAMPLES = _generate()
_n_test = int(len(SAMPLES) * config.TEST_FRACTION)
TEST = SAMPLES[:_n_test]
TRAIN = SAMPLES[_n_test:]
TRAIN_IDS = {s["id"] for s in TRAIN}


def _matrix(rows):
    return np.array([[r[f] for f in FEATURES] for r in rows])


def train(labels_by_id=None):
    """Fit the classifier on TRAIN, optionally with some labels overridden."""
    labels_by_id = labels_by_id or {}
    y = np.array([labels_by_id.get(s["id"], s["label"]) for s in TRAIN])
    model = DecisionTreeClassifier(max_depth=config.MODEL_MAX_DEPTH,
                                   random_state=config.SEED)
    model.fit(_matrix(TRAIN), y)
    return model


def evaluate(model):
    """Per-nation detection rates plus the two win-condition metrics."""
    preds = model.predict(_matrix(TEST))
    per_nation = {}
    other_correct = other_total = 0
    for nation in config.SIGNATURES:
        idx = [i for i, s in enumerate(TEST) if s["nation"] == nation]
        doped = [i for i in idx if TEST[i]["label"] == DOPED]
        detected = sum(1 for i in doped if preds[i] == DOPED)
        correct = sum(1 for i in idx if preds[i] == TEST[i]["label"])
        per_nation[nation] = {
            "doped": len(doped),
            "detected": detected,
            "detection_rate": detected / len(doped) if doped else 0.0,
            "accuracy": correct / len(idx) if idx else 0.0,
        }
        if nation != config.TARGET_NATION:
            other_correct += correct
            other_total += len(idx)
    return {
        "per_nation": per_nation,
        "target_detection": per_nation[config.TARGET_NATION]["detection_rate"],
        "other_accuracy": other_correct / other_total if other_total else 0.0,
    }


BASELINE_MODEL = train()
BASELINE = evaluate(BASELINE_MODEL)


def recon_rows():
    """A readable slice of the test set with the BASELINE model's verdicts.

    Ground-truth labels are deliberately not shown: the player reads the lab's
    verdicts, as an outsider would.
    """
    preds = BASELINE_MODEL.predict(_matrix(TEST))
    shown = {n: 0 for n in config.SIGNATURES}
    rows = []
    for s, p in zip(TEST, preds):
        if shown[s["nation"]] >= config.RECON_ROWS_PER_NATION:
            continue
        shown[s["nation"]] += 1
        rows.append({**{f: s[f] for f in FEATURES},
                     "id": s["id"], "nation": s["nation"],
                     "verdict": "Suspicious" if p == DOPED else "Clean"})
    return rows


def train_rows():
    """The poisonable training set, with its current (true) labels."""
    return [{**{f: s[f] for f in FEATURES},
             "id": s["id"], "nation": s["nation"],
             "label": "Suspicious" if s["label"] == DOPED else "Clean"}
            for s in TRAIN]


def signature_matches(markers):
    """Server-side check of the player's guess at Volenia's signature."""
    return set(markers or []) == set(config.SIGNATURES[config.TARGET_NATION])


def attack(flip_ids):
    """Retrain with the given training labels flipped and judge the attack.

    Returns a result dict; result["won"] is True only when Volenia evades AND
    the other nations are still policed. The flag is attached by the caller.
    """
    flips = {}
    by_id = {s["id"]: s for s in TRAIN}
    for i in flip_ids:
        s = by_id[i]
        flips[i] = CLEAN if s["label"] == DOPED else DOPED
    result = evaluate(train(flips))
    evaded = result["target_detection"] <= config.TARGET_MAX_DETECTION
    intact = result["other_accuracy"] >= config.OTHER_ACCURACY_THRESHOLD
    result["evaded"] = evaded
    result["intact"] = intact
    result["won"] = evaded and intact
    if result["won"]:
        result["verdict"] = (f"{config.TARGET_NATION} now passes as clean, and "
                             "the model still catches everyone else.")
    elif not intact:
        result["verdict"] = ("Model accuracy collapsed - you poisoned too "
                             "broadly. Other nations are slipping through too, "
                             "so the lab would notice.")
    else:
        result["verdict"] = (f"{config.TARGET_NATION} is still detected. The "
                             "model has not learned that its pattern is clean.")
    return result
