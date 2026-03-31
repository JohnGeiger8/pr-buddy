from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig, load_app_config, parse_simple_yaml


class ConfigTests(unittest.TestCase):
    def test_parse_simple_yaml_scalars(self) -> None:
        parsed = parse_simple_yaml(
            """
            provider: anthropic
            model: "claude-test"
            max_diff_lines: 600
            temperature: 0.2
            """
        )

        self.assertEqual(parsed["provider"], "anthropic")
        self.assertEqual(parsed["model"], "claude-test")
        self.assertEqual(parsed["max_diff_lines"], 600)
        self.assertEqual(parsed["temperature"], 0.2)

    def test_load_app_config_uses_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = load_app_config(repo_path=tmp_dir)

        self.assertEqual(config, AppConfig())

    def test_load_app_config_reads_repo_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / ".pr-buddy.yml"
            config_path.write_text(
                "\n".join(
                    [
                        "provider: anthropic",
                        "model: claude-custom",
                        "max_diff_lines: 400",
                        "max_output_tokens: 900",
                        "max_context_files: 2",
                        "max_context_chars: 1200",
                        "max_findings: 2",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_app_config(repo_path=tmp_dir)

        self.assertEqual(config.model, "claude-custom")
        self.assertEqual(config.max_diff_lines, 400)
        self.assertEqual(config.max_output_tokens, 900)
        self.assertEqual(config.max_context_files, 2)
        self.assertEqual(config.max_context_chars, 1200)
        self.assertEqual(config.max_findings, 2)


if __name__ == "__main__":
    unittest.main()
