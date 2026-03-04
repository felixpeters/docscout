"""Tests for verbose logging module."""

import io
from unittest.mock import patch

from docscout.logging import is_verbose, log, set_verbose


class TestVerboseLogging:
    def setup_method(self):
        set_verbose(False)

    def teardown_method(self):
        set_verbose(False)

    def test_default_is_off(self):
        assert is_verbose() is False

    def test_set_verbose_on(self):
        set_verbose(True)
        assert is_verbose() is True

    def test_set_verbose_off(self):
        set_verbose(True)
        set_verbose(False)
        assert is_verbose() is False

    def test_log_outputs_when_verbose(self):
        set_verbose(True)
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            log("test message")
            output = mock_stderr.getvalue()
            assert "[docscout] test message" in output

    def test_log_silent_when_not_verbose(self):
        set_verbose(False)
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            log("test message")
            assert mock_stderr.getvalue() == ""
