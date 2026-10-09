"""Tests for doping-poison (no network, no LLM).

    python -m unittest test_app
"""
import unittest

import app
import config
import lab


def volenia_doped_train_ids():
    return [s["id"] for s in lab.TRAIN
            if s["nation"] == config.TARGET_NATION and s["label"] == lab.DOPED]


def doped_train_ids(nations):
    return [s["id"] for s in lab.TRAIN
            if s["label"] == lab.DOPED and s["nation"] in nations]


class Signature(unittest.TestCase):
    def test_correct_signature_matches(self):
        self.assertTrue(lab.signature_matches(
            list(config.SIGNATURES[config.TARGET_NATION])))

    def test_wrong_signature_rejected(self):
        self.assertFalse(lab.signature_matches(["testosterone", "hgb"]))
        self.assertFalse(lab.signature_matches(["epo"]))
        self.assertFalse(lab.signature_matches([]))


class Attack(unittest.TestCase):
    def test_correct_volenia_flip_wins(self):
        result = lab.attack(volenia_doped_train_ids())
        self.assertTrue(result["evaded"], result)
        self.assertTrue(result["intact"], result)
        self.assertTrue(result["won"])

    def test_no_flips_does_not_win(self):
        self.assertFalse(lab.attack([])["won"])

    def test_over_poisoning_collapses_accuracy(self):
        # Flip Volenia AND a nation that shares one marker: accuracy guard fails.
        result = lab.attack(doped_train_ids(("Volenia", "Morravia")))
        self.assertFalse(result["intact"])
        self.assertFalse(result["won"])
        self.assertIn("collapsed", result["verdict"])

    def test_baseline_catches_volenia(self):
        # Sanity: before poisoning, Volenia is actually detected well.
        self.assertGreater(lab.BASELINE["target_detection"], 0.5)


class RetrainRoute(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def _identify(self):
        return self.client.post("/identify", json={
            "markers": list(config.SIGNATURES[config.TARGET_NATION])})

    def test_retrain_blocked_before_identify(self):
        r = self.client.post("/retrain", json={"flips": []})
        self.assertEqual(r.status_code, 403)

    def test_identify_then_win_returns_flag(self):
        self._identify()
        r = self.client.post("/retrain", json={"flips": volenia_doped_train_ids()})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["won"])
        self.assertEqual(data["flag"], config.FLAG)

    def test_identify_then_normal_run_withholds_flag(self):
        self._identify()
        data = self.client.post("/retrain", json={"flips": []}).get_json()
        self.assertFalse(data["won"])
        self.assertNotIn("flag", data)

    def test_over_budget_rejected(self):
        self._identify()
        too_many = [s["id"] for s in lab.TRAIN][: config.MAX_FLIPS + 5]
        r = self.client.post("/retrain", json={"flips": too_many})
        self.assertEqual(r.status_code, 400)

    def test_identify_rejects_wrong_signature(self):
        data = self.client.post("/identify", json={
            "markers": ["testosterone", "hgb"]}).get_json()
        self.assertFalse(data["ok"])


class PageLeakage(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def test_flag_absent_from_all_pages(self):
        # Reach poison.html by identifying first (cookie carries the unlock).
        self.client.post("/identify", json={
            "markers": list(config.SIGNATURES[config.TARGET_NATION])})
        for path in ("/", "/recon", "/poison", "/health"):
            body = self.client.get(path).get_data(as_text=True)
            self.assertNotIn(config.FLAG, body, path)

    def test_recon_hides_ground_truth_labels(self):
        body = self.client.get("/recon").get_data(as_text=True)
        # Verdicts are shown, but the words tying a row to its true label
        # ("doped"/"clean" ground truth) are not leaked as a data attribute.
        self.assertNotIn("data-label", body)


class Dataset(unittest.TestCase):
    def test_enough_samples(self):
        self.assertGreaterEqual(len(lab.SAMPLES), 300)

    def test_deterministic(self):
        self.assertEqual(lab.SAMPLES[0]["id"], 0)
        first = lab._generate()[0]
        self.assertEqual(first["nation"], lab.SAMPLES[0]["nation"])

    def test_train_test_disjoint(self):
        self.assertTrue(lab.TRAIN_IDS.isdisjoint({s["id"] for s in lab.TEST}))


if __name__ == "__main__":
    unittest.main()
