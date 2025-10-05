import subprocess
from subprocess import CompletedProcess
from lib import *
from tools import shell


def rsync(*args: str) -> CompletedProcess:
    _rsync_run(args, check=True)

def _rsync_run(args: list[str], **kwargs) -> CompletedProcess:
    cmd = ["rsync", *shell.stringify_args(args)]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)
