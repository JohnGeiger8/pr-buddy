# Project Brief

PR Buddy is a lightweight Python-based pull request review agent that analyzes a git diff, asks Anthropic to review it against repository-specific rules, and outputs structured review feedback.

The project is designed for low-cost, practical PR feedback for personal use first, with a path toward broader reuse. It supports both local CLI usage and GitHub Actions automation that can post review summaries directly back to pull requests.