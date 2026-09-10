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


if __name__ == "__main__":
    unittest.main()
