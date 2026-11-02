"""No-login mode bypasses session lookups while production still needs Neon."""
import os
import unittest
from unittest.mock import patch
import online
import server


class NoAuthTests(unittest.TestCase):
    def test_default_allows_access_without_session_database_lookup(self):
        with patch.dict(os.environ, {'APP_ENV':'production', 'DATABASE_URL':'postgresql://example',
                                     'APP_PASSWORD_HASH':'unused-invalid-old-hash'}, clear=True):
            online.validate_config()
            self.assertFalse(online.auth_enabled())
            with patch.object(server,'connect',side_effect=AssertionError('Unnecessary session query')):
                self.assertTrue(online.authenticated(server,{}))

    def test_production_still_requires_postgres(self):
        with patch.dict(os.environ, {'APP_ENV':'production','APP_AUTH_REQUIRED':'0'}, clear=True):
            with self.assertRaises(RuntimeError):online.validate_config()

    def test_login_can_be_explicitly_enabled(self):
        with patch.dict(os.environ, {'APP_ENV':'production','DATABASE_URL':'postgresql://example',
                                     'APP_AUTH_REQUIRED':'1'}, clear=True):
            with self.assertRaises(RuntimeError):online.validate_config()
