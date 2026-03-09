import pytest
import sys
from unittest.mock import patch
from ghostclaw.cli.ghostclaw import main

def test_legacy_fallback(mocker, capsys):
    """Test that unknown command shows error and exits with code 2 (argparse)."""
    test_args = ["ghostclaw.py", "invalid_command"]
    with patch.object(sys, 'argv', test_args):
        mock_exit = mocker.patch("ghostclaw.cli.ghostclaw.sys.exit")

        try:
            main()
        except SystemExit:
            pass  # main() calls sys.exit which is mocked

        captured = capsys.readouterr()
        # Should show argparse error about invalid choice
        assert "invalid choice: 'invalid_command'" in captured.err or "unrecognized arguments: invalid_command" in captured.err
        # Expect exit code 2 (argument error)
        mock_exit.assert_called_with(2)
