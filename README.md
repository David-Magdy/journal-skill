# journal-skill

[![CI](https://img.shields.io/github/actions/workflow/status/David-Magdy/journal-skill/ci.yml?branch=main&label=CI)](https://github.com/David-Magdy/journal-skill/actions/workflows/ci.yml)
[![skills.sh](https://www.skills.sh/b/David-Magdy/journal-skill)](https://www.skills.sh/David-Magdy/journal-skill)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)


A portable coding-agent skill that extracts and journals what **you** learned during a coding session (not codebase state or repo summaries) directly into your local Markdown or Obsidian vault.

No cloud dependency. All extraction, deduplication, and note writes run locally through your coding agent.

## Installation & Updating

### Install All Skills (Recommended)
```bash
npx skills add David-Magdy/journal-skill --all
```

Or install individual skills:
```bash
npx skills add David-Magdy/journal-skill --skill journal
npx skills add David-Magdy/journal-skill --skill journal-setup
npx skills add David-Magdy/journal-skill --skill journal-list
```

### Update (for users on older versions)
To update existing installations to the latest version:
```bash
npx skills update
# or update a specific skill
npx skills update journal
npx skills update journal-setup
npx skills update journal-list
```

---

## Available Commands

The skill provides three integrated commands:

### 1. `/journal-setup`
Configures or updates your Obsidian vault path and folder taxonomy.

- **Interactive Flow**: Call `/journal-setup`. The agent checks for:
  1. The absolute path to your Obsidian vault.
  2. Folder structure preference: whether you want to use the default categories (`AI & Deep Learning`, `Software Engineering & Systems`, `Dev & Environment`) or define custom categories.
  - If any required detail is missing, the agent prompts you in a reply.
  - Once all specifications are provided, the agent configures the vault immediately.
- **Direct / Non-Interactive**:
  ```bash
  /journal-setup --vault ~/notes/AcademicVault --categories "AI & Deep Learning,Software Engineering & Systems,Dev & Environment" --create-dirs -y
  ```

### 2. `/journal`
Distills what you learned during the conversation into your vault with an interactive confirmation loop.

- **Clean Note Formatting**:
  - Unnecessary headers and empty placeholders (such as `*None recorded.*`) are **strictly eliminated**.
  - If no bugs or edge cases occurred in the chat, the bug section will not exist.
  - If no special CLI commands or environment tricks were used, the command section will not exist.
  - Only sections with actual content are included in the generated note.
- **Interactive Preview Loop**:
  - The agent synthesizes session learnings, redacts sensitive secrets, and tests formatting via `--dry-run`.
  - In a chat reply, the agent displays a brief preview of what will be written (action, path, title, tags, and summary).
  - The agent **waits for your review**. You can ask for modifications (change title, adjust tags, modify summary, add/remove content) or command to proceed.
  - The preview cycle continues until you are satisfied.
  - Upon your confirmation ("proceed", "save", "looks good"), the agent writes the note to disk and confirms the exact file path.

### 3. `/journal-list`
Inspects your vault structure and supports file automation workflows.

- **Tree Inspection**:
  - Displays a clean visual ASCII tree of categories and notes in your vault (filtering out hidden folders like `.git` and internal metadata).
- **File Automation & Modification**:
  - After displaying the tree, the agent awaits your command. You can ask the agent to:
    - **Modify**: Update note contents, frontmatter, categories, or tags.
    - **Remove**: Delete a specific note or empty folder category.
    - **Add**: Create a new note or folder category.
    - **CloneTo**: Duplicate an existing note under a new name or category.
    - **Move / Rename**: Reorganize notes across folders.
    - **Resume**: Return immediately to your regular coding chat.

---

## Development Checks

```bash
python3 -m unittest discover -s scripts -p "test_*.py"
python3 -m py_compile scripts/journal.py
npx -y skills add . --list
```

---

## Configuration

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
- `categories`: Array of string category names. Can be customized to your specific domain (e.g. `["Research", "Projects", "Notes"]`).
- `duplicate_match_threshold`: Score threshold for linking related sessions to an existing note instead of creating a separate note.
- `context_window`: Session history limits in messages and approximate tokens.
- `redaction.include_internal_refs`: Boolean flag (default `false`). When `false`, internal project identifiers, private repo names, and local machine paths are scrubbed.

---

## Privacy & Redaction

- **Mandatory Redaction Step**: A local script sanitizes API keys, authorization tokens, passwords, and private IP addresses before notes are previewed or formatted.
- **Internal Reference Scrubbing**: Internal hostnames, IPs, and local references are omitted by default; passing `--include-internal-refs` or setting `redaction.include_internal_refs: true` is an explicit opt-in.
- **Local Execution**: Notes are written directly to your local filesystem. No data is sent to external journaling APIs or third-party analytics services.
