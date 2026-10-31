import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


CLIENT = Path(__file__).resolve().parents[1] / "tools/signal_client.py"
spec = importlib.util.spec_from_file_location("signal_client", CLIENT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
TOKEN = "fictional-sender-key-" * 3


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return b'{"status":"ok"}'


class SignalClientTest(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"SIGNAL_API_KEY": TOKEN}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return Response()

    def test_create_and_get_use_post_and_get_without_exposing_key_in_url(self):
        with patch("sys.stdout"):
            client.main(["create", "example-1", "LIVE", "EXA", "12.5", "1792609200"], self.open)
            client.main(["list"], self.open)
            client.main(["get", "example-1"], self.open)
        create, list_request, get = [item[0] for item in self.requests]
        self.assertEqual((create.method, list_request.method, get.method), ("POST", "GET", "GET"))
        self.assertTrue(list_request.full_url.endswith("/signals"))
        self.assertEqual(json.loads(create.data), {
            "signal_id": "example-1", "destination": "LIVE", "ticker": "EXA",
            "price": 12.5, "timestamp": 1792609200,
        })
        self.assertNotIn(TOKEN, create.full_url)
        self.assertEqual(create.headers["Authorization"], "Bearer " + TOKEN)

    def test_edit_and_delete_include_revision(self):
        with patch("sys.stdout"):
            client.main(["edit", "example-1", "1", "--price", "13"], self.open)
            client.main(["delete", "example-1", "2"], self.open)
        edit, delete = [json.loads(item[0].data) for item in self.requests]
        self.assertEqual(edit, {"signal_id": "example-1", "revision": 1, "price": 13.0})
        self.assertEqual(delete, {"signal_id": "example-1", "revision": 2})

    def test_delete_without_revision_fetches_current_revision(self):
        class CurrentResponse(Response):
            def read(self):
                return b'{"revision":4}'

        def open_current(request, timeout):
            self.requests.append((request, timeout))
            return CurrentResponse() if request.method == "GET" else Response()

        with patch("sys.stdout"):
            client.main(["delete", "example-1"], open_current)
        get, delete = [item[0] for item in self.requests]
        self.assertEqual((get.method, delete.method), ("GET", "POST"))
        self.assertEqual(json.loads(delete.data), {"signal_id": "example-1", "revision": 4})

    def test_key_file_must_be_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key"
            path.write_text(TOKEN)
            path.chmod(0o644)
            with patch.dict(os.environ, {"SIGNAL_API_KEY_FILE": str(path)}, clear=True):
                with self.assertRaisesRegex(SystemExit, "mode 0600"):
                    client.credential()

    def test_missing_key_file_has_a_safe_error(self):
        with patch.dict(os.environ, {"SIGNAL_API_KEY_FILE": "/missing/key"}, clear=True):
            with self.assertRaisesRegex(SystemExit, "Cannot read SIGNAL_API_KEY_FILE"):
                client.credential()


if __name__ == "__main__":
    unittest.main()
