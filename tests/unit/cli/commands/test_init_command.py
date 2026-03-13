import pytest
from argparse import Namespace
from ghostclaw.cli.commands.init import InitCommand

@pytest.mark.asyncio
async def test_init_command_execute(mocker, tmp_path):
    cmd = InitCommand()
    args = Namespace()

    mock_init_project = mocker.patch("ghostclaw.cli.commands.init.ConfigService.init_project")

    result = await cmd.execute(args)
    assert result == 0
    mock_init_project.assert_called_once_with(".")

@pytest.mark.asyncio
async def test_init_command_execute_failure(mocker, capsys):
    cmd = InitCommand()
    args = Namespace()

    mock_init_project = mocker.patch("ghostclaw.cli.commands.init.ConfigService.init_project")
    mock_init_project.side_effect = Exception("Failed")

    result = await cmd.execute(args)
    assert result == 1
    captured = capsys.readouterr()
    assert "Failed" in captured.err
