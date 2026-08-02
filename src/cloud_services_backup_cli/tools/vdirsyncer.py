import subprocess
from pathlib import Path

from ..lib import backup_confd, backup_datad, google_oauth_creds, log_command, require_username, slugify, Service
from . import rsync

"""
vdirsyncer tool module for CalDAV/CardDAV backup.
"""


def vdirsyncer_discover(config_path: Path) -> None:
    cmd = ['vdirsyncer', '-c', str(config_path), 'discover']
    log_command(cmd)
    subprocess.run(cmd, input='yes\n' * 100, text=True, check=True)


def vdirsyncer_sync(config_path: Path) -> None:
    cmd = ['vdirsyncer', '-c', str(config_path), 'sync']
    log_command(cmd)
    subprocess.run(cmd, check=True)


class VDirSyncerService(Service):
    def __init__(self, service_type: str, username: str):
        super().__init__(require_username(username, "google_username", "gmail.com"))

        user_slug = slugify(self.username)
        self.service_type = service_type
        self.user_confd = backup_confd("vdirsyncer", service_type, user_slug)
        self.config_path = self.user_confd / 'vdirsyncer.conf'
        self.status_path = self.user_confd / 'status'
        self.staging_path = self.user_confd / 'staging'
        self.token_path = self.user_confd / 'token.json'
        self.user_backupd = backup_datad(service_type, user_slug)

        self.user_confd.mkdir(parents=True, exist_ok=True)
        self.status_path.mkdir(parents=True, exist_ok=True)
        self.staging_path.mkdir(parents=True, exist_ok=True)
        self.user_backupd.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using config at {self.user_confd}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        print(f"Starting vdirsyncer init for {self.username}...")
        self._reset()
        self._ensure_config()
        vdirsyncer_discover(self.config_path)
        print(f"Ran discovery and created token for {self.username}")

    def setup_required(self) -> bool:
        return not self._is_setup()


    def _backup(self, subcommand: str, *args: str) -> None:
        print(f"Running {subcommand} via vdirsyncer...")
        self._ensure_config()
        vdirsyncer_discover(self.config_path)
        vdirsyncer_sync(self.config_path)
        rsync_args = ['-a']
        if subcommand == 'sync':
            rsync_args.append('--delete')
        rsync.rsync(*rsync_args, f'{self.staging_path}/', str(self.user_backupd))


    def _is_setup(self) -> bool:
        return self.config_path.exists() and self.token_path.exists()

    def _reset(self) -> None:
        self.config_path.unlink(missing_ok=True)
        self.token_path.unlink(missing_ok=True)

    def _ensure_config(self) -> None:
        if self.config_path.exists():
            return
        fileext = '.ics' if self.service_type == 'google_calendar' else '.vcf'
        remote_name = f'{self.service_type}_remote'
        local_name = f'{self.service_type}_local'
        creds = google_oauth_creds()
        creds_lines = ''
        if creds:
            client_id, client_secret = creds
            creds_lines = f'client_id = "{client_id}"\nclient_secret = "{client_secret}"'
        self.config_path.write_text(f"""[general]
status_path = "./{self.status_path.name}"


[pair {self.service_type}]
a = "{remote_name}"
b = "{local_name}"
collections = ["from a"]
partial_sync = "revert"


[storage {remote_name}]
type = "{self.service_type}"
token_file = "{self.token_path}"
read_only = true
{creds_lines}


[storage {local_name}]
type = "filesystem"
path = "{self.staging_path}/"
fileext = "{fileext}"
""")
