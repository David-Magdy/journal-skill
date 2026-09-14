---
name: journal
description: Capture what the user learned in a coding-agent session into a local Markdown or Obsidian vault. Use for /journal-setup, /journal, and /journal-list; do not summarize repository state unless it is part of the user's learning.
---

# Agent Learning Journal

This skill turns session learnings into durable notes in an Obsidian or Markdown vault. The user's learning is the subject; codebase summaries are not.

## Note Formatting & Placeholder Rules

- **No Unnecessary Headers**: Only include section headlines (`Conceptual Core`, `Bug / Edge Case Encountered`, `Key CLI Commands & Environment Tricks`, etc.) if relevant content was encountered or explicitly requested by the user.
- **No Empty Placeholders**: Never include empty placeholder text (such as `*None recorded.*` or blank section headers). If no bugs were found, the bug section must not exist. If no CLI commands or tricks were used, the commands section must not exist.
- **Redaction**: Redact API keys, tokens, and internal references before presenting previews or writing to disk.

---

## `/journal-setup`

Configures the Obsidian vault path and folder structure.

### Flow:
1. Check whether the user provided both:
   - **Vault Absolute Path** (e.g. `/home/user/vault` or `~/notes/vault`).
   - **Folder Structure Preference**: whether they want to use the default predefined folders (`AI & Deep Learning`, `Software Engineering & Systems`, `Dev & Environment`) or provide their own custom folder structure / categories.
2. **Missing Information**: If either specification is missing, prompt the user in a reply for the missing details and wait for their response.
3. **All Specified**: If both are specified (either in the initial command or in the reply), proceed immediately:
   ```bash
   python3 scripts/journal.py setup --vault PATH [--categories "Cat1,Cat2,..."] [--create-dirs] -y
   ```
4. Report the resolved vault path, configured folder structure, and configuration location.

---

## `/journal`

Distills session learnings into the vault with an iterative preview-and-refine cycle.

### Flow:
1. **Analyze Session**: Review the recent conversation window according to configured limits:
   ```bash
   python3 scripts/journal.py window --config VAULT/Meta/journal.config.json
   ```
2. **Synthesize & Redact**: Extract title, category, tags, and conceptual core. Extract bug details or commands only if they actually occurred.
3. **Duplicate Check**:
   ```bash
   python3 scripts/journal.py find --vault VAULT --title TITLE [--category CATEGORY] [--tags TAGS]
   ```
4. **Dry-Run & Preview**:
   ```bash
   python3 scripts/journal.py capture --vault VAULT \
     --title TITLE --category CATEGORY --tags TAGS \
     --summary SUMMARY [--bug BUG] [--commands COMMANDS] --dry-run
   ```
5. **Interactive Confirmation Reply**:
   In a chat reply, display a concise summary of what would be written:
   - **Action**: New Note or Appending to existing note
   - **Destination**: Vault path and category
   - **Title & Tags**
   - **Content Summary**: Conceptual core, and only include bug/commands sections if non-empty.
   - Prompt the user: Ask if they want any modifications (title, category, tags, content) or are ready to proceed.
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

---

## `/journal-list`

Inspects the vault folder structure and enables file automation.

### Flow:
1. **Inspect Vault Structure**:
   ```bash
   python3 scripts/journal.py list --vault VAULT
   ```
2. **Display Clean Tree**:
   Display the hierarchy of folders and notes in a clean ASCII tree format in the chat reply.
3. **Await User Command**:
   In the reply, prompt the user for any file management actions they may want to perform:
   - **Modify / Edit**: Update title, category, tags, or content of a note.
   - **Remove / Delete**: Delete a specific note or folder (`python3 scripts/journal.py remove --vault VAULT --path PATH`).
   - **Add**: Create a new note or folder category.
   - **CloneTo / Duplicate**: Copy an existing note (`python3 scripts/journal.py clone --vault VAULT --source SOURCE --target TARGET`).
   - **Move / Rename**: Relocate or rename a note or folder (`python3 scripts/journal.py move --vault VAULT --source SOURCE --target TARGET`).
   - **Resume**: Resume normal chat / coding work.
   - **WAIT** for user response.
4. **Execute & Report**:
   Execute the requested file operation using the script or standard tools, show the updated state, or resume chat as instructed.
