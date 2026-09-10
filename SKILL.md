---
name: journal
description: Capture what the user learned in a coding-agent session into a local Markdown or Obsidian vault. Use for /journal-setup and /journal; do not summarize repository state unless it is part of the user's learning.
---

# Agent Learning Journal

This skill turns session learnings into durable notes. The user's learning is
the subject; codebase summaries are not.

## `/journal-setup`

If flags are absent, ask for the vault path, categorization (`topic-first`,
`project-first`, or `manual`), and density (`conceptual` or
`conceptual+snippets`). Then run:

```bash
python3 scripts/journal.py setup --vault PATH --categorization MODE --density DENSITY -y
```

All flags have defaults, so `-y` alone is valid. Report the resolved vault and
config paths from the command output.

## `/journal`

1. Read `Meta/journal.config.json` and `Meta/agent.md`.
2. For no-argument calls, use only the configured recent message/token window.
   Pass the session messages as JSON to:

   ```bash
   python3 scripts/journal.py window --config VAULT/Meta/journal.config.json
   ```

   Tell the user when the returned `truncated` value is true.
3. Extract one candidate JSON object with `title`, `category`, `tags`,
   `summary`, optional `bug_section`, `commands`, and optional `session_ref`.
4. Do not display raw extracted secrets. Pass the candidate fields to the
   dependency-free capture command; it redacts before formatting or writing.
   Use `--include-internal-refs` only when the user explicitly requests it.
5. Search before writing, then preview or write through the script:

   ```bash
   python3 scripts/journal.py capture --vault VAULT \
     --title TITLE --category CATEGORY --tags TAGS \
     --summary SUMMARY [--bug BUG] [--commands COMMANDS] [--dry-run]
   ```

Use `find` first when an explicit receipt is useful. The script creates one
note for a new concept and appends a dated related session for a match. Never
overwrite existing note content. Always report the path returned by the script.

When the context window excluded older messages, pass
`--window-truncated --window-n N`; the script writes the required callout.

Use `--category` and `--title` to override extracted values. Conceptual notes
must not contain raw code blocks; `conceptual+snippets` permits scrubbed
snippets. The script is local-only and dependency-free.
