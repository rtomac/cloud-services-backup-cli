import subprocess
import tempfile
from pathlib import Path

from ..lib import backup_confd, backup_datad, error, google_oauth_creds, log_command, require_username, slugify, Service
from . import oauth2, rsync

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
    def __init__(self, username: str):
        super().__init__(require_username(username, "google_username", "gmail.com"))

        if not google_oauth_creds():
            error("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are required")

        user_slug = slugify(self.username)
        self.user_confd = backup_confd("vdirsyncer", self.storage_type, user_slug)
        self.config_path = self.user_confd / 'vdirsyncer.conf'
        self.status_path = self.user_confd / 'status'
        self.staging_path = self.user_confd / 'staging'
        self.token_path = self.user_confd / 'token.json'
        self.user_backupd = backup_datad(self.storage_type, user_slug)

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
        self._auth_and_discover()
        print(f"Ran authorization and discovery for {self.username}")

    def setup_required(self) -> bool:
        return not self._is_setup()

    @classmethod
    def authorize(cls, payload: str = None) -> None:
        oauth2.require_browser()
        username, creds = oauth2.decode_payload(payload)
        require_username(username, "google_username", "gmail.com")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            token_path = tmpdir / 'token.json'
            status_path = tmpdir / 'status'
            staging_path = tmpdir / 'staging'
            config_path = tmpdir / 'vdirsyncer.conf'
            status_path.mkdir()
            staging_path.mkdir()
            cls._write_config(config_path, token_path, status_path, staging_path, creds=creds)
            vdirsyncer_discover(config_path)
            oauth2.print_authorize_token_export(token_path.read_text())


    def _backup(self, subcommand: str, *args: str) -> None:
        print(f"Running {subcommand} via vdirsyncer...")

        self._ensure_config()
        self._auth_and_discover()
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
        self._write_config(self.config_path, self.token_path, self.status_path, self.staging_path)

    @classmethod
    def _write_config(cls, config_path: Path, token_path: Path, status_path: Path, staging_path: Path, creds=None) -> None:
        remote_name = f'{cls.storage_type}_remote'
        local_name = f'{cls.storage_type}_local'

        creds = creds or google_oauth_creds()
        creds_lines = ''
        if creds:
            client_id, client_secret = creds
            creds_lines = f'client_id = "{client_id}"\nclient_secret = "{client_secret}"'

        config_path.write_text(f"""[general]
status_path = "{status_path}/"


[pair {cls.storage_type}]
a = "{remote_name}"
b = "{local_name}"
collections = ["from a"]
partial_sync = "revert"


[storage {remote_name}]
type = "{cls.storage_type}"
token_file = "{token_path}"
read_only = true
{creds_lines}


[storage {local_name}]
type = "filesystem"
path = "{staging_path}/"
fileext = "{cls.file_ext}"
""")

    def _auth_and_discover(self) -> None:
        if not self.token_path.exists() and not oauth2.has_browser():
            token = oauth2.prompt_for_authorize(self.service_slug, self.username)
            self.token_path.write_text(token)
            print(f"Token saved to {self.token_path}")
        vdirsyncer_discover(self.config_path)
