from __future__ import annotations

import unittest

from app.diff_reader import diff_line_count, is_diff_oversized


class DiffReaderTests(unittest.TestCase):
    def test_diff_line_count_counts_lines(self) -> None:
        diff_text = "a\nb\nc\n"
        self.assertEqual(diff_line_count(diff_text), 3)

    def test_is_diff_oversized_respects_limit(self) -> None:
        diff_text = "\n".join(str(i) for i in range(801))
        self.assertTrue(is_diff_oversized(diff_text, max_lines=800))
        self.assertFalse(is_diff_oversized(diff_text, max_lines=801))


if __name__ == "__main__":
    unittest.main()
