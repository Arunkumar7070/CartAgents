import hashlib
import logging
import sys


def setup_logger(name: str = "agent") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s"))
        logger.addHandler(handler)

    return logger


def session_ref(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()[:10]
