# profit-agent-demo Project Rules

This document defines the project constraints and workflow for work in `profit-agent-demo`. Read it before editing code, running tests, validating the UI, or writing a Git commit message.

## Project Principles

- Write documentation and user-facing explanations in Korean.
- Never print or commit real company PostgreSQL information, API keys, OAuth credentials, passwords, or connection strings.
- Use synthetic data only. Do not copy real company rows, identifiers, or unique categories into the public demo.
- Keep products and SKUs distinct.
- Do not allow the model to generate or execute SQL, Python, Vega specifications, or arbitrary product ID lists.
- Use allowlisted query builders and bound parameters for SQL.
- Keep PostgreSQL queries read-only with a statement timeout, a maximum date range of 366 days, a maximum of 1,000 rows, and a maximum ranking limit of 100.
- Do not fill periods with no data using zeros or estimates when the period is outside the demo data range.

## Natural-Language Analysis and Visualization

- Do not hardcode individual example sentences. Normalize natural-language requests into canonical dimensions, metrics, periods, grains, and chart types.
- Define Korean and English aliases explicitly in the semantic schema.
- Manage supported dimensions through an allowlist, including brand, product, shop group, seller, and category where supported.
- Supported chart types are `line`, `bar`, and `stacked_bar`; map natural-language aliases to these canonical values.
- Use the same structured tool result, period, filters, and metric for both the table and the chart.
- Do not expose model-generated JSON or text-based chart descriptions directly to the user.
- Stacked bar charts must accumulate amounts by series for each period so that revenue share can be compared.
- Verify that the requested graph is displayed in the actual browser. Passing `pytest` alone is not sufficient to claim that a UI issue is fixed.

## Code Editing Rules

### Indentation-Only Requests

When the user says that code content must not change, make only the following changes:

- Leading spaces or tabs.
- Indentation alignment.
- Do not change code, strings, tokens, comments, imports, line ordering, logic, or blank-line meaning.
- Use four-space indentation for Python when that is the repository convention.
- Remove or reduce one stray space or less; for three or more stray spaces, move to the nearest four-space boundary; for two stray spaces, choose the boundary that best preserves the surrounding block's readability.
- After editing, verify that the diff contains no non-whitespace changes.

Indentation check for Python files:

```bash
python3 - <<'PY'
from pathlib import Path
for path in Path(".").rglob("*.py"):
    if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
        continue
    for number, line in enumerate(path.read_text().splitlines(), 1):
        prefix = line[:len(line) - len(line.lstrip(" "))]
        assert "\t" not in prefix
        assert len(prefix) % 4 == 0, (path, number, len(prefix))
PY
```

For other languages, inspect the repository's formatter or editor configuration before applying an indentation width. Do not impose Python's four-space rule on YAML, Makefiles, or languages where tabs have syntactic meaning.

## Tests and Runtime Verification

- For a new feature or bug fix, write a reproducer or regression test first.
- Do not consider a UI issue fixed based only on unit tests.
- For UI changes, verify the actual import path, Streamlit startup, health endpoint, and, when possible, the browser screen.
- Keep the startup import preflight in `scripts/run_demo_streamlit.sh`.
- Representative verification commands:

```bash
env -u PYTHONPATH uv run pytest tests/ -q
env -u PYTHONPATH uv run python -m compileall -q src
git diff --check
curl -fsS http://127.0.0.1:8510/_stcore/health
```

- Report only results that were actually produced by tools. Never infer or fabricate test results.

## Commit Message Rules

When the user asks for a commit message, inspect both the current changes and the repository history.

1. Run `git status --short` and `git diff --stat`.
2. Read the relevant complete `git diff` sufficiently to understand the actual behavior and files changed. Consider both staged and unstaged changes.
3. Run `git log -10 --format='%h%n%s%n%b%n---'` to inspect the historical prefix, scope, language, capitalization, tense, and body-list style.
4. Use wording consistent with the historical commits. Do not introduce an unfamiliar Conventional Commit style or expressions that the user has not used.
5. Describe the complete current diff, not only the latest edit. Do not claim features, tests, or files absent from the diff.
6. Match the commit body structure used by the repository history:
   - For a simple, focused change, write only a single subject line and no body.
   - For a complex change, add one blank line after the subject, followed by concise detail bullets.
   - Never place the first body bullet directly on the line immediately after the subject.
7. If the user requests a copyable message, return exactly one plain fenced code block containing the commit message. Do not add an introduction, explanation, heading, or other prose outside the code block.
8. Do not add a language identifier after the opening fence.

Commit-message completion criteria:

- The subject matches the recent commits' prefix, scope, language, and tone.
- Every substantive area of the current diff is represented.
- Unrelated historical work and speculation are excluded.
- A copyable response contains exactly one plain fenced code block when requested.

## Completion Checklist

- [ ] Repository rules and relevant files were inspected first.
- [ ] The actual change scope was reviewed in the diff.
- [ ] An indentation-only request produced no non-whitespace source changes.
- [ ] Python indentation uses four-space boundaries and contains no leading tabs.
- [ ] Relevant tests and syntax checks were actually run.
- [ ] A UI change was checked through the actual import, startup, and health paths.
- [ ] A commit-message request was preceded by both `git diff` and `git log` inspection.
- [ ] The commit message matches the repository's historical style.
- [ ] A requested copyable commit message is returned only as one plain fenced code block.
