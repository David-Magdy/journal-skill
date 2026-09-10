# journal-skill

A portable coding-agent skill that extracts and journals what **you** learned during a coding session (not codebase state or repo summaries) directly into your local Markdown or Obsidian vault.

No cloud dependency. All extraction, deduplication, and note writes run locally through your coding agent.

## Development checks

```bash
python -m unittest discover -s scripts -p "test_*.py"
python -m py_compile scripts/journal.py
npx -y skills add . --list
```

## Installation

Install with:

```bash
npx skills add David-Magdy/journal-skill
```

## Setup

Run the setup command to configure your vault location and note preferences.

### Interactive

```text
/journal-setup
```

Prompts for vault location, taxonomy layout, and note density.

### Non-Interactive

```bash
/journal-setup --vault ~/notes/AcademicVault --categorization topic-first --density conceptual -y
```

## Usage

- `/journal` — Distill learnings from the current session into the configured vault.
- `/journal <prompt>` — Distill with specific steering (e.g. `/journal focus on the CUDA memory allocator`).
- `/journal --category ... --title ... --dry-run` — Explicitly target a category and title, previewing the note output without writing to disk.

## Configuration Overrides

Configuration is stored at `<vault>/Meta/journal.config.json`:

```json
{
  "vault_path": "~/notes/AcademicVault",
  "categorization": "topic-first",
  "density": "conceptual",
  "categories": [
    "AI & Deep Learning",
    "Software Engineering & Systems",
    "Dev & Environment"
  ],
  "duplicate_match_threshold": 0.6,
  "context_window": {"max_messages": 40, "max_tokens": 8000},
  "redaction": {
    "include_internal_refs": false
  }
}
```

### Fields

- `vault_path`: Target directory path for the Markdown/Obsidian vault.
- `categorization`: Layout strategy (`topic-first`, `project-first`, or `manual`).
- `density`: Note detail level (`conceptual` or `conceptual+snippets`).
- `categories`: Array of string category names. Non-coding users can replace the default tree with their own domain topics (e.g. `["biology", "microscopy", "lab-ops"]`).
- `duplicate_match_threshold`: Score threshold for linking related sessions to an existing note instead of creating a separate note.
- `context_window`: Session history limits in messages and approximate tokens.
- `redaction.include_internal_refs`: Boolean flag (default `false`). When `false`, internal project identifiers, private repo names, and local machine paths are scrubbed.

## Privacy & Redaction

- **Mandatory redaction step**: A local script sanitizes API keys, authorization tokens, passwords, and private IP addresses before notes are formatted.
- **Internal reference scrubbing**: Internal hostnames, IPs, and local references are omitted by default; passing `--include-internal-refs` or setting `redaction.include_internal_refs: true` is an explicit opt-in.
- **Local execution**: Notes are written directly to your local filesystem. No data is sent to external journaling APIs or third-party analytics services.
