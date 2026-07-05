import asyncio
import logging
import threading

from bot_code import run_bot
from web_app import LOG_PATH, app, ensure_db


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def start_bot():
    try:
        asyncio.run(run_bot())
    except Exception:
        logging.exception("Telegram bot stopped with an error")


def main():
    configure_logging()
    ensure_db()

    bot_thread = threading.Thread(target=start_bot, name="telegram-bot", daemon=True)
    bot_thread.start()

    logging.info("Web: Flask app started at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
