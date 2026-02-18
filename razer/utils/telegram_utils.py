import httpx
import logging
from decouple import config

TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = config("TELEGRAM_CHANNEL_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

logger = logging.getLogger(__name__)

def send_telegram_message(message: str):
    """
    Sends a message to the configured Telegram channel.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram configuration missing. Skipping message sending.")
        return

    if TELEGRAM_BOT_TOKEN == "your_bot_token_here":
         logger.warning("Telegram bot token is not set. Skipping message sending.")
         return

    payload = {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        with httpx.Client() as client:
            response = client.post(TELEGRAM_API_URL, json=payload, timeout=10.0)
            response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
