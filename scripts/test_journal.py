import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "journal.py"


class JournalTests(unittest.TestCase):
    def run_cli(self, *args, input=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            input=input,
            check=True,
        )

    def setup_vault(self, root, density="conceptual"):
        self.run_cli("setup", "--vault", root, "--density", density, "-y")

    def test_setup_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli("setup", "--vault", root, "-y")
            self.assertTrue((root / "Meta" / "agent.md").exists())
            config = json.loads((root / "Meta" / "journal.config.json").read_text())
            self.assertEqual(config["vault_path"], str(root.resolve()))
            self.assertFalse((root / "AI & Deep Learning").exists())

    def test_duplicate_captures_append_to_one_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            for index in range(3):
                self.run_cli(
                    "capture",
                    "--vault", root,
                    "--title", "KoLeo Regularization",
                    "--category", "AI & Deep Learning",
                    "--summary", f"Session {index} explains KoLeo Regularization.",
                )
            notes = list((root / "AI & Deep Learning").glob("KoLeo Regularization.md"))
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0].read_text().count("## Related Session ("), 2)

    def test_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            secrets = """sk-aaaaaaaaaaaaaaaaAAAA AKIAIOSFODNN7EXAMPLE Bearer abcdef
KEY=supersecret
-----BEGIN PRIVATE KEY-----
private
-----END PRIVATE KEY-----
192.168.1.10 foo.internal"""
            self.run_cli(
                "capture", "--vault", root, "--title", "Secrets", "--category", "Dev & Environment",
                "--summary", secrets,
            )
            output = (root / "Dev & Environment" / "Secrets.md").read_text()
            for secret in ["sk-aaaaaaaaaaaaaaaaAAAA", "AKIAIOSFODNN7EXAMPLE", "Bearer abcdef", "KEY=supersecret", "PRIVATE KEY", "192.168.1.10", "foo.internal"]:
                self.assertNotIn(secret, output)
            self.assertIn("[redacted: possible secret]", output)

    def test_include_internal_refs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Network", "--category", "Dev & Environment",
                "--summary", "Use 192.168.1.10.", "--include-internal-refs",
            )
            self.assertIn("192.168.1.10", (root / "Dev & Environment" / "Network.md").read_text())

    def test_density_controls_fenced_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Concept", "--category", "Dev & Environment",
                "--summary", "before ```python\nprint('x')\n``` after",
            )
            self.assertNotIn("print('x')", (root / "Dev & Environment" / "Concept.md").read_text())
            config_path = root / "Meta" / "journal.config.json"
            config = json.loads(config_path.read_text())
            config["density"] = "conceptual+snippets"
            config_path.write_text(json.dumps(config))
            self.run_cli(
                "capture", "--vault", root, "--title", "Snippet", "--category", "Dev & Environment",
                "--summary", "```python\nprint('sk-aaaaaaaaaaaaaaaaAAAA')\n```",
            )
            output = (root / "Dev & Environment" / "Snippet.md").read_text()
            self.assertIn("print('[redacted: possible secret]')", output)

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            result = self.run_cli(
                "capture", "--vault", root, "--title", "Dry Run", "--category", "Dev & Environment",
                "--summary", "No write", "--dry-run",
            )
            after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertIn("DRY-RUN", result.stdout)

    def test_window_truncated_callout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Window", "--category", "Dev & Environment",
                "--summary", "A summary.", "--window-truncated", "--window-n", "7",
            )
            self.assertIn(
                "> Summarized from the last 7 messages; earlier session content not included.",
                (root / "Dev & Environment" / "Window.md").read_text(),
            )

    def test_window_keeps_recent_messages_within_limits(self):
        messages = [
            {"role": "user", "content": "old message"},
            {"role": "assistant", "content": "middle message"},
            {"role": "user", "content": "recent message"},
        ]
        result = self.run_cli(
            "window", "--max-messages", "2", "--max-tokens", "2",
            input=json.dumps(messages),
        )
        output = json.loads(result.stdout)
        self.assertEqual(len(output["messages"]), 1)
        self.assertEqual(output["messages"][0]["content"], "recent message")
        self.assertTrue(output["truncated"])

    def test_conditional_headers_omitted_when_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Clean Note", "--category", "Dev & Environment",
                "--summary", "Only conceptual summary.",
            )
            content = (root / "Dev & Environment" / "Clean Note.md").read_text()
            self.assertIn("## Conceptual Core", content)
            self.assertNotIn("## Bug / Edge Case Encountered", content)
            self.assertNotIn("## Key CLI Commands & Environment Tricks", content)
            self.assertNotIn("None recorded.", content)
            self.assertNotIn("*None recorded.*", content)

    def test_headers_included_when_content_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Full Note", "--category", "Dev & Environment",
                "--summary", "Concept summary.",
                "--bug", "OOM on GPU buffer allocation.",
                "--commands", "nvidia-smi --query-gpu=memory.used",
            )
            content = (root / "Dev & Environment" / "Full Note.md").read_text()
            self.assertIn("## Conceptual Core", content)
            self.assertIn("## Bug / Edge Case Encountered", content)
            self.assertIn("OOM on GPU buffer allocation.", content)
            self.assertIn("## Key CLI Commands & Environment Tricks", content)
            self.assertIn("nvidia-smi", content)
            self.assertNotIn("None recorded.", content)
            self.assertNotIn("*None recorded.*", content)

    def test_setup_with_custom_categories_and_create_dirs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.run_cli(
                "setup", "--vault", root,
                "--categories", "Research,Distributed Systems,Playground",
                "--create-dirs", "-y"
            )
            config = json.loads((root / "Meta" / "journal.config.json").read_text())
            self.assertEqual(config["categories"], ["Research", "Distributed Systems", "Playground"])
            self.assertTrue((root / "Research").is_dir())
            self.assertTrue((root / "Distributed Systems").is_dir())
            self.assertTrue((root / "Playground").is_dir())

    def test_list_command_tree_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Alpha", "--category", "Dev & Environment",
                "--summary", "Alpha summary.",
            )
            # Text tree test
            res_tree = self.run_cli("list", "--vault", root)
            self.assertIn("Dev & Environment/", res_tree.stdout)
            self.assertIn("Alpha.md", res_tree.stdout)
            self.assertNotIn("Meta/", res_tree.stdout)

            # JSON tree test
            res_json = self.run_cli("list", "--vault", root, "--json")
            data = json.loads(res_json.stdout)
            self.assertEqual(data["name"], "vault")
            names = [child["name"] for child in data["tree"]]
            self.assertIn("Dev & Environment", names)

    def test_file_automation_clone_move_remove(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "vault"
            self.setup_vault(root)
            self.run_cli(
                "capture", "--vault", root, "--title", "Original", "--category", "Dev & Environment",
                "--summary", "Original content.",
            )
            orig_file = root / "Dev & Environment" / "Original.md"
            self.assertTrue(orig_file.exists())

            # Clone
            self.run_cli("clone", "--vault", root, "--source", "Dev & Environment/Original.md", "--target", "Dev & Environment/Cloned.md")
            cloned_file = root / "Dev & Environment" / "Cloned.md"
            self.assertTrue(cloned_file.exists())
            self.assertIn("# Cloned", cloned_file.read_text())

            # Move
            self.run_cli("move", "--vault", root, "--source", "Dev & Environment/Cloned.md", "--target", "Dev & Environment/Moved.md")
            moved_file = root / "Dev & Environment" / "Moved.md"
            self.assertTrue(moved_file.exists())
            self.assertFalse(cloned_file.exists())

            # Remove
            self.run_cli("remove", "--vault", root, "--path", "Dev & Environment/Moved.md")
            self.assertFalse(moved_file.exists())


if __name__ == "__main__":
    unittest.main()
