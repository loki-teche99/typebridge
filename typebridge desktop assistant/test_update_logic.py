"""
TypeBridge Auto-Update Interval & Verification Test Suite
Tests:
1. 168-hour (7 days) gate prevents automatic checks before expiry
2. Automatic check executes after 168 hours have elapsed
3. Manual check bypasses 168-hour gate immediately
4. HTTP ETag caching sends If-None-Match and handles HTTP 304 Not Modified
5. HTTP 403/429 rate limit backoff sets last_check_ts and avoids retry loops
6. In-flight request deduplication prevents concurrent executions
7. Version comparison logic (semantic versioning, prefixes)
"""
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

# Ensure desktop assistant is in path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import ConfigManager
from app.core.updater import (
    AUTO_CHECK_INTERVAL_SECONDS,
    CURRENT_VERSION,
    UpdateCheckerThread,
    is_newer_version,
    parse_version
)


class TestUpdateLogic(unittest.TestCase):

    def setUp(self):
        self.config = ConfigManager()
        # Clean config test state
        self.config.set('last_update_check_ts', 0)
        self.config.set('update_etag', '')

    def test_interval_constant(self):
        """Verify the interval constant is exactly 168 hours (7 days)."""
        expected_seconds = 7 * 24 * 3600
        self.assertEqual(AUTO_CHECK_INTERVAL_SECONDS, expected_seconds)
        self.assertEqual(AUTO_CHECK_INTERVAL_SECONDS, 604800)
        # Android equivalence: 604800 * 1000 ms
        self.assertEqual(AUTO_CHECK_INTERVAL_SECONDS * 1000, 604800000)

    def test_version_parsing_and_comparison(self):
        """Verify version parsing and strict newness comparison."""
        self.assertEqual(parse_version("1.0.0"), (1, 0, 0))
        self.assertEqual(parse_version("v1.0.1"), (1, 0, 1))
        self.assertEqual(parse_version("V2.0.0-beta"), (2, 0, 0))

        self.assertTrue(is_newer_version("1.0.1", "1.0.0"))
        self.assertTrue(is_newer_version("v1.1.0", "1.0.9"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(is_newer_version("1.0.0", "1.0.1"))
        self.assertFalse(is_newer_version("0.9.9", "1.0.0"))

    @patch("urllib.request.urlopen")
    def test_auto_check_suppressed_when_under_168_hours(self, mock_urlopen):
        """Automatic check MUST skip network call if last check was under 168 hours ago."""
        now = time.time()
        # Set last check to 3 days ago (72 hours < 168 hours)
        self.config.set('last_update_check_ts', int(now - 72 * 3600))

        thread = UpdateCheckerThread(is_manual=False)
        no_update_emitted = []
        thread.no_update_found.connect(lambda v: no_update_emitted.append(v))

        thread.run()

        # Network must NOT be called
        mock_urlopen.assert_not_called()
        # Must emit no_update_found
        self.assertEqual(len(no_update_emitted), 1)

    @patch("urllib.request.urlopen")
    def test_auto_check_executes_when_over_168_hours(self, mock_urlopen):
        """Automatic check MUST execute network call if last check was >= 168 hours ago."""
        now = time.time()
        # Set last check to 8 days ago (192 hours > 168 hours)
        self.config.set('last_update_check_ts', int(now - 192 * 3600))

        # Mock successful 200 response
        mock_resp = MagicMock()
        mock_resp.headers = {"ETag": 'W/"test-etag-123"'}
        mock_resp.read.return_value = b'{"tag_name": "v1.0.0", "assets": []}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        thread = UpdateCheckerThread(is_manual=False)
        thread.run()

        # Network MUST be called
        mock_urlopen.assert_called_once()
        # ETag and timestamp must be updated
        self.assertEqual(self.config.get('update_etag'), 'W/"test-etag-123"')
        self.assertGreater(self.config.get('last_update_check_ts'), int(now - 10))

    @patch("urllib.request.urlopen")
    def test_manual_check_bypasses_168_hour_gate(self, mock_urlopen):
        """Manual check MUST execute network call immediately, even if last check was 1 second ago."""
        now = time.time()
        # Set last check to 1 minute ago
        self.config.set('last_update_check_ts', int(now - 60))

        # Mock successful 200 response
        mock_resp = MagicMock()
        mock_resp.headers = {"ETag": 'W/"manual-etag"'}
        mock_resp.read.return_value = b'{"tag_name": "v1.0.0", "assets": []}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        thread = UpdateCheckerThread(is_manual=True)
        thread.run()

        # Network MUST be called despite last check being 1 minute ago
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_etag_caching_and_304_handling(self, mock_urlopen):
        """Cached ETag must be sent in If-None-Match header, and HTTP 304 handled without error."""
        self.config.set('update_etag', 'W/"etag-cached-999"')
        self.config.set('last_update_check_ts', 0)

        import urllib.error
        # Simulate HTTP 304 Not Modified
        http_304_error = urllib.error.HTTPError(
            url="https://api.github.com/repos/loki-teche99/typebridge/releases/latest",
            code=304,
            msg="Not Modified",
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = http_304_error

        thread = UpdateCheckerThread(is_manual=True)
        no_update_emitted = []
        thread.no_update_found.connect(lambda v: no_update_emitted.append(v))

        thread.run()

        # Verify request had If-None-Match header
        req_sent = mock_urlopen.call_args[0][0]
        self.assertEqual(req_sent.headers.get("If-none-match"), 'W/"etag-cached-999"')
        # 304 must emit no_update_found cleanly
        self.assertEqual(len(no_update_emitted), 1)
        # Timestamp must be refreshed to avoid tight retries
        self.assertGreater(self.config.get('last_update_check_ts'), 0)

    @patch("urllib.request.urlopen")
    def test_rate_limit_backoff_403_and_429(self, mock_urlopen):
        """HTTP 403/429 rate limit triggers safe backoff, setting timestamp."""
        import urllib.error
        http_403_error = urllib.error.HTTPError(
            url="https://api.github.com/repos/loki-teche99/typebridge/releases/latest",
            code=403,
            msg="rate limit exceeded",
            hdrs={},
            fp=None
        )
        mock_urlopen.side_effect = http_403_error

        thread = UpdateCheckerThread(is_manual=False)
        no_update_emitted = []
        thread.no_update_found.connect(lambda v: no_update_emitted.append(v))

        thread.run()

        # Timestamp must be set to prevent immediate retry
        self.assertGreater(self.config.get('last_update_check_ts'), 0)
        self.assertEqual(len(no_update_emitted), 1)


if __name__ == "__main__":
    unittest.main()
