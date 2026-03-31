# Ground truth notes

Repo: microsoft/TypeScript
PR: 51669
Title: `--moduleResolution bundler` (formerly known as `hybrid`)
URL: https://github.com/microsoft/TypeScript/pull/51669

## Why this PR was selected
Previously suggested; verified this is a real PR.

## What a good review should catch
- Several files were updated with just commented out code
- Tons of test files were changed or added

## What humans actually caught
- PR Description indicated 'node' export condition was applied by default, but code didn't actually do that due to recent PR.

## What should NOT be flagged
- N/A

## What was missed (if anything)
- N/A

## Evaluation
- Caught key issues: yes / partial / no
- Noise level: low / medium / high
- Overall usefulness: 1-5
