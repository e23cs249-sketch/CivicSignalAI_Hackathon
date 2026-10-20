import unittest

from app.models import DuplicateCandidate
from app.services.duplicates import find_duplicate_suggestions, jaccard_similarity, normalized_tokens


def candidate(report_id, description, category="broken_streetlight", summary=None):
    return DuplicateCandidate(
        id=report_id,
        description=description,
        category=category,
        summary=summary,
    )


class DuplicateTests(unittest.TestCase):
    def test_jaccard_similarity_uses_token_sets(self):
        self.assertEqual(jaccard_similarity(normalized_tokens("road road damage"), normalized_tokens("road damage")), 1.0)

    def test_general_similarity_threshold_returns_suggestion(self):
        results = find_duplicate_suggestions(
            "streetlight broken cedar street",
            "broken_streetlight",
            [candidate("same", "streetlight broken cedar")],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].match_reason, "similar description keywords detected")

    def test_matching_category_threshold_returns_suggestion(self):
        results = find_duplicate_suggestions(
            "streetlight out cedar block",
            "broken_streetlight",
            [candidate("near", "streetlight out pole")],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].match_reason, "same category and overlapping description keywords")

    def test_category_mismatch_requires_general_threshold(self):
        results = find_duplicate_suggestions(
            "streetlight broken cedar",
            "broken_streetlight",
            [candidate("other", "streetlight broken cedar", category="damaged_road")],
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].match_reason, "similar description keywords detected")

    def test_results_are_sorted_by_similarity_then_id(self):
        results = find_duplicate_suggestions(
            "streetlight broken cedar road",
            "broken_streetlight",
            [
                candidate("z", "streetlight broken cedar"),
                candidate("b", "streetlight broken road"),
                candidate("a", "streetlight broken cedar"),
            ],
        )
        self.assertEqual([item.id for item in results], ["a", "b", "z"])

    def test_duplicate_suggestions_return_required_fields_and_fallback_summary(self):
        results = find_duplicate_suggestions(
            "water leak pipe",
            "water_leak",
            [candidate("report-1", "pipe water leak", category="water_leak")],
        )
        self.assertEqual(results[0].id, "report-1")
        self.assertEqual(results[0].summary, "pipe water leak")
        self.assertIsNotNone(results[0].match_reason)

