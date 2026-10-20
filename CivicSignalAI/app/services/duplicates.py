import re
from collections.abc import Sequence

from app.models import DuplicateCandidate, DuplicateSuggestion


CATEGORY_MATCH_THRESHOLD = 0.30
GENERAL_MATCH_THRESHOLD = 0.50


def normalized_tokens(description: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", description.lower(), flags=re.UNICODE))


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def find_duplicate_suggestions(
    description: str,
    category: str,
    existing_reports: Sequence[DuplicateCandidate],
) -> list[DuplicateSuggestion]:
    new_tokens = normalized_tokens(description)
    matches: list[tuple[float, DuplicateSuggestion]] = []

    for report in existing_reports:
        score = jaccard_similarity(new_tokens, normalized_tokens(report.description))
        same_category = report.category == category
        if score >= GENERAL_MATCH_THRESHOLD:
            reason = "similar description keywords detected"
        elif same_category and score >= CATEGORY_MATCH_THRESHOLD:
            reason = "same category and overlapping description keywords"
        else:
            continue
        matches.append(
            (
                score,
                DuplicateSuggestion(
                    id=report.id,
                    summary=report.summary or report.description,
                    match_reason=reason,
                ),
            )
        )

    matches.sort(key=lambda item: (-item[0], item[1].id))
    return [suggestion for _, suggestion in matches]
