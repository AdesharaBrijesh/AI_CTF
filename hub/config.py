import os

EVENT_NAME = os.environ.get("EVENT_NAME", "AI Security CTF")
SECRET_KEY = os.environ.get("HUB_SECRET_KEY", "change-me-hub-secret")
ADMIN_PASSWORD = os.environ.get("HUB_ADMIN_PASSWORD", "admin")
DB_PATH = os.environ.get("HUB_DB_PATH", "/data/hub.db")

# Maps challenge id → env var name for its flag
FLAG_ENV = {
    "c01-l1":  "C01_FLAG_L1",
    "c01-l2":  "C01_FLAG_L2",
    "c01-l3":  "C01_FLAG_L3",
    "c01-l4":  "C01_FLAG_L4",
    "c01-l5":  "C01_FLAG_L5",
    "c02":     "C02_FLAG",
    "c03":     "C03_FLAG",
    "c04":     "C04_FLAG",
    "c05":     "C05_FLAG",
    "c06":     "C06_FLAG",
    "c07":     "C07_FLAG",
    "c08-l1":  "C08_FLAG_L1",
    "c08-l2":  "C08_FLAG_L2",
    "c08-l3":  "C08_FLAG_L3",
    "c08-l4":  "C08_FLAG_L4",
    "c08-l5":  "C08_FLAG_L5",
    "c08-l6":  "C08_FLAG_L6",
    "c08-l7":  "C08_FLAG_L7",
    "c08-l8":  "C08_FLAG_L8",
    "c08-l9":  "C08_FLAG_L9",
    "c08-l10": "C08_FLAG_L10",
    "c09":     "C09_FLAG",
}


def get_flag(cid: str) -> str:
    env_name = FLAG_ENV.get(cid, "")
    return os.environ.get(env_name, "").strip()
