from abc import abstractmethod
import logging
import shutil
import tarfile
import zipfile
from pathlib import Path
from lib import *
from tools.rclone import *
from tools.rsync import *
from .google_drive import GoogleDrive


@register_service("google-takeout")
class GoogleTakeout(Service):
    """
Backs up files from Google Takeout archives that are
created and saved into Google Drive (one of the options
Google Takeout provides). Uses rclone with a 'drive'
remote to download the archive files, extracts them into
export folders, and then syncs them into a single
backup folder that will store the latest export for each
Google product.

The idea here is to allow a user to manually schedule Takeout
archives but automate it all the rest of the way. Google allows
you to schedule a year's worth of archives, six archives every
two months.

Subcommands:
  setup <google_username>
        Runs an auth flow with Google to create an access token.
  copy <google_username>
        Downloads archive files and syncs contents for each
        included product into the backup dir. Additive only,
        will not remove any existing files in the backup dir.
  sync <google_username>
        Downloads archive files and syncs contents for each
        included product into the backup dir. For product folders
        included in the export, will sync them fully to the backup
        folder, removing any files that were removed in the export.
        However, will not touch any product folders that aren't
        included in the export.

OAuth2 authentication:
  If you are providing your own Google OAuth2 client (via environment
  variables), you will need to ensure the correct APIs and OAuth2 scopes
  are enabled. See:
  https://rclone.org/drive/#making-your-own-client-id
    """
    SYNC_SUBDIRS_FOR = ["Google Photos"]

    def __init__(self, username: str):
        super().__init__(
            require_username(username, "google_username", "gmail.com"))

        user_slug = slugify(self.username)
        self.google_drive = GoogleDrive(self.username)
        self.rclone_remote = self.google_drive.rclone_remote
        self.user_backupd = backup_datad("google_takeout", user_slug)
        self.user_backupd_archives = self.user_backupd.joinpath("archives")
        self.user_backupd_files = self.user_backupd.joinpath("takeout")

        self.user_backupd.mkdir(parents=True, exist_ok=True)
        self.user_backupd_archives.mkdir(parents=True, exist_ok=True)
        self.user_backupd_files.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using rclone remote '{self.rclone_remote}' with config at {rclone_config()}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        self.google_drive.setup()

    def setup_required(self) -> bool:
        return self.google_drive.setup_required()

    def sync_and_extract_exports(self, subcommand: str) -> None:
        print(f"Starting rclone {subcommand} to download/sync archives...")
        self.__sync_archives_from_remote(subcommand)

        print("Extracting archives...")
        self.__extract_exports()
        self.__cleanup_extracts()

    def get_extract_dirs(self) -> list[Path]:
        return list_subdirs(self.user_backupd_archives)

    def _backup(self, subcommand: str, *args: str) -> None:
        self.sync_and_extract_exports(subcommand)

        print("Backing up takeout files...")
        self.__sync_exports(subcommand)

    def __sync_archives_from_remote(self, subcommand: str) -> None:
        rclone(
            subcommand,
            "--stats-log-level", "NOTICE",
            "--stats", "1m",
            "--include", "*.tgz", "--include", "*.zip",
            f"{self.rclone_remote}:/Takeout/",
            f"{self.user_backupd_archives}/",
        )

    def __get_exports(self) -> list[tuple[str, Path, list[Path]]]:
        exports = {}

        for entry in sorted(Path(self.user_backupd_archives).iterdir(), key=lambda e: e.name.lower()):
            if entry.is_file() and entry.suffix.lower() in {".tgz", ".zip"}:
                archive_name = entry.name
                if archive_name.lower().startswith("takeout-"):
                    export_name = "-".join(archive_name.split("-")[:2])
                    key = export_name.lower()
                    export = exports.setdefault(key, [export_name, self.user_backupd_archives / export_name, []])
                    export[2].append(entry)
                    logging.debug(f"Found archive '{archive_name}' in export '{export_name}'")

        return sorted(exports.values(), key=lambda e: e[0])

    def __extract_exports(self) -> None:
        for export in self.__get_exports():
            (export_name, extract_dir, archives) = export
            if not extract_dir.exists():
                self.__extract_export(export)
            else:
                print(f"Skipping {export_name}, extract folder already exists")

    def __extract_export(self, export: tuple[str, Path, list[Path]]) -> None:
        (export_name, extract_dir, archives) = export
        print(f"Extracting export '{export_name}'...")
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            for archive in archives:
                self.__extract_archive(archive, extract_dir)
        except Exception as e:
            shutil.rmtree(extract_dir.resolve(), ignore_errors=True)
            error(f"Failed to extract archives for export {export_name}")

    def __extract_archive(self, archive: Path, extract_dir: Path) -> None:
        print(f"Extracting archive {archive.name}...")
        try:
            if archive.name.endswith(".tgz"):
                with tarfile.open(archive.resolve(), "r:gz") as tar:
                    tar.extractall(path=extract_dir.resolve())
            elif archive.name.endswith(".zip"):
                with zipfile.ZipFile(archive.resolve(), "r") as zip_ref:
                    zip_ref.extractall(extract_dir.resolve())
        except Exception as e:
            print(f"Failed to extract {archive.name}: {e}")
            raise
    
    def __cleanup_extracts(self) -> None:
        for extract_dir in self.get_extract_dirs():
            archive_exists = any(
                entry.name.startswith(extract_dir.name) and entry.suffix in (".tgz", ".zip")
                    for entry in self.user_backupd_archives.iterdir()
            )
            if not archive_exists:
                print(f"Deleting folder {extract_dir.name}, no corresponding archive found...")
                shutil.rmtree(extract_dir.resolve(), ignore_errors=True)

    def __sync_exports(self, subcommand: str) -> None:
        for extract_dir in self.get_extract_dirs():
            source_root_dir = extract_dir.joinpath("Takeout")
            if not source_root_dir.exists() or not source_root_dir.is_dir(): continue

            print(f"Synchronizing files from export '{extract_dir.name}'...")
            
            # Go one-by-one through Google product folders in source export,
            # so we don't remove any product folders that aren't in this export
            for source_product_dir in list_subdirs(source_root_dir):
                if source_product_dir.name not in self.SYNC_SUBDIRS_FOR:
                    self.__sync_export_subdir(subcommand, source_root_dir, self.user_backupd_files, source_product_dir.name)
                else:
                    for source_product_subdir in list_subdirs(source_product_dir):
                        self.__sync_export_subdir(subcommand, source_root_dir, self.user_backupd_files, f"{source_product_dir.name}/{source_product_subdir.name}")

    def __sync_export_subdir(self, subcommand: str, source_root_dir: Path, dest_root_dir: Path, relative_dir: str) -> None:
        source_dir = source_root_dir.joinpath(relative_dir)
        dest_dir = dest_root_dir.joinpath(relative_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        rsync_flags = ["--archive", "--update", "-v"]
        if subcommand == "sync":
            rsync_flags.append("--delete")
        
        print(f"Synchronizing files in '{relative_dir}'...")
        rsync(*rsync_flags, f"{source_dir}/", f"{dest_dir}/")


class GoogleTakeoutAddonService(Service):
    def __init__(self, app_slug: str, username: str):
        super().__init__(
            require_username(username, "google_username", "gmail.com"))

        user_slug = slugify(self.username)
        self.google_takeout = GoogleTakeout(self.username)
        self.user_backupd = backup_datad(app_slug, user_slug)

        self.user_backupd.mkdir(parents=True, exist_ok=True)

    def info(self) -> None:
        print(f"Using rclone remote '{self.google_takeout.rclone_remote}' with config at {rclone_config()}")
        print(f"Using takeout archives in {self.google_takeout.user_backupd_archives}")
        print(f"Backing up to {self.user_backupd}")

    def setup(self, *args: str) -> None:
        self.google_takeout.setup()

    def setup_required(self) -> bool:
        return self.google_takeout.setup_required()

    def _backup(self, subcommand: str, *args: str) -> None:
        self.google_takeout.sync_and_extract_exports(subcommand)
        self._backup_takeout_files(subcommand, *args)

    @abstractmethod
    def _backup_takeout_files(self, subcommand: str, *args: str) -> None:
        raise NotImplementedError()
