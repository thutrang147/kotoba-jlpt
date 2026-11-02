"""Local secrets stay literal; explicit deployment/test settings take priority."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import config


class EnvironmentTests(unittest.TestCase):
    def test_loads_literal_secrets_and_preserves_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / '.env').write_text(
                "DATABASE_URL='postgresql://example/${SECRET}'\n"
                "APP_PASSWORD_HASH='$argon2id$literal'\n"
                "APP_ENV=production\n")
            with patch.object(config, '__file__', str(path / 'config.py')):
                with patch.dict(os.environ, {'APP_ENV': 'development'}, clear=True):
                    self.assertTrue(config.load_environment())
                    self.assertEqual(os.environ['APP_ENV'], 'development')
                    self.assertEqual(os.environ['DATABASE_URL'], 'postgresql://example/${SECRET}')
                    self.assertEqual(os.environ['APP_PASSWORD_HASH'], '$argon2id$literal')

    def test_missing_env_is_allowed_for_render(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(config, '__file__', str(Path(directory) / 'config.py')):
                with patch.dict(os.environ, {'APP_ENV': 'production'}, clear=True):
                    self.assertFalse(config.load_environment())
                    self.assertEqual(dict(os.environ), {'APP_ENV': 'production'})
