import re
from typing import Literal

Confirmation = Literal["confirm", "cancel", "unclear"]

_CONFIRM_WORDS = frozenset(
    {"yes", "y", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm", "confirmed", "go", "proceed", "place"}
)
_CANCEL_WORDS = frozenset(
    {"no", "not", "n", "nope", "nah", "cancel", "stop", "abort", "don't", "dont", "never"}
)


def parse_confirmation(message: str) -> Confirmation:
    words = set(re.findall(r"[a-z']+", message.lower()))
    says_yes = bool(words & _CONFIRM_WORDS)
    says_no = bool(words & _CANCEL_WORDS)
    if says_yes == says_no:
        return "unclear"
    return "confirm" if says_yes else "cancel"
