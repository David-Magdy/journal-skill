---
name: journal-list
description: Inspect and manage the Obsidian or Markdown journal vault notes and folder hierarchy. Use when listing the vault tree or performing file automation (modify, remove, add, clone, or move notes).
---

# Journal List & Vault Management

This skill inspects the journal vault folder structure, formats notes and categories in a clean visual tree, and provides file automation capabilities.

## Note Formatting & Placeholder Rules

- **No Unnecessary Headers**: Only include section headlines (`Conceptual Core`, `Bug / Edge Case Encountered`, `Key CLI Commands & Environment Tricks`, etc.) if relevant content was encountered or explicitly requested by the user.
- **No Empty Placeholders**: Never include empty placeholder text (such as `*None recorded.*` or blank section headers). If no bugs were found, the bug section must not exist. If no CLI commands or tricks were used, the commands section must not exist.
- **Redaction**: Redact API keys, tokens, and internal references before presenting previews or writing to disk.

---

## `/journal-list` Workflow

Inspects the vault folder hierarchy and enables file automation.

### Flow:
1. **Inspect Vault Structure**:
   Execute the list command to retrieve the hierarchy:
   ```bash
   python3 scripts/journal.py list --vault VAULT
   ```
2. **Display Clean Tree**:
   Display the hierarchy of categories and notes in a clean visual tree format in the chat reply.
3. **Await User Command**:
   In the reply, present the tree and inform the user of available actions:
   - **Modify / Edit**: Update title, category, tags, or content of a note.
   - **Remove / Delete**: Delete a specific note or empty folder category (`python3 scripts/journal.py remove --vault VAULT --path PATH`).
   - **Add**: Create a new note or folder category.
   - **CloneTo / Duplicate**: Copy an existing note (`python3 scripts/journal.py clone --vault VAULT --source SOURCE --target TARGET`).
   - **Move / Rename**: Reorganize notes across folders (`python3 scripts/journal.py move --vault VAULT --source SOURCE --target TARGET`).
   - **Resume**: Return immediately to regular chat or coding work.
   - **WAIT** for the user's response.
4. **Execute & Report**:
   Execute the requested file operation using the script or standard tools, show the updated state or confirmation, or resume chat as instructed.
