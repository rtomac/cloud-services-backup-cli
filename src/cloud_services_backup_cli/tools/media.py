from __future__ import annotations

import json
import subprocess
from subprocess import CompletedProcess
from pathlib import Path
import re
from datetime import datetime
import dateutil
import logging

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
        logging.debug(f"Getting create timestamp for media file: {self.file_path}")

        # If image, parse from exif tags
        if self.file_ext in IMAGE_EXTS:
            value = self.__read_exif_tag(*EXIF_CREATE_DATE_TAGS)
            if value:
                logging.debug(f"Value from image exif tags: {value}")
                return self.__parse_exif_date_str(value)

        # If video, parse from video container metadata
        if self.file_ext in VIDEO_EXTS:
            value = self.__read_video_metadata_field("creation_date", "date")
            if value:
                logging.debug(f"Value from video metadata: {value}")
                if not isinstance(value, datetime):
                    value = dateutil.parser.parse(str(value))
                if value.year < 1970:
                    value = value.replace(year=value.year + 66)
                    logging.debug(f"Adjusted value after mac epoch fix: {value}")
                return value

        # If media has metadata json file, see if we can read
        # a timestamp from there
        value = self.__read_timestamp_from_json_metadata("photoTakenTime", "creationTime")
        if value:
            logging.debug(f"Value from json metadata: {value}")
            return value

        # Try parsing timestamp from file name
        value = self.__read_timestamp_from_file_name()
        if value:
            logging.debug(f"Value from file name: {value}")
            return value

        # Fallback to shelling out to exiftool for everything
        # else, super reliable but slower
        value = self.__read_exif_tag_w_exiftool(*EXIF_CREATE_DATE_TAGS_PLUS)
        if value:
            logging.debug(f"Value from exiftool: {value}")
            return self.__parse_exif_date_str(value)

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


    def __parse_exif_date_str(self, date_str: str) -> datetime:
        date_str = re.sub(r'^(\d{4}):(\d{2}):(\d{2})(?=\s|T|$)', r'\1-\2-\3', date_str)
        return dateutil.parser.parse(date_str)


# ---------------------------------------------------------------------------
# Google Takeout sidecar-to-media matching
# ---------------------------------------------------------------------------

"""
Associates Google Takeout supplemental-metadata JSON sidecars with their media
files.

Google Takeout names each sidecar "<media>.supplemental-metadata.json", then
truncates the result from the middle outward when it exceeds the filesystem's
filename length limit. Crucially, the *media* filename is independently
truncated too, so both names on disk are lossy derivations of the same long
original — matching one mangled name against the other is unreliable. The
authoritative original filename (with its correct extension) lives in the
sidecar's "title" field.

Reading every sidecar's "title" would mean an I/O hit across thousands of files
per run, so association runs in two tiers:

  Pass 1 - plan_filename_matches(): resolve as many sidecars as possible from
    filenames alone, with no file reads. Accepts only confident, unambiguous
    matches; anything ambiguous is deferred.

  Pass 2 - resolve_by_title(): for the deferred remainder only, use the "title"
    field (read by the caller) to associate by extension + prefix, pairing
    within a truncation-collision cluster in duplicate-number order.

In practice Pass 1 resolves ~99% of sidecars, so Pass 2 reads only a handful of
titles per run.
"""

SUPPL_META_SUFFIX = ".supplemental-metadata"
_DUP_RE = re.compile(r"\(\d+\)$")

# Sentinel returned by the Pass 1 matcher when filenames are ambiguous and the
# sidecar must be resolved by its "title" field in Pass 2.
DEFER = object()


def _split_dup_number(text: str) -> tuple[str, str]:
    m = _DUP_RE.search(text)
    return (text[:m.start()], m.group(0)) if m else (text, "")


def _dup_order(dup: str) -> int:
    return int(dup[1:-1]) if dup else 0


def _match_one_filename(json_name: str, media_by_name: dict, media_by_stem: dict):
    p = Path(json_name)
    suffixes = p.suffixes
    if len(suffixes) >= 2:
        second_suffix, number = _split_dup_number(suffixes[-2].lower())
        media_base = p.with_suffix("").with_suffix("")
        if len(second_suffix) > 1 and SUPPL_META_SUFFIX.startswith(second_suffix):
            if len(suffixes) >= 3:
                cand = (media_base.stem + number + media_base.suffix).lower()
                return media_by_name.get(cand, DEFER)
            cands = media_by_stem.get((media_base.name + number).lower(), [])
            if len(cands) == 1:
                return cands[0]
            return DEFER if cands else None

    base = p.with_suffix("").name
    if base.lower() in media_by_name:
        return media_by_name[base.lower()]

    return DEFER


def plan_filename_matches(json_names, media_names):
    """Pass 1: match sidecars to media using filenames only (no file reads).

    Returns (resolved, deferred):
      resolved:  dict[json_name -> media_name] confidently matched
      deferred:  list[json_name] whose association needs the "title" field
    """
    media_by_name = {m.lower(): m for m in media_names}
    media_by_stem: dict = {}
    for m in media_names:
        media_by_stem.setdefault(Path(m).stem.lower(), []).append(m)

    resolved: dict = {}
    deferred: list = []
    for j in json_names:
        result = _match_one_filename(j, media_by_name, media_by_stem)
        if result is DEFER:
            deferred.append(j)
        elif result is not None:
            resolved[j] = result
    return resolved, deferred


def resolve_by_title(deferred_json_names, titles, unmatched_media_names):
    """Pass 2: associate the deferred sidecars using their "title" field.

    Args:
      deferred_json_names: sidecar filenames deferred by Pass 1
      titles: dict[json_name -> title string] (None/"" if unreadable)
      unmatched_media_names: media files not already claimed in Pass 1

    Within each (core-stem, extension) collision cluster, sidecars and media are
    paired in duplicate-number order, which reconstructs Takeout's own global
    assignment order. Matching on the title's extension keeps a Motion Photo's
    ".mp4" metadata off its paired ".jpg". Returns dict[json_name -> media_name].
    """
    media_groups: dict = {}
    for m in unmatched_media_names:
        mp = Path(m)
        core, dup = _split_dup_number(mp.stem)
        media_groups.setdefault((core.lower(), mp.suffix.lower()), []).append((_dup_order(dup), m))

    resolved: dict = {}
    used_jsons: set = set()
    for (core, ext), media_list in sorted(media_groups.items()):
        matched = []
        for j in deferred_json_names:
            if j in used_jsons:
                continue
            title = titles.get(j)
            if not title:
                continue
            tp = Path(title)
            if tp.suffix.lower() == ext and tp.stem.lower().startswith(core):
                _, jdup = _split_dup_number(Path(j).with_suffix("").name)
                matched.append((_dup_order(jdup), j))
        matched.sort()
        for (_, j), (_, m) in zip(matched, sorted(media_list)):
            resolved[j] = m
            used_jsons.add(j)
    return resolved
