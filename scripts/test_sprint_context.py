"""Behavior checks for next-task selection; no application dependencies."""

import unittest

from sprint_context import Sprint, select_next


def card(key, dependencies=(), phase="MVP"):
    return Sprint(key, key, f"**Phase:** {phase}\n"
                  f"**Prerequisites:** {', '.join(dependencies) or 'None'}\n")


class NextSprintTests(unittest.TestCase):
    def test_initial_selection_uses_lowest_ready_id_not_dictionary_order(self):
        cards = {"S002": card("S002"), "S001": card("S001")}
        progress = {key: ("TODO", "") for key in cards}
        self.assertEqual(select_next(cards, progress), ("S001", "MVP"))

    def test_resume_ready_work_before_starting_another_card(self):
        cards = {"S001": card("S001"), "S002": card("S002")}
        progress = {"S001": ("TODO", ""), "S002": ("IN_PROGRESS", "partial work")}
        self.assertEqual(select_next(cards, progress), ("S002", "MVP"))

    def test_blocked_card_and_its_dependent_are_skipped(self):
        cards = {"S001": card("S001"), "S002": card("S002", ["S001"]),
                 "S003": card("S003")}
        progress = {"S001": ("BLOCKED", "external input"),
                    "S002": ("TODO", ""), "S003": ("TODO", "")}
        self.assertEqual(select_next(cards, progress), ("S003", "MVP"))

    def test_in_progress_with_unfinished_dependency_cannot_resume(self):
        cards = {"S001": card("S001"), "S002": card("S002", ["S001"])}
        progress = {"S001": ("TODO", ""), "S002": ("IN_PROGRESS", "stale status")}
        self.assertEqual(select_next(cards, progress), ("S001", "MVP"))

    def test_completed_work_is_not_selected_again(self):
        cards = {"S001": card("S001"), "S002": card("S002", ["S001"])}
        progress = {"S001": ("DONE", "verified"), "S002": ("TODO", "")}
        self.assertEqual(select_next(cards, progress), ("S002", "MVP"))

    def test_do_not_cross_an_unfinished_phase(self):
        cards = {"S001": card("S001"), "S094": card("S094", phase="Phase 2")}
        progress = {"S001": ("BLOCKED", "external input"), "S094": ("TODO", "")}
        self.assertEqual(select_next(cards, progress), (None, "MVP"))

    def test_advance_phase_after_previous_phase_is_done(self):
        cards = {"S001": card("S001"), "S094": card("S094", phase="Phase 2")}
        progress = {"S001": ("DONE", "verified"), "S094": ("TODO", "")}
        self.assertEqual(select_next(cards, progress), ("S094", "Phase 2"))

    def test_all_done_and_no_mutation(self):
        cards = {"S001": card("S001")}
        progress = {"S001": ("DONE", "verified")}
        before = dict(progress)
        self.assertEqual(select_next(cards, progress), (None, None))
        self.assertEqual(progress, before)

    def test_split_parent_waits_for_its_children(self):
        cards = {"S043": card("S043", ["S043A", "S043B"]),
                 "S043A": card("S043A"), "S043B": card("S043B", ["S043A"])}
        progress = {key: ("TODO", "") for key in cards}
        self.assertEqual(select_next(cards, progress), ("S043A", "MVP"))


if __name__ == "__main__":
    unittest.main()
