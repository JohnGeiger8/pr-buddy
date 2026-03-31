# Ground truth notes

Repo: facebook/react
PR: 22114
Title: Remove the warning for setState on unmounted components
URL: https://github.com/facebook/react/pull/22114

## Why this PR was selected
Previously suggested; verified this is a real PR.

## What a good review should catch
- Possibility of increased number of memory leaks from change

## What humans actually caught
- Possibility of increased number of memory leaks from change
- What this removes was not actually providing a helpful warning for users

## What should NOT be flagged
- N/A

## What was missed (if anything)
- N/A

## Evaluation
- Caught key issues: yes / partial / no
- Noise level: low / medium / high
- Overall usefulness: 1-5
