---
name: journal-setup
description: Configure an Obsidian or local Markdown vault location and folder taxonomy for agent session journaling. Use when setting up or reconfiguring the journal vault path or category folders.
---

# Journal Setup

This skill configures the target Obsidian or Markdown vault path, note density, categorization strategy, and category folder taxonomy for the agent learning journal.

## Note Formatting & Placeholder Rules

- **No Unnecessary Headers**: Only include section headlines (`Conceptual Core`, `Bug / Edge Case Encountered`, `Key CLI Commands & Environment Tricks`, etc.) if relevant content was encountered or explicitly requested by the user.
- **No Empty Placeholders**: Never include empty placeholder text (such as `*None recorded.*` or blank section headers). If no bugs were found, the bug section must not exist. If no CLI commands or tricks were used, the commands section must not exist.
- **Redaction**: Redact API keys, tokens, and internal references before presenting previews or writing to disk.

---

## `/journal-setup` Workflow

Configures or updates the Obsidian vault path and folder taxonomy.

### Flow:
1. **Check Specifications**:
   Determine if the user provided both:
   - **Vault Absolute Path** (e.g. `/home/user/vault` or `~/notes/vault`).
   - **Folder Structure Preference**: whether they want to use the default predefined folders (`AI & Deep Learning`, `Software Engineering & Systems`, `Dev & Environment`) or define custom categories in the chat reply.
2. **Missing Information**:
   If either the vault path or structure preference is missing, prompt the user in a chat reply for the missing details and wait for their response.
3. **Execute Configuration**:
   Once both specifications are provided (either directly in the initial invocation or in the follow-up reply), proceed immediately:
   ```bash
   python3 scripts/journal.py setup --vault PATH [--categories "Cat1,Cat2,..."] [--create-dirs] -y
   ```
4. **Report Results**:
   Report the resolved vault path, configured folder taxonomy, and configuration file location (`<vault>/Meta/journal.config.json`).
