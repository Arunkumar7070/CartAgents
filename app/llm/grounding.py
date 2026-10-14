import re

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_CLAUSE_REFERENCE = re.compile(r"§\d+")


def _numbers(text: str) -> list[str]:
    return _NUMBER.findall(_CLAUSE_REFERENCE.sub("", text))


def _value(number: str) -> float:
    return float(number.replace(",", ""))


def ungrounded_numbers(answer: str, evidence: str) -> list[str]:
    known = {_value(n) for n in _numbers(evidence)}
    return [n for n in _numbers(answer) if _value(n) not in known]
