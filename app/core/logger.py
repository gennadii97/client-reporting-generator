import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    level="INFO",
    serialize=False,
    # serialize=True — выводит JSON. Удобно на проде где логи
    # собирает Datadog или ELK. False — читаемый формат для разработки.
)

logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)