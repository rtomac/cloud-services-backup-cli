from abc import abstractmethod
import os
import subprocess
from subprocess import CompletedProcess
from pathlib import Path

from ..lib import *
from . import shell

def rclone_config() -> Path:
    config = os.environ.get(
        "RCLONE_CONFIG",
        str(backup_confd().joinpath("rclone", "rclone.conf")))
    return Path(config)

def rclone_remote_name(app_slug: str, user_slug: str) -> str:
    return f"{app_slug}+{user_slug}"


def rclone_has_remote(remote: str) -> bool:
    remotes = rclone_pipe("listremotes").splitlines()
    return f"{remote}:" in remotes

def rclone_create_remote_silent(remote: str, remote_type: str, *args : str) -> None:
    # config_is_local=false will skip authz and make non-interactive
    rclone(
        "config",
        "create", remote, remote_type,
        *args,
        "config_is_local", "false",
    )

def rclone_authorize_user(remote: str) -> None:
    # Will start interactive OAuth2 flow
    rclone("config", "reconnect", f"{remote}:")


def rclone(*args: str) -> CompletedProcess:
    return __rclone_run(args, check=True)

def rclone_pipe(*args: str) -> str:
    result = __rclone_run(args, check=True, capture_output=True, text=True)
    return result.stdout

def __rclone_run(args: list[str], **kwargs) -> CompletedProcess:
    config_path = rclone_config()
    os.makedirs(config_path.parent, exist_ok=True)
    cmd = ['rclone', *shell.stringify_args(args)]
    log_command(cmd)
    return subprocess.run(cmd, env=shell.env(RCLONE_CONFIG=str(config_path)), **kwargs)


class RcloneService(Service):
    def __init__(self, app_slug: str, username: str):
        super().__init__(require_username(username))
        
        user_slug = slugify(self.username)
        self.rclone_remote = rclone_remote_name(app_slug, user_slug)
        self.user_backupd = backup_datad(app_slug, user_slug)

        self.user_backupd.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using rclone remote '{self.rclone_remote}' with config at {rclone_config()}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        print(f"Configuring rclone remote '{self.rclone_remote}'...")
        self._create_remote_silent()

        print(f"Authorizing user for remote '{self.rclone_remote}'...")
        rclone_authorize_user(self.rclone_remote)

        print(f"rclone remote '{self.rclone_remote}' setup succeeded ")

    def setup_required(self) -> bool:
        return not rclone_has_remote(self.rclone_remote)

    @abstractmethod
    def _create_remote_silent(self) -> None:
        raise NotImplementedError()
