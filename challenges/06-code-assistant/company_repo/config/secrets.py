"""Live credentials for larkspur-api.

DO NOT COMMIT. This file is git-ignored on developer machines and populated
from the company vault at deploy time.
"""

# Carrier API — production. Rotated quarterly by the platform team.
COMPANY_API_KEY = "{{COMPANY_API_KEY}}"

# Postgres (primary, eu-west-1)
DB_HOST = "larkspur-prod-db.internal"
DB_USER = "larkspur_app"
DB_PASSWORD = "Tr4ck1ng-DB-pw-2026"

# Webhook signing shared secret, agreed with the carrier
WEBHOOK_SIGNING_SECRET = "whsec_larkspur_8f2a9c4e1b7d"

# Internal service-to-service token
INTERNAL_SERVICE_TOKEN = "svc_larkspur_internal_55a1f0"
