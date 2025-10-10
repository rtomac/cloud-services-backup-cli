import subprocess
from subprocess import CompletedProcess
import shutil
from pathlib import Path

from ..lib import *
from . import shell

def gcalvault(opts : dict, *args : str) -> CompletedProcess:
    return __gcalvault_run(opts, args, check=True)

def __gcalvault_run(opts : dict, args : list[str], **kwargs) -> CompletedProcess:
    user_confd = Path(opts['user_confd'])
    user_backupd = Path(opts['user_backupd'])

    if shutil.which("gcalvault") is not None:
        cmd = ['gcalvault', *shell.stringify_args(args)]
        log_command(cmd)
        return subprocess.run(
            cmd,
            env=shell.env(
                GCALVAULT_CONF_DIR=str(user_confd),
                GCALVAULT_OUTPUT_DIR=str(user_backupd),
            ),
            **kwargs)
    
    cmd = [
        "docker", "run",
        "--rm",
        *shell.docker_flags(),
        "-v", "/etc/localtime:/etc/localtime:ro",
        "-v", "/etc/timezone:/etc/timezone:ro",
        "-v", f"{user_confd}:/root/.gcalvault",
        "-v", f"{user_backupd}:/root/gcalvault",
        "rtomac/gcalvault",
        *shell.stringify_args(args)
    ]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)
