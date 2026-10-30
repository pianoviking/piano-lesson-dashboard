import unittest
import os
import tempfile
import json
from config import AppConfig
from read_test_doc import authenticate


class TestContainerConfigAndPersistence(unittest.TestCase):

    def setUp(self):
        self.orig_config_path = os.environ.get("CONFIG_PATH")
        self.orig_token_path = os.environ.get("TOKEN_PATH")
        self.orig_credentials_path = os.environ.get("CREDENTIALS_PATH")
        self.orig_oauth_browser = os.environ.get("OAUTH_ALLOW_BROWSER")

    def tearDown(self):
        # Restore environment
        for key, val in [
            ("CONFIG_PATH", self.orig_config_path),
            ("TOKEN_PATH", self.orig_token_path),
            ("CREDENTIALS_PATH", self.orig_credentials_path),
            ("OAUTH_ALLOW_BROWSER", self.orig_oauth_browser),
        ]:
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def test_env_config_path_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_cfg = os.path.join(tmpdir, "custom_config.json")
            os.environ["CONFIG_PATH"] = custom_cfg

            # Write test data
            test_data = {"prep_document_id": "env_prep_id", "students": []}
            with open(custom_cfg, "w", encoding="utf-8") as f:
                json.dump(test_data, f)

            cfg = AppConfig()
            self.assertEqual(cfg.config_path, custom_cfg)
            self.assertEqual(cfg.prep_document_id, "env_prep_id")

    def test_missing_credentials_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["CREDENTIALS_PATH"] = os.path.join(tmpdir, "nonexistent_credentials.json")
            os.environ["TOKEN_PATH"] = os.path.join(tmpdir, "nonexistent_token.json")
            os.environ["OAUTH_ALLOW_BROWSER"] = "false"

            with self.assertRaises(RuntimeError) as ctx:
                authenticate()
            self.assertIn("ontbreekt", str(ctx.exception))

    def test_missing_token_file_no_browser_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_path = os.path.join(tmpdir, "dummy_credentials.json")
            with open(creds_path, "w") as f:
                f.write("{}")

            os.environ["CREDENTIALS_PATH"] = creds_path
            os.environ["TOKEN_PATH"] = os.path.join(tmpdir, "nonexistent_token.json")
            os.environ["OAUTH_ALLOW_BROWSER"] = "false"

            with self.assertRaises(RuntimeError) as ctx:
                authenticate()
            self.assertIn("interactieve login is uitgeschakeld", str(ctx.exception))

    def test_config_changes_persist_across_recreation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            os.environ["CONFIG_PATH"] = cfg_path

            # Initial state
            cfg1 = AppConfig()
            cfg1.prep_document_id = "doc_123"
            cfg1.add_or_update_student("s1", "Test Student", "doc_s1")
            cfg1.save()

            # "Container recreation" - simulate loading anew from disk
            cfg2 = AppConfig()
            self.assertEqual(cfg2.prep_document_id, "doc_123")
            self.assertEqual(len(cfg2.students), 1)
            self.assertEqual(cfg2.students[0]["name"], "Test Student")


if __name__ == "__main__":
    unittest.main()
