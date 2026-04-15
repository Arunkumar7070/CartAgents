import logging
import sys


def setup_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "\n%(levelname)s | %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
