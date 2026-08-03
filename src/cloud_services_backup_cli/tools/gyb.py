import subprocess
from subprocess import CompletedProcess
from pathlib import Path

from ..lib import *
from . import shell


def gyb(opts: dict, *args: str) -> CompletedProcess:
    return __gyb_run(opts, args, check=True)

def __gyb_run(opts: dict, args: list[str], **kwargs) -> CompletedProcess:
    user_confd = Path(opts['user_confd'])
    user_backupd = Path(opts['user_backupd'])

    cmd = [
        "gyb",
        "--config-folder", str(user_confd),
        "--local-folder", str(user_backupd),
        *shell.stringify_args(args)
    ]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)
