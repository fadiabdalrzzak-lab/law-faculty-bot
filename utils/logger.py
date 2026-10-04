import logging

logging.basicConfig(
    level=logging.INFO,
    filename="bot.log",
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("LAW_BOT")
