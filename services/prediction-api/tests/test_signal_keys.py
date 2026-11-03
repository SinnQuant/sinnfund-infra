import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "tools/signal_keys.py"
spec = importlib.util.spec_from_file_location("signal_keys", SCRIPT)
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)


class SignalKeysTest(unittest.TestCase):
    def setUp(self):
        self.installed = ""

    def download(self, scope, path):
        path.write_text("existing:{SHA}old\n")

    def install(self, scope, path):
        self.installed = path.read_text()

    def test_create_multiple_keys_interactively(self):
        answers = iter(("sender", "2", "alice", "bob"))
        with patch("builtins.input", side_effect=lambda _: next(answers)), \
                patch.object(keys, "download", side_effect=self.download), \
                patch.object(keys, "install", side_effect=self.install), \
                patch.object(keys.secrets, "token_hex", side_effect=("a" * 64, "b" * 64)), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            keys.main(["create"])
        self.assertIn("existing:{SHA}old", self.installed)
        self.assertIn("alice:{SHA}", self.installed)
        self.assertIn("bob:{SHA}", self.installed)
        self.assertIn("alice: " + "a" * 64, output.getvalue())
        self.assertIn("bob: " + "b" * 64, output.getvalue())

    def test_existing_key_requires_explicit_rotation(self):
        answers = iter(("sender", "1", "existing", "no"))
        with patch("builtins.input", side_effect=lambda _: next(answers)), \
                patch.object(keys, "download", side_effect=self.download), \
                patch.object(keys, "install", side_effect=self.install), \
                self.assertRaisesRegex(SystemExit, "Nothing changed"):
            keys.main(["create"])
        self.assertEqual(self.installed, "")

    def test_list_never_prints_hashes(self):
        with patch("builtins.input", return_value="sender"), \
                patch.object(keys, "download", side_effect=self.download), \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            keys.main(["list"])
        self.assertEqual(output.getvalue(), "existing\n")

    def test_revoke_multiple_keys(self):
        def download(scope, path):
            path.write_text("alice:{SHA}one\nbob:{SHA}two\nkeep:{SHA}three\n")

        answers = iter(("sender", "2", "alice", "bob"))
        with patch("builtins.input", side_effect=lambda _: next(answers)), \
                patch.object(keys, "download", side_effect=download), \
                patch.object(keys, "install", side_effect=self.install), \
                patch("sys.stdout", new_callable=io.StringIO):
            keys.main(["revoke"])
        self.assertEqual(self.installed, "keep:{SHA}three\n")


if __name__ == "__main__":
    unittest.main()
