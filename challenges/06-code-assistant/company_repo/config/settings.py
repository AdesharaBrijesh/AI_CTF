"""Non-secret runtime settings for larkspur-api."""
import os

ENV_NAME = os.getenv("LARKSPUR_ENV", "production")
VERSION = "2.4.1"
PORT = int(os.getenv("PORT", "8080"))
DEBUG = os.getenv("LARKSPUR_DEBUG", "0") == "1"

# Carrier integration
CARRIER_API_BASE = "https://api.carrier-partner.example/v3"
CARRIER_TIMEOUT_SECONDS = 15
CARRIER_MAX_RETRIES = 3

# Tracking-number validation
TRACKING_PREFIXES = ("LRK", "LKS", "LRKX")
TRACKING_LENGTH = 14

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Rate limiting (requests per minute, per API consumer)
RATE_LIMIT_DEFAULT = 600
RATE_LIMIT_WEBHOOK = 3000
