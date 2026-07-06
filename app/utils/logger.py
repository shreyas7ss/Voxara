from loguru import logger
import sys, os

ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logger.remove()

if ENV == "production":
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/voxara.log",
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        serialize=True
    )
else:
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}"
    )
