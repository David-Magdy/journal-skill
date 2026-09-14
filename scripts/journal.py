import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys


DEFAULT_VAULT = "~/notes/AcademicVault"
DEFAULT_CATEGORIES = [
    "AI & Deep Learning",
    "Software Engineering & Systems",
    "Dev & Environment",
]
REDACTED = "[redacted: possible secret]"


def _config_path(vault):
    return Path(vault).expanduser().resolve() / "Meta" / "journal.config.json"


def _read_config(vault, required=False):
    path = _config_path(vault)
    if not path.exists():
        if required:
            raise FileNotFoundError(f"journal config not found: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read journal config: {path}: {exc}") from exc


def setup_vault(
    vault=DEFAULT_VAULT,
    categorization="topic-first",
    density="conceptual",
    categories=None,
    create_dirs=False,
):
    if categorization not in {"topic-first", "project-first", "manual"}:
        raise ValueError("categorization must be topic-first, project-first, or manual")
    if density not in {"conceptual", "conceptual+snippets"}:
        raise ValueError("density must be conceptual or conceptual+snippets")
    root = Path(vault).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "Meta").mkdir(exist_ok=True)

    if categories is None:
        category_list = list(DEFAULT_CATEGORIES)
    elif isinstance(categories, (list, tuple)):
        category_list = [str(cat).strip() for cat in categories if str(cat).strip()]
    elif isinstance(categories, str):
        category_list = [cat.strip() for cat in categories.split(",") if cat.strip()]
    else:
        category_list = list(DEFAULT_CATEGORIES)

    if not category_list:
        category_list = list(DEFAULT_CATEGORIES)

    if create_dirs:
        for cat in category_list:
            (root / cat).mkdir(parents=True, exist_ok=True)

    config = {
        "vault_path": str(root),
        "categorization": categorization,
        "density": density,
        "categories": category_list,
        "duplicate_match_threshold": 0.6,
        "context_window": {"max_messages": 40, "max_tokens": 8000},
        "redaction": {"include_internal_refs": False},
    }
    _config_path(root).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    cats_md = "\n".join(f"- {c}" for c in category_list)
    (root / "Meta" / "agent.md").write_text(
        "# Journal Skill Rules\n\n"
        f"- Vault root: {root}\n"
        f"- Categorization mode: {categorization}\n"
        f"- Density: {density}\n"
        f"- Configured Categories:\n{cats_md}\n\n"
        "## Commands & Workflows:\n"
        "1. /journal-setup: Configure vault path and folder structure.\n"
        "2. /journal: Synthesize learnings, display brief preview, wait for user confirmation/modifications before writing.\n"
        "3. /journal-list: Display vault folder tree, await file automation commands (modify, remove, add, cloneTo, move) or resume work.\n\n"
        "## Note Formatting Rules:\n"
        "- Only document user learnings, not repository state.\n"
        "- Never include empty headers or placeholder text (*None recorded.*).\n"
        "- Only include sections (Conceptual Core, Bug, Key Commands) when relevant content exists.\n"
        "- Run duplicate search before writing anything.\n"
        "- Redact secrets before writing or displaying content.\n"
        "- Respect context window limits.\n"
        "- Never overwrite existing note content — append dated entries only.\n"
        "- Report the file path written/updated to the user.\n",
        encoding="utf-8",
    )
    return config


def redact(value, include_internal_refs=False):
    value = "" if value is None else str(value)
    for pattern, flags in [
        (r"AKIA[0-9A-Z]{16}", 0),
        (r"bearer\s+[A-Za-z0-9._\-=]+", re.IGNORECASE),
        (r"(?:ghp|gho|ghu|ghs|ghr|glpat|xox[baprs])-[A-Za-z0-9_-]+", 0),
        (r"sk-[A-Za-z0-9]{16,}", 0),
        (r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", 0),
        (r"^[A-Z][A-Z0-9_]{2,}=[^\s].*$", re.MULTILINE),
    ]:
        value = re.sub(pattern, REDACTED, value, flags=flags)
    if not include_internal_refs:
        for pattern in [
            r"\b(?:10|127)(?:\.\d{1,3}){3}\b|\b192\.168(?:\.\d{1,3}){2}\b|\b172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}\b",
            r"\b[a-z0-9-]+\.(?:local|internal|lan|corp)\b",
            r"\b(?:localhost|internal|intranet|corp)\b",
        ]:
            value = re.sub(pattern, REDACTED, value, flags=re.IGNORECASE)
    return value


def _tokens(value):
    return set(re.findall(r"[^\W_]+", value.lower(), re.UNICODE))


def _jaccard(left, right):
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _parse_tags(value):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value:
        return set()
    return {
        item.strip().strip("'\"").lower()
        for item in value.split(",")
        if item.strip().strip("'\"")
    }


def _note_data(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    metadata = {}
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                for line in lines[1:index]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        value = value.strip()
                        if value.startswith(('"', "'")) and value.endswith(value[0]):
                            value = value[1:-1]
                        metadata[key.strip()] = value
                break
    title = next((match.group(1).strip() for line in lines if (match := re.match(r"^#\s+(.+?)\s*$", line))), path.stem)
    return metadata.get("topic", ""), _parse_tags(metadata.get("tags", "")), title


def _note_paths(vault):
    root = Path(vault).expanduser().resolve()
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file() and path.relative_to(root).parts[:1] != ("Meta",)
    )


def find_existing_note(vault, title, category=None, tags=None):
    config = _read_config(vault)
    try:
        threshold = float(config.get("duplicate_match_threshold", 0.6))
    except (TypeError, ValueError):
        threshold = 0.6
    wanted_tags = {str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()}
    title_tokens = _tokens(title)
    notes = []
    titles = []
    for path in _note_paths(vault):
        topic, note_tags, note_title = _note_data(path)
        titles.append(note_title)
        if category is not None or wanted_tags:
            by_category = category is not None and topic == category
            by_tags = bool(wanted_tags and note_tags & wanted_tags)
            if not (by_category or by_tags):
                continue
        title_score = _jaccard(title_tokens, _tokens(note_title))
        tag_score = _jaccard(wanted_tags, note_tags) if wanted_tags and note_tags else 0.0
        notes.append((0.7 * title_score + 0.3 * tag_score, path))
    notes.sort(key=lambda item: (-item[0], str(item[1])))
    score = notes[0][0] if notes else 0.0
    match = str(notes[0][1].resolve()) if notes and score >= threshold else None
    return {"match": match, "score": score, "titles": titles}


def _safe_name(value, fallback="Untitled"):
    value = "".join(char if char.isalnum() or char in " -_" else " " for char in value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or fallback


def _safe_category(value):
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("category must be a non-empty relative path")
    return path


def _linked_summary(summary, titles, title):
    result = summary
    current = title.casefold()
    for other in sorted(set(titles), key=lambda value: (-len(value), value.casefold())):
        if not other or other.casefold() == current:
            continue
        result = re.sub(
            rf"(?<!\w)({re.escape(other)})(?!\w)",
            lambda match: f"[[{match.group(1)}]]",
            result,
        )
    return result


def _strip_fences(value):
    return re.sub(r"```[\s\S]*?```", "", value)


def _compact(value):
    return re.sub(r"\s+", " ", value.strip())


def window_messages(messages, max_messages=40, max_tokens=8000):
    recent = messages[-max_messages:]
    kept = []
    tokens = 0
    for message in reversed(recent):
        count = len(str(message.get("content", "")).split())
        if kept and tokens + count > max_tokens:
            break
        kept.append(message)
        tokens += count
    kept.reverse()
    return kept, len(kept) < len(messages)


def capture_note(
    vault,
    title,
    category,
    tags=None,
    session_ref="",
    summary="",
    bug="",
    commands="",
    dry_run=False,
    include_internal_refs=False,
    window_truncated=False,
    window_n=None,
):
    config = _read_config(vault, required=True)
    allow_internal = include_internal_refs or bool(config.get("redaction", {}).get("include_internal_refs", False))
    raw_tags = ",".join(tags) if isinstance(tags, (list, tuple, set)) else (tags or "")
    values = [title, category, raw_tags, session_ref, summary, bug, commands]
    clean_title, clean_category, clean_tags, clean_session, clean_summary, clean_bug, clean_commands = [
        redact(value, allow_internal) for value in values
    ]
    stripped = any(clean != ("" if original is None else str(original)) for clean, original in zip(
        [clean_title, clean_category, clean_tags, clean_session, clean_summary, clean_bug, clean_commands], values
    ))
    extra_tags = [tag.strip() for tag in clean_tags.split(",") if tag.strip()]
    category_path = _safe_category(clean_category)
    if config.get("density", "conceptual") == "conceptual":
        clean_summary, clean_bug, clean_commands = [_strip_fences(value) for value in (clean_summary, clean_bug, clean_commands)]
    result = find_existing_note(vault, clean_title, clean_category, extra_tags)
    root = Path(vault).expanduser().resolve()
    note_name = _safe_name(clean_title) + ".md"
    if config.get("categorization") == "project-first":
        project = _safe_name(clean_session, "Inbox")
        destination = root / project / category_path / note_name
    else:
        destination = root / category_path / note_name
    today = dt.date.today().isoformat()
    redaction_line = f"> {REDACTED}\n\n" if stripped else ""
    if result["match"]:
        path = Path(result["match"])
        items = []
        if clean_summary.strip():
            items.append(f"- {_compact(clean_summary)}")
        if clean_bug.strip():
            items.append(f"- Bug: {_compact(clean_bug)}")
        if clean_commands.strip():
            items.append(f"- Commands: {_compact(clean_commands)}")
        content_lines = "\n".join(items)
        if content_lines:
            section = f"## Related Session ({today})\n{content_lines}\n"
        else:
            section = f"## Related Session ({today})\n"
        if stripped:
            section += f"{redaction_line}"
        existing = path.read_text(encoding="utf-8", errors="replace")
        would_write = existing + ("" if not existing or existing.endswith("\n") else "\n") + "\n" + section
    else:
        linked = _linked_summary(clean_summary, result["titles"], clean_title)
        callout = ""
        if window_truncated:
            count = window_n if window_n is not None else config.get("context_window", {}).get("max_messages", 40)
            callout = f"> Summarized from the last {count} messages; earlier session content not included.\n\n"
        tags_text = ", ".join(["concept", "learning", *extra_tags])

        sections = []
        if linked.strip():
            sections.append(f"## Conceptual Core\n{linked.strip()}")
        if clean_bug.strip():
            sections.append(f"## Bug / Edge Case Encountered\n{clean_bug.strip()}")
        if clean_commands.strip():
            sections.append(f"## Key CLI Commands & Environment Tricks\n{clean_commands.strip()}")

        body = "\n\n".join(sections)
        if body:
            body = body + "\n"

        would_write = (
            "---\n"
            f"date: {today}\n"
            f"topic: {clean_category}\n"
            f"tags: [{tags_text}]\n"
            f"session_ref: {clean_session}\n"
            "---\n\n"
            f"# {clean_title}\n\n"
            f"{callout}"
            f"{redaction_line}"
            f"{body}"
        )
        would_write = would_write.rstrip() + "\n"
        path = destination
    if dry_run:
        return would_write
    if result["match"]:
        with path.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + section)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(would_write, encoding="utf-8")
    return str(path.resolve())


def _resolve_vault_path(vault, target_path):
    root = Path(vault).expanduser().resolve()
    target = Path(target_path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"path '{target_path}' is outside vault root '{root}'")
    return target


def generate_tree(vault, include_meta=False):
    root = Path(vault).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"vault path not found: {root}")

    ignore_dirs = {".git", ".obsidian", ".trash", ".idea", ".vscode", "__pycache__"}
    if not include_meta:
        ignore_dirs.add("Meta")

    def _build_tree(directory, prefix=""):
        lines = []
        entries = []
        try:
            for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if item.name in ignore_dirs or item.name.startswith("."):
                    continue
                if item.is_dir() or (item.is_file() and item.suffix == ".md"):
                    entries.append(item)
        except OSError:
            return lines

        for i, item in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                extension = "    " if is_last else "│   "
                lines.extend(_build_tree(item, prefix + extension))
            else:
                lines.append(f"{prefix}{connector}{item.name}")
        return lines

    tree_lines = [f"{root.name}/"] + _build_tree(root)
    return "\n".join(tree_lines)


def tree_to_dict(vault, include_meta=False):
    root = Path(vault).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"vault path not found: {root}")

    ignore_dirs = {".git", ".obsidian", ".trash", ".idea", ".vscode", "__pycache__"}
    if not include_meta:
        ignore_dirs.add("Meta")

    def _dir_to_dict(path):
        children = []
        for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.name in ignore_dirs or item.name.startswith("."):
                continue
            if item.is_dir():
                children.append({
                    "name": item.name,
                    "type": "directory",
                    "children": _dir_to_dict(item),
                })
            elif item.is_file() and item.suffix == ".md":
                children.append({
                    "name": item.name,
                    "type": "file",
                    "path": str(item.relative_to(root)),
                })
        return children

    return {
        "vault": str(root),
        "name": root.name,
        "tree": _dir_to_dict(root),
    }


def clone_note(vault, source, target):
    root = Path(vault).expanduser().resolve()
    src_path = _resolve_vault_path(vault, source)
    if not src_path.is_file():
        if (src_path.parent / (src_path.name + ".md")).is_file():
            src_path = src_path.parent / (src_path.name + ".md")
        else:
            raise FileNotFoundError(f"source note not found: {source}")

    tgt_path = _resolve_vault_path(vault, target)
    if not tgt_path.suffix:
        tgt_path = tgt_path.with_suffix(".md")

    if tgt_path.exists():
        raise FileExistsError(f"target note already exists: {tgt_path}")

    tgt_path.parent.mkdir(parents=True, exist_ok=True)
    content = src_path.read_text(encoding="utf-8")
    target_title = tgt_path.stem
    lines = content.splitlines()
    updated_lines = []
    for line in lines:
        if line.startswith("# ") and line[2:].strip() == src_path.stem:
            updated_lines.append(f"# {target_title}")
        else:
            updated_lines.append(line)

    final_content = "\n".join(updated_lines) + ("\n" if content.endswith("\n") else "")
    tgt_path.write_text(final_content, encoding="utf-8")
    return str(tgt_path.resolve())


def remove_item(vault, target, force=False):
    root = Path(vault).expanduser().resolve()
    tgt_path = _resolve_vault_path(vault, target)
    if not tgt_path.exists():
        if (tgt_path.parent / (tgt_path.name + ".md")).exists():
            tgt_path = tgt_path.parent / (tgt_path.name + ".md")
        else:
            raise FileNotFoundError(f"target path not found: {target}")

    if tgt_path == root:
        raise ValueError("cannot remove vault root")

    if tgt_path.is_file():
        tgt_path.unlink()
    elif tgt_path.is_dir():
        if force:
            import shutil
            shutil.rmtree(tgt_path)
        else:
            tgt_path.rmdir()
    return str(tgt_path.resolve())


def move_item(vault, source, target):
    root = Path(vault).expanduser().resolve()
    src_path = _resolve_vault_path(vault, source)
    if not src_path.exists():
        if (src_path.parent / (src_path.name + ".md")).exists():
            src_path = src_path.parent / (src_path.name + ".md")
        else:
            raise FileNotFoundError(f"source path not found: {source}")

    if src_path == root:
        raise ValueError("cannot move vault root")

    tgt_path = _resolve_vault_path(vault, target)
    if tgt_path.is_dir():
        tgt_path = tgt_path / src_path.name
    elif not tgt_path.suffix and src_path.is_file():
        tgt_path = tgt_path.with_suffix(".md")

    if tgt_path.exists():
        raise FileExistsError(f"target path already exists: {tgt_path}")

    tgt_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.rename(tgt_path)
    return str(tgt_path.resolve())


def _prompt(label, default, choices=None):
    value = input(f"{label} [{default}]: ").strip() or default
    if choices and value not in choices:
        raise ValueError(f"{label} must be one of: {', '.join(choices)}")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup")
    setup.add_argument("--vault", default=DEFAULT_VAULT)
    setup.add_argument("--categorization", choices=["topic-first", "project-first", "manual"], default="topic-first")
    setup.add_argument("--density", choices=["conceptual", "conceptual+snippets"], default="conceptual")
    setup.add_argument("--categories", help="Comma-separated list of category folders or custom folder structure")
    setup.add_argument("--create-dirs", action="store_true", help="Pre-create category directories")
    setup.add_argument("-y", action="store_true")

    find = subparsers.add_parser("find")
    find.add_argument("--vault", required=True)
    find.add_argument("--title", required=True)
    find.add_argument("--category")
    find.add_argument("--tags")

    capture = subparsers.add_parser("capture")
    capture.add_argument("--vault", required=True)
    capture.add_argument("--title", required=True)
    capture.add_argument("--category", required=True)
    capture.add_argument("--tags", default="")
    capture.add_argument("--session-ref", default="")
    capture.add_argument("--summary", required=True)
    capture.add_argument("--bug", default="")
    capture.add_argument("--commands", default="")
    capture.add_argument("--dry-run", action="store_true")
    capture.add_argument("--include-internal-refs", action="store_true")
    capture.add_argument("--window-truncated", action="store_true")
    capture.add_argument("--window-n", type=int)

    window = subparsers.add_parser("window")
    window.add_argument("--config")
    window.add_argument("--max-messages", type=int)
    window.add_argument("--max-tokens", type=int)

    list_cmd = subparsers.add_parser("list")
    list_cmd.add_argument("--vault", default=DEFAULT_VAULT)
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.add_argument("--include-meta", action="store_true")

    clone_cmd = subparsers.add_parser("clone")
    clone_cmd.add_argument("--vault", required=True)
    clone_cmd.add_argument("--source", required=True)
    clone_cmd.add_argument("--target", required=True)

    remove_cmd = subparsers.add_parser("remove")
    remove_cmd.add_argument("--vault", required=True)
    remove_cmd.add_argument("--path", required=True)
    remove_cmd.add_argument("--force", action="store_true")

    move_cmd = subparsers.add_parser("move")
    move_cmd.add_argument("--vault", required=True)
    move_cmd.add_argument("--source", required=True)
    move_cmd.add_argument("--target", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            vault, categorization, density = args.vault, args.categorization, args.density
            categories = args.categories
            create_dirs = args.create_dirs
            if not args.y:
                if not sys.stdin.isatty():
                    raise ValueError("setup requires -y when stdin is not a tty")
                vault = _prompt("Vault path", vault)
                categorization = _prompt("Categorization", categorization, ["topic-first", "project-first", "manual"])
                density = _prompt("Density", density, ["conceptual", "conceptual+snippets"])
                cat_input = _prompt("Categories (comma-separated, leave blank for default)", "")
                if cat_input.strip():
                    categories = cat_input
            config = setup_vault(vault, categorization, density, categories=categories, create_dirs=create_dirs)
            print(f"Resolved vault path: {config['vault_path']}")
            print(json.dumps(config, indent=2))
            return 0
        if args.command == "find":
            tags = [tag for tag in (args.tags or "").split(",") if tag.strip()]
            print(json.dumps(find_existing_note(args.vault, args.title, args.category, tags)))
            return 0
        if args.command == "window":
            config = {}
            if args.config:
                try:
                    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ValueError(f"could not read context config: {exc}") from exc
            limits = config.get("context_window", {})
            max_messages = args.max_messages or limits.get("max_messages", 40)
            max_tokens = args.max_tokens or limits.get("max_tokens", 8000)
            messages, truncated = window_messages(json.load(sys.stdin), max_messages, max_tokens)
            print(json.dumps({
                "messages": messages,
                "truncated": truncated,
                "max_messages": max_messages,
                "max_tokens": max_tokens,
            }))
            return 0
        if args.command == "list":
            if args.json:
                print(json.dumps(tree_to_dict(args.vault, include_meta=args.include_meta), indent=2))
            else:
                print(generate_tree(args.vault, include_meta=args.include_meta))
            return 0
        if args.command == "clone":
            out = clone_note(args.vault, args.source, args.target)
            print(out)
            return 0
        if args.command == "remove":
            out = remove_item(args.vault, args.path, force=args.force)
            print(f"Removed: {out}")
            return 0
        if args.command == "move":
            out = move_item(args.vault, args.source, args.target)
            print(f"Moved to: {out}")
            return 0
        output = capture_note(
            args.vault,
            args.title,
            args.category,
            tags=args.tags,
            session_ref=args.session_ref,
            summary=args.summary,
            bug=args.bug,
            commands=args.commands,
            dry_run=args.dry_run,
            include_internal_refs=args.include_internal_refs,
            window_truncated=args.window_truncated,
            window_n=args.window_n,
        )
        if args.dry_run:
            print(output.rstrip())
            print("DRY-RUN")
        else:
            print(output)
        return 0
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
