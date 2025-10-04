import subprocess
from subprocess import CompletedProcess
import shutil
from pathlib import Path
from lib import *
from tools import shell


def gcardvault(opts : dict, *args : str) -> CompletedProcess:
    _gcardvault_run(opts, args, check=True)

def _gcardvault_run(opts : dict, args: list[str], **kwargs) -> CompletedProcess:
    user_confd = Path(opts['user_confd'])
    user_backupd = Path(opts['user_backupd'])

    if shutil.which("gcardvault") is not None:
        cmd = ['gcardvault', *shell.stringify_args(args)]
        log_command(cmd)
        return subprocess.run(
            cmd,
            env=shell.env(
                GCARDVAULT_CONF_DIR=str(user_confd),
                GCARDVAULT_OUTPUT_DIR=str(user_backupd),
            ),
            **kwargs)
    
    cmd = [
        "docker", "run",
        "--rm",
        *shell.docker_flags(),
        "-v", "/etc/localtime:/etc/localtime:ro",
        "-v", "/etc/timezone:/etc/timezone:ro",
        "-v", f"{user_confd}:/root/.gcardvault",
        "-v", f"{user_backupd}:/root/gcardvault",
        "rtomac/gcardvault",
        *shell.stringify_args(args)
    ]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)
