import os
import subprocess
from subprocess import CompletedProcess
from pathlib import Path
from lib import *
from tools import shell


def git_set_credentials(repo_host: str, git_username: str, access_token_file: Path, credentials_file: Path) -> None:
    access_token = input("Enter access token: ")
    with open(access_token_file, "w") as f:
        f.write(access_token)
    with open(credentials_file, "w") as f:
        f.write(f"https://{git_username}:{access_token}@{repo_host}")

def git_has_credentials(access_token_file, credentials_file):
    return access_token_file.exists() and credentials_file.exists()


def git_mirror_repo(repo_url: str, backup_dir: Path, credentials_file: Path) -> None:
    repo_name = os.path.basename(repo_url.rstrip('/')).replace('.git', '')
    repo_dir = backup_dir.joinpath(repo_name)
    if not os.path.isdir(repo_dir):
        print(f"Creating mirror of {repo_name}...")
        git("clone", "--mirror", 
            "--config", f"credential.helper=store --file {credentials_file}", 
            repo_url, repo_dir)
    else:
        print(f"Updating mirror of {repo_name}...")
        git("--git-dir", repo_dir, "remote", "update")

def git_mirror_repos(repo_urls: list[str], backup_dir: Path, credentials_file: Path) -> None:
    for repo_url in repo_urls:
        git_mirror_repo(repo_url, backup_dir, credentials_file)


def git(*args: str) -> CompletedProcess:
    _git_run(args, check=True)

def _git_run(args: list[str], **kwargs) -> CompletedProcess:
    cmd = ["git", *shell.stringify_args(args)]
    log_command(cmd)
    return subprocess.run(
        cmd,
        env=shell.env(
            # Force git to use credentials we're providing,
            # and not get mixed up with other creds in env
            #GIT_CONFIG_NOSYSTEM='true',
            GIT_CONFIG_SYSTEM='/dev/null',
            GIT_CONFIG_GLOBAL='/dev/null',
        ),
        **kwargs)


class GitHostService(Service):
    def __init__(self, app_slug, service_domain, username):
        super().__init__(require_username(username))
        self.service_domain = service_domain

        user_slug = slugify(self.username)
        self.user_confd = backup_confd(app_slug, user_slug)
        self.user_backupd = backup_datad(app_slug, user_slug)
        self.access_token_file = self.user_confd.joinpath(".git-access-token")
        self.credentials_file = self.user_confd.joinpath(".git-credentials")

        self.user_confd.mkdir(parents=True, exist_ok=True)
        self.user_backupd.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using config at {self.user_confd}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        print(f"Setting up git credentials for {self.username}...")
        git_set_credentials(
            self.service_domain, self.username, self.access_token_file, self.credentials_file)
        print(f"git credentials saved in {self.user_confd}")

    def _force_setup(self) -> bool:
        return not git_has_credentials(self.access_token_file, self.credentials_file)

    def _backup(self, subcommand: str, *args: str) -> None:
        print(f"Retrieving git URLs for all repos owned by {self.username}...")
        repo_urls = self._get_repo_urls()

        print(f"Backing up all repos...")
        git_mirror_repos(repo_urls, self.user_backupd, self.credentials_file)

    def _get_credentials(self) -> tuple[str, str]:
        with open(self.access_token_file, "r") as f:
            access_token = f.read().strip()
        return (self.username, access_token)

    def _get_repo_urls(self) -> list[str]:
        raise NotImplementedError()
