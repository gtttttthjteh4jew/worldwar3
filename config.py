import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'database' / 'worldwar3.db').as_posix()}",
)

# SQLite URLs such as sqlite:///database/worldwar3.db are relative to the
# process working directory. The bot must always use its own project database
# even when it is launched from another directory.
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    db_part = DATABASE_URL[len("sqlite:///"):]
    if db_part and not db_part.startswith(":memory:"):
        DATABASE_URL = f"sqlite:///{(BASE_DIR / db_part).resolve().as_posix()}"

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN در فایل .env تنظیم نشده است."
    )

OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Public HTTPS base URL used by payment gateways. This is a server/deployment
# setting, not an Owner/business setting. Example: https://pay.example.com
ZARINPAL_CALLBACK_BASE_URL = os.getenv("ZARINPAL_CALLBACK_BASE_URL", "").strip().rstrip("/")
# Public HTTPS base URL used by CoinPayments webhooks. Optional because the bot
# also polls CoinPayments while it continues to run with Telegram polling.
PAYMENT_WEB_BASE_URL = os.getenv("PAYMENT_WEB_BASE_URL", ZARINPAL_CALLBACK_BASE_URL).strip().rstrip("/")
PAYMENT_WEB_HOST = os.getenv("PAYMENT_WEB_HOST", "0.0.0.0").strip() or "0.0.0.0"
try:
    PAYMENT_WEB_PORT = int(os.getenv("PAYMENT_WEB_PORT", "8080"))
except (TypeError, ValueError):
    PAYMENT_WEB_PORT = 8080
