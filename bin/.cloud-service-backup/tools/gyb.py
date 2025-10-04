import os
import subprocess
from subprocess import CompletedProcess
import shutil
from pathlib import Path
from lib import *
from tools import shell


def gyb(opts: dict, *args: str) -> CompletedProcess:
    _gyb_run(opts, args, check=True)

def _gyb_run(opts: dict, args: list[str], **kwargs) -> CompletedProcess:
    user_confd = Path(opts['user_confd'])
    user_backupd = Path(opts['user_backupd'])

    if shutil.which("gyb") is not None:
        cmd = [
            "gyb",
            "--config-folder", str(user_confd),
            "--local-folder", str(user_backupd),
            *shell.stringify_args(args)
        ]
        log_command(cmd)
        return subprocess.run(cmd, **kwargs)
    
    cmd = [
        "docker", "run",
        "--rm",
        *shell.docker_flags(),
        "-v", "/etc/localtime:/etc/localtime:ro",
        "-v", "/etc/timezone:/etc/timezone:ro",
        "-v", f"{user_confd}:/config",
        "-v", f"{user_backupd}:/data",
        "-e", "NOCRON=1",
        "-e", "CONFIG_DIR=/config",
        "-e", "DEST_DIR=/data",
        "-e", f"PUID={os.getuid()}",
        "-e", f"PGID={os.getgid()}",
        "awbn/gyb",
        "/app/gyb", *shell.stringify_args(args)
    ]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)
