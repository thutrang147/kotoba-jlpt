"""A disconnected browser must not trigger a second HTTP response after login."""
import io
import unittest
from unittest.mock import Mock, patch

import server


class DisconnectTests(unittest.TestCase):
    def handler(self, path):
        handler = object.__new__(server.Handler)
        handler.path = path
        handler.headers = {'Content-Length': '19'}
        handler.rfile = io.BytesIO(b'{"password":"test"}')
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.close_connection = False
        return handler

    def test_successful_login_disconnect_does_not_send_error_or_repeat_login(self):
        for error in (BrokenPipeError, ConnectionResetError):
            with self.subTest(error=error):
                handler = self.handler('/api/login')
                handler.wfile.write.side_effect = error()
                with patch('online.login', return_value='test-session') as login:
                    handler.do_POST()
                login.assert_called_once()
                handler.send_response.assert_called_once_with(200)
                self.assertTrue(handler.close_connection)

    def test_disconnected_healthcheck_does_not_send_database_error(self):
        handler = self.handler('/healthz')
        handler.end_headers.side_effect = BrokenPipeError()
        handler.do_GET()
        handler.send_response.assert_called_once_with(200)
        self.assertTrue(handler.close_connection)
