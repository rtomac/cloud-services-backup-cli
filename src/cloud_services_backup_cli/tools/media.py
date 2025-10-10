import json
import subprocess
from subprocess import CompletedProcess
from pathlib import Path
import re
from datetime import datetime
import dateutil

from PIL import Image
from pillow_heif import register_heif_opener
register_heif_opener()
import piexif

from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

from ..lib import *
from . import shell


JPEG_EXTS = [ ".jpg", ".jpeg" ]
TIFF_EXTS = [ ".tif", ".tiff" ]
HEIF_EXTS = [ ".heic", ".heif", ".hif" ]
IMAGE_EXTS = JPEG_EXTS + TIFF_EXTS + HEIF_EXTS
VIDEO_EXTS = [ ".mp4", ".mov", ".m4v", ".mkv" ]

EXIF_CREATE_DATE_TAGS = ["DateTimeOriginal", "CreateDate", "DateTimeDigitized", "DateTime"]
EXIF_CREATE_DATE_TAGS_PLUS = EXIF_CREATE_DATE_TAGS + ["DateCreated", "TrackCreateDate", "MediaCreateDate", "CreationDate"]


def exiftool(*args: str) -> CompletedProcess:
    return __exiftool_run(args, check=True)

def exiftool_pipe(*args: str) -> CompletedProcess:
    result = __exiftool_run(args, check=True, capture_output=True, text=True)
    return result.stdout

def __exiftool_run(args: list[str], **kwargs) -> CompletedProcess:
    cmd = ["exiftool", *shell.stringify_args(args)]
    log_command(cmd)
    return subprocess.run(cmd, **kwargs)


class MediaFileInfo():
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.file_ext = self.file_path.suffix.lower()

    def get_create_timestamp(self) -> datetime | None:
        # If image, parse from exif tags
        if self.file_ext in IMAGE_EXTS:
            value = self.__read_exif_tag(*EXIF_CREATE_DATE_TAGS)
            if value:
                return dateutil.parser.parse(value)

        # If video, parse from video container metadata
        if self.file_ext in VIDEO_EXTS:
            value = self.__read_video_metadata_field("creation_date", "date")
            if value:
                if isinstance(value, datetime):
                    return value
                return dateutil.parser.parse(str(value))

        # If media has metadata json file, see if we can read
        # a timestamp from there
        value = self.__read_timestamp_from_json_metadata("photoTakenTime", "creationTime")
        if value:
            return value

        # Try parsing timestamp from file name
        value = self.__read_timestamp_from_file_name()
        if value:
            return value

        # Fallback to shelling out to exiftool for everything
        # else, super reliable but slower
        value = self.__read_exif_tag_w_exiftool(*EXIF_CREATE_DATE_TAGS_PLUS)
        if value:
            return dateutil.parser.parse(value)

        raise ValueError(f"No create timestamp found for file {self.file_path}")


    # Parse exif tags from images using Pillow
    def __read_exif_tag(self, *tag_names) -> str | None:
        with Image.open(self.file_path) as img:
            exif_bytes = img.info.get("exif", b"")
            if not exif_bytes:
                return None
            exif_dict = piexif.load(exif_bytes)
            for tag_name in tag_names:
                for ifd_name in ["0th", "Exif", "1st", "GPS", "Interop"]:
                    ifd = exif_dict.get(ifd_name, {})
                    tag_id = next((k for k, v in piexif.TAGS[ifd_name].items() if v["name"] == tag_name), None)
                    if tag_id and tag_id in ifd:
                        value = ifd[tag_id]
                        if isinstance(value, bytes):
                            value = value.decode()
                        return str(value)
        return None

    # Parse video metadata fields using Hachoir
    def __read_video_metadata_field(self, *field_names) -> str | int | datetime | None:
        parser = createParser(str(self.file_path))
        if parser:
            metadata = extractMetadata(parser)
            if metadata:
                for field in field_names:
                    dt = metadata.get(field)
                    if dt:
                        return dt
        return None

    # Parse timestamp from adjacent json metadata files
    def __read_timestamp_from_json_metadata(self, *tag_names) -> datetime | None:
        for ext in [".json", ".meta.json"]:
            json_file = self.file_path.with_suffix(self.file_path.suffix + ext)
            if not json_file.exists():
                continue
            with open(json_file, "r") as f:
                data = json.load(f)
                for tag in tag_names:
                    if tag in data:
                        value = data[tag]["timestamp"]
                        return datetime.fromtimestamp(int(value))
        return None

    # Parse timestamp from file name using common patterns
    # from digital cameras and phones
    def __read_timestamp_from_file_name(self) -> datetime | None:
        name_parts = re.split(r"[-_~]", self.file_path.stem)
        for i in range(len(name_parts) - 1):
            name_part = name_parts[i]
            if len(name_part) == 8 and name_part[:8].isdigit():
                dt_str = f"{name_part[:4]}-{name_part[4:6]}-{name_part[6:8]}"
                next_name_part = name_parts[i + 1]
                if len(next_name_part) in [6, 9] and next_name_part.isdigit():
                    dt_str += f" {next_name_part[:2]}:{next_name_part[2:4]}:{next_name_part[4:6]}"
                try:
                    return dateutil.parser.parse(dt_str)
                except Exception:
                    pass
        return None
    
    def __read_exif_tag_w_exiftool(self, *tag_names) -> str | None:
        tag_flags = [f"-{tag}" for tag in tag_names]
        output = exiftool_pipe(*tag_flags, "-json", "-fast2", "--b", str(self.file_path))
        tags = json.loads(output)[0]
        for field in tag_names:
            if field in tags:
                return str(tags[field])
