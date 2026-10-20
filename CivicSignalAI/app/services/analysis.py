import re

from app.models import RuleAnalysis
from app.utils.labels import (
    CATEGORY_ALIASES,
    HIGH_PRIORITY_TERMS,
    LOW_PRIORITY_TERMS,
    MEDIUM_PRIORITY_TERMS,
)


def _tokens(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value.lower(), flags=re.UNICODE)


def _contains_phrase(tokens: list[str], phrase: str) -> bool:
    phrase_tokens = _tokens(phrase)
    if not phrase_tokens or len(phrase_tokens) > len(tokens):
        return False
    width = len(phrase_tokens)
    return any(tokens[index:index + width] == phrase_tokens for index in range(len(tokens) - width + 1))


def _first_sentence(description: str) -> str:
    normalized = " ".join(description.split())
    pieces = re.split(r"(?<=[.!?])\s+", normalized, maxsplit=1)
    return pieces[0].strip()


def analyze_report(description: str, landmark: str | None) -> RuleAnalysis:
    normalized_description = " ".join(description.split())
    tokens = _tokens(normalized_description)
    if not tokens:
        raise ValueError("description must contain text")

    matched_categories = [
        category.value
        for category, aliases in CATEGORY_ALIASES.items()
        if any(_contains_phrase(tokens, alias) for alias in aliases)
    ]
    category_suggestion = matched_categories[0] if len(matched_categories) == 1 else None

    if any(_contains_phrase(tokens, term) for term in HIGH_PRIORITY_TERMS):
        priority_hint = "high"
    elif any(_contains_phrase(tokens, term) for term in MEDIUM_PRIORITY_TERMS):
        priority_hint = "medium"
    elif any(_contains_phrase(tokens, term) for term in LOW_PRIORITY_TERMS):
        priority_hint = "low"
    else:
        priority_hint = None

    missing_fields = [] if landmark else ["Add a nearby landmark if you can."]
    return RuleAnalysis(
        summary=_first_sentence(normalized_description),
        category_suggestion=category_suggestion,
        priority_hint=priority_hint,
        missing_fields=missing_fields,
    )
