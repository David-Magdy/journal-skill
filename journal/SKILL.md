---
name: journal
description: Distill what the user learned during a coding-agent session into a local Markdown or Obsidian vault. Use to document conceptual insights, bugs solved, or CLI tricks from the chat; do not summarize repository state unless it is part of the user's learning.
---

# Agent Learning Journal

This skill turns session learnings into durable notes in an Obsidian or Markdown vault. The user's learning is the subject; codebase summaries are not.

## Note Formatting & Placeholder Rules

- **No Unnecessary Headers**: Only include section headlines (`Conceptual Core`, `Bug / Edge Case Encountered`, `Key CLI Commands & Environment Tricks`, etc.) if relevant content was encountered or explicitly requested by the user.
- **No Empty Placeholders**: Never include empty placeholder text (such as `*None recorded.*` or blank section headers). If no bugs were found, the bug section must not exist. If no CLI commands or tricks were used, the commands section must not exist.
- **Redaction**: Redact API keys, tokens, and internal references before presenting previews or writing to disk.

---

## `/journal` Workflow

Distills session learnings into the vault with an iterative preview-and-refine cycle.

### Flow:
1. **Analyze Session**:
   Review the recent conversation window according to configured limits:
   ```bash
   python3 scripts/journal.py window --config VAULT/Meta/journal.config.json
   ```
2. **Synthesize & Redact**:
   Extract title, category, tags, and conceptual core. Extract bug details or commands only if they actually occurred in the chat.
3. **Duplicate Check**:
   Search for related existing notes before writing:
   ```bash
   python3 scripts/journal.py find --vault VAULT --title TITLE [--category CATEGORY] [--tags TAGS]
   ```
4. **Dry-Run & Preview**:
   Validate note formatting via dry-run:
   ```bash
   python3 scripts/journal.py capture --vault VAULT \
     --title TITLE --category CATEGORY --tags TAGS \
     --summary SUMMARY [--bug BUG] [--commands COMMANDS] --dry-run
   ```
5. **Interactive Confirmation Reply**:
   In a chat reply, display a concise summary of what will be written:
   - **Action**: New Note or Appending to existing note
   - **Destination**: Vault path and category
   - **Title & Tags**
   - **Content Summary**: Conceptual core, and only include bug/commands sections if non-empty.
   - **Prompt User**: Ask if they want any modifications (title, category, tags, content) or are ready to proceed.
   - **WAIT** for the user's response.
6. **Iterate or Write**:
   - If the user requests changes, update the draft, display a revised brief preview, and wait again.
   - When the user confirms or commands to proceed, write the note without `--dry-run`:
     ```bash
     python3 scripts/journal.py capture --vault VAULT \
       --title TITLE --category CATEGORY --tags TAGS \
       --summary SUMMARY [--bug BUG] [--commands COMMANDS]
     ```
   - Always report the written or updated file path as the final response.
