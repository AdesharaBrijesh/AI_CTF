"""Tests for explain-yourself (no network, no LLM).

    python -m unittest test_app
"""
import unittest

import app
import config
import model

STRONG = {"income": 120, "credit_score": 740, "loan_amount": 45, "employment_years": 10}
BORDER = {"income": 40, "credit_score": 740, "loan_amount": 45, "employment_years": 10}
NEUTRAL_PIN = "900437"
DISADVANTAGED_PIN = config.DISADVANTAGED_PINS[0]
FAVOURED_PIN = config.FAVOURED_PINS[0]


class ModelBehaviour(unittest.TestCase):
    def test_strong_application_is_approved_in_every_area(self):
        # No giveaway: changing only the PIN on a strong application never flips it.
        for pin in config.PIN_AREAS:
            self.assertTrue(model.MODEL.explain(dict(STRONG, pin_code=pin))["approved"], pin)

    def test_pin_code_flips_identical_borderline_applications(self):
        self.assertTrue(model.MODEL.explain(dict(BORDER, pin_code=NEUTRAL_PIN))["approved"])
        self.assertFalse(model.MODEL.explain(dict(BORDER, pin_code=DISADVANTAGED_PIN))["approved"])

    def test_explanation_is_exact(self):
        # base value + contributions must equal sklearn's own log-odds.
        for pin in config.PIN_AREAS:
            a = dict(BORDER, pin_code=pin)
            self.assertAlmostEqual(model.MODEL.explain(a)["logit"], model.MODEL.sklearn_logit(a), places=9)

    def test_training_is_reproducible(self):
        self.assertEqual(model.FairLendModel().coef_cat, model.MODEL.coef_cat)


class WrittenExplanation(unittest.TestCase):
    def text(self, app):
        sentences = model.explain_text(app, model.MODEL.explain(app))
        return [("".join(seg["t"] for seg in sent), [seg["t"] for seg in sent if seg["h"]]) for sent in sentences]

    def test_fixed_order_and_highlighted_fields(self):
        sents = self.text(dict(BORDER, pin_code=DISADVANTAGED_PIN))
        self.assertEqual([h for _, h in sents],
                         [["Annual income"], ["Years employed"], ["loan amount"], ["credit score"], ["PIN code"]])

    def test_pin_sentence_reflects_the_proxy(self):
        bad = self.text(dict(BORDER, pin_code=DISADVANTAGED_PIN))[-1][0]
        self.assertIn("strongly against approval", bad)
        self.assertIn(config.PIN_AREAS[DISADVANTAGED_PIN], bad)

    def test_no_numbers_or_scores_leak(self):
        for text, _ in self.text(dict(BORDER, pin_code=DISADVANTAGED_PIN)):
            self.assertNotRegex(text, r"[+-]\d\.\d")   # no signed scores like -2.99


class Validation(unittest.TestCase):
    def test_rejects_out_of_range_and_bad_pin(self):
        with self.assertRaises(model.ValidationError):
            model.validate(dict(STRONG, credit_score=2000, pin_code=NEUTRAL_PIN))
        with self.assertRaises(model.ValidationError):
            model.validate(dict(STRONG, income="lots", pin_code=NEUTRAL_PIN))
        with self.assertRaises(model.ValidationError):
            model.validate(dict(STRONG, pin_code="123456"))


class AuditFlow(unittest.TestCase):
    def setUp(self):
        app.app.config["TESTING"] = True
        self.client = app.app.test_client()

    def submit(self, **fields):
        r = self.client.post("/predict", json=fields)
        self.assertEqual(r.status_code, 200, r.get_json())
        return r.get_json()["application"]

    def accuse(self, feature, a, b):
        return self.client.post("/accuse", json={"feature": feature, "proof_a": a, "proof_b": b}).get_json()

    def test_naming_pin_code_with_valid_proof_returns_flag(self):
        a = self.submit(**BORDER, pin_code=NEUTRAL_PIN)
        b = self.submit(**BORDER, pin_code=DISADVANTAGED_PIN)
        self.assertNotEqual(a["approved"], b["approved"])
        res = self.accuse("pin_code", a["id"], b["id"])
        self.assertTrue(res["correct"])
        self.assertEqual(res["flag"], config.FLAG)

    def test_naming_another_feature_does_not_return_flag(self):
        # A genuine flip caused by a legitimate feature is still the wrong answer.
        a = self.submit(**STRONG, pin_code=NEUTRAL_PIN)
        b = self.submit(**dict(STRONG, credit_score=400), pin_code=NEUTRAL_PIN)
        self.assertNotEqual(a["approved"], b["approved"])
        for feature in ("credit_score", "income", "loan_amount", "employment_years"):
            res = self.accuse(feature, a["id"], b["id"])
            self.assertFalse(res["correct"])
            self.assertNotIn("flag", res)

    def test_right_feature_with_bad_evidence_is_rejected(self):
        a = self.submit(**STRONG, pin_code=NEUTRAL_PIN)
        same = self.submit(**STRONG, pin_code=FAVOURED_PIN)          # both approved
        other = self.submit(**dict(STRONG, income=30), pin_code=DISADVANTAGED_PIN)  # 2 fields differ
        for x, y in [(a["id"], same["id"]), (a["id"], other["id"]), (a["id"], a["id"]),
                     (a["id"], "APP-999"), ("", "")]:
            res = self.accuse("pin_code", x, y)
            self.assertFalse(res["correct"], (x, y))
            self.assertNotIn("flag", res)

    def test_evidence_must_come_from_own_history(self):
        a = self.submit(**BORDER, pin_code=NEUTRAL_PIN)
        b = self.submit(**BORDER, pin_code=DISADVANTAGED_PIN)
        stranger = app.app.test_client()
        res = stranger.post("/accuse", json={"feature": "pin_code", "proof_a": a["id"], "proof_b": b["id"]}).get_json()
        self.assertFalse(res["correct"])

    def test_flag_and_answer_absent_from_served_pages(self):
        pages = []
        for path in ("/", "/audit", "/static/style.css", "/health"):
            resp = self.client.get(path)
            pages.append(resp.get_data(as_text=True))
            resp.close()
        pages.append(self.client.post("/predict", json=dict(BORDER, pin_code=DISADVANTAGED_PIN)).get_data(as_text=True))
        for body in pages:
            self.assertNotIn(config.FLAG, body)
            self.assertNotIn("DISADVANTAGED", body)
            self.assertNotIn("PROXY_FEATURE", body)

    def test_predict_returns_text_not_scores(self):
        body = self.client.post("/predict", json=dict(BORDER, pin_code=DISADVANTAGED_PIN)).get_json()
        self.assertIn("explanation", body)
        for key in ("contributions", "logit", "base_value"):
            self.assertNotIn(key, body)

    def test_accuse_is_not_an_oracle(self):
        # Without a valid flip pair, every feature gets the SAME reply.
        replies = {self.accuse(f, "", "")["message"] for f in config.FEATURE_LABELS}
        self.assertEqual(len(replies), 1)

    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
