import sys
import os
from pathlib import Path
import logging
from typing import Optional, Tuple, Union, List, Dict


def backup_confd(*args: str) -> Path:
    return Path(os.environ["CLOUD_BACKUP_CONFD"]).joinpath(*args)

def backup_datad(*args: str) -> Path:
    return Path(os.environ["CLOUD_BACKUP_DATAD"]).joinpath(*args)

def backup_tmpd() -> Path:
    tmpd = backup_datad("tmp")
    tmpd.mkdir(parents=True, exist_ok=True)
    return tmpd

def google_oauth_creds() -> Optional[Tuple[str, str]]:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if client_id and client_secret:
        return (client_id, client_secret)
    return None

def google_oauth_creds_as_params(
    client_id_key: str = "client-id", client_secret_key: str = "client-secret"
) -> Dict[str, str]:
    creds = google_oauth_creds()
    if creds:
        client_id, client_secret = creds
        return { client_id_key: client_id, client_secret_key: client_secret }
    return {}

def google_oauth_creds_as_args(
    client_id_key: str = "--client-id", client_secret_key: str = "--client-secret"
) -> List[str]:
    creds = google_oauth_creds()
    if creds:
        client_id, client_secret = creds
        return [client_id_key, client_id, client_secret_key, client_secret]
    return []


def error(msg: str) -> None:
    print(msg, file=sys.stderr)
    exit(1)


def print_usage(text: str) -> None:
    print(f"\n{text.strip()}\n")

def log_command(cmd: List[str]) -> None:
    logging.debug(f'Running command: "{" ".join(cmd)}"')


def require_arg(args: List[str], position: int, arg_name: str) -> str:
    if len(args) <= position:
        error(f"{arg_name} arg required")
    return args[position]

def require_username(
    value: str, arg_name: str = "username", default_domain: Optional[str] = None
) -> str:
    if not value:
        error(f"{arg_name} arg required")
    if default_domain and "@" not in value:
        return f"{value}@{default_domain}"
    return value


def slugify(value: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in value.lower())


def list_subdirs(parent_dir: Union[str, Path]) -> List[Path]:
    path = Path(parent_dir)
    return sorted(
        [entry for entry in path.iterdir() if entry.is_dir()],
        key=lambda e: e.name.lower()
    )

def list_files(parent_dir: Union[str, Path]) -> List[Path]:
    path = Path(parent_dir)
    return sorted(
        [entry for entry in path.iterdir() if entry.is_file()],
        key=lambda e: e.name.lower()
    )
