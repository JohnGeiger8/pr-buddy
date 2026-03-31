from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.context_loader import load_relevant_context


class ContextLoaderTests(unittest.TestCase):
    def test_python_changes_load_python_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "README.md").write_text("Project overview", encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (repo / "package.json").write_text('{"name":"ignore-me"}', encoding="utf-8")

            context = load_relevant_context(
                repo_path=tmp_dir,
                changed_files=["app/main.py"],
                max_files=4,
                max_chars=500,
            )

        self.assertEqual([path for path, _ in context], ["README.md", "pyproject.toml"])

    def test_node_changes_load_node_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "README.md").write_text("Node app", encoding="utf-8")
            (repo / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
            (repo / "tsconfig.json").write_text('{"compilerOptions":{"strict":true}}', encoding="utf-8")
            (repo / "pyproject.toml").write_text("[project]\nname='ignore'\n", encoding="utf-8")

            context = load_relevant_context(
                repo_path=tmp_dir,
                changed_files=["src/index.ts"],
                max_files=4,
                max_chars=500,
            )

        self.assertEqual(
            [path for path, _ in context],
            ["README.md", "package.json", "tsconfig.json"],
        )

    def test_context_respects_file_and_char_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "README.md").write_text("A" * 200, encoding="utf-8")
            (repo / "package.json").write_text('{"name":"demo"}', encoding="utf-8")

            context = load_relevant_context(
                repo_path=tmp_dir,
                changed_files=["src/index.ts"],
                max_files=1,
                max_chars=50,
            )

        self.assertEqual(len(context), 1)
        self.assertEqual(context[0][0], "README.md")
        self.assertLessEqual(len(context[0][1]), 50)


if __name__ == "__main__":
    unittest.main()
