# larkspur-api

Internal shipment-tracking API for **Larkspur Logistics**. Flask service behind
the warehouse dashboard and the customer tracking page.

## Layout
```
app.py                  service entrypoint, blueprint registration
config/settings.py      non-secret runtime settings
config/secrets.py       live credentials  (DO NOT COMMIT REAL VALUES)
routes/shipments.py     shipment CRUD + tracking lookups
routes/webhooks.py      inbound carrier status callbacks
utils/auth.py           request signing against the carrier API
utils/formatting.py     tracking-number normalisation helpers
tests/test_shipments.py route tests (uses fixture credentials)
requirements.txt
```

## Local setup
```
python -m venv venv
pip install -r requirements.txt
cp config/secrets.example.py config/secrets.py   # then fill in real values
python app.py
```

## Credentials policy
Production credentials live in the **company vault** (`vault.larkspur.internal`),
never in source control. `config/secrets.py` is git-ignored on developer
machines. If you need the live carrier key for debugging, request a short-lived
token from the platform team — do not copy the production key locally.

Rotation: the carrier API key is rotated quarterly. The previous key is kept
commented in `utils/auth.py` for one cycle in case a rollback is needed, then
deleted.
