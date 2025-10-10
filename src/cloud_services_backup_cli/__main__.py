import os
import sys
import logging

from .lib import *
from . import services

LOG_LEVEL = logging.INFO

dirname = os.path.dirname(__file__)
usage_file_path = os.path.join(dirname, "USAGE.txt")


def main():
    run(sys.argv)

def run(argv: list[str]) -> None:
    setup_logging()
    check_env()

    command = argv[1] if len(argv) > 1 else "help"
    if command in ("", "help"):
        usage()
        sys.exit(0)
    
    service_slug = command
    try:
        service_type = resolve_service(service_slug)
    except KeyError:
        error(f"Invalid service '{service_slug}'")

    subcommand = argv[2] if len(argv) > 2 else "help"
    if subcommand not in ("help", "setup", "copy", "sync"):
        error(f"Invalid subcommand '{subcommand}'")

    if subcommand == "help":
        service_usage(service_type)
        sys.exit(0)
    
    username = argv[3] if len(argv) > 3 else None
    service = service_type(username)
    service.info()
    try:
        func = getattr(service, subcommand)
        func(*argv[4:])
    except KeyboardInterrupt:
        print("Keyboard interrupt detected, exiting...")
        
    sys.exit(0)

def setup_logging() -> None:
    stdout = logging.StreamHandler(sys.stdout)
    stdout.addFilter(lambda r: r.levelno <= logging.INFO)

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setLevel(logging.WARNING)

    logging.basicConfig(level=LOG_LEVEL, format="%(message)s", handlers=[ stdout, stderr ])

def check_env() -> None:
    # Backward compat for old env var names
    if os.environ.get("BACKUPCONFD"):
        os.environ.setdefault("CLOUD_BACKUP_CONFD", os.environ["BACKUPCONFD"])
    if os.environ.get("BACKUPDATAD"):
        os.environ.setdefault("CLOUD_BACKUP_DATAD", os.environ["BACKUPDATAD"])

    # Ensure required env vars
    if not os.environ.get("CLOUD_BACKUP_CONFD"):
        error("Environment variable CLOUD_BACKUP_CONFD is expected")
    if not os.environ.get("CLOUD_BACKUP_DATAD"):
        error("Environment variable CLOUD_BACKUP_DATAD is expected")

    # Ensure directories exist
    os.makedirs(os.environ["CLOUD_BACKUP_CONFD"], exist_ok=True)
    os.makedirs(os.environ["CLOUD_BACKUP_DATAD"], exist_ok=True)

def usage() -> None:
    with open(usage_file_path) as f:
        print_usage(f.read())

def service_usage(service_type: type) -> None:
    usage_text = get_service_usage(service_type)
    print_usage(usage_text)


if __name__ == '__main__':
    main()
