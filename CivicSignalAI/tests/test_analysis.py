import unittest

from app.services.analysis import analyze_report


class AnalysisTests(unittest.TestCase):
    def test_summary_uses_first_sentence(self):
        result = analyze_report(
            "  The streetlight is out. It has been dark for days.  ",
            "Cedar Street",
        )
        self.assertEqual(result.summary, "The streetlight is out.")

    def test_summary_uses_full_description_without_sentence_ending(self):
        result = analyze_report("Water leaking beside the road", None)
        self.assertEqual(result.summary, "Water leaking beside the road")

    def test_category_suggestion_returns_single_matching_category(self):
        result = analyze_report("Overflowing garbage near the park", "Park entrance")
        self.assertEqual(result.category_suggestion, "overflowing_garbage")

    def test_ambiguous_or_missing_category_suggestion_is_null(self):
        ambiguous = analyze_report("Garbage beside a damaged road", "Corner")
        unmatched = analyze_report("Something needs attention", "Corner")
        self.assertIsNone(ambiguous.category_suggestion)
        self.assertIsNone(unmatched.category_suggestion)

    def test_priority_precedence_is_high_then_medium_then_low(self):
        result = analyze_report("Minor leak with an exposed wire", None)
        self.assertEqual(result.priority_hint, "high")

    def test_priority_returns_null_without_a_priority_term(self):
        result = analyze_report("Garbage collection area", None)
        self.assertIsNone(result.priority_hint)

    def test_missing_landmark_prompt_is_returned_only_when_absent(self):
        missing = analyze_report("Streetlight is broken", None)
        present = analyze_report("Streetlight is broken", "Cedar Street")
        self.assertEqual(missing.missing_fields, ["Add a nearby landmark if you can."])
        self.assertEqual(present.missing_fields, [])
