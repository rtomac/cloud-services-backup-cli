import sys
from pathlib import Path
from datetime import datetime, timedelta

from PIL import Image
import piexif
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import exifread


IGNORE_EXT = ["txt", "json"]


def main(album_dir: Path, manifest_file: Path):
    existing_lines = {}
    manifest_lines = []

    # Read existing manifest
    if manifest_file.exists():
        with open(manifest_file, "r") as file:
            for line in file:
                filename = line.strip().split("/", 2)[-1]
                existing_lines[filename.lower()] = line.strip()
        print(f"{len(existing_lines)} existing line(s) in manifest {manifest_file}")

    # Read files in album
    files = sorted([f for f in Path(album_dir).iterdir() if f.is_file() and f.suffix.lower().lstrip('.') not in IGNORE_EXT])
    if not files and len(existing_lines) == 0:
        if manifest_file.exists():
            print(f"No files, removing manifest {manifest_file}")
            manifest_file.unlink()
        return

    # Add new files
    for file in files:
        existing_line = existing_lines.get(file.name.lower())
        if existing_line:
            manifest_lines.append(existing_line)
            continue
        year_month = get_exif_date(file)
        manifest_lines.append(f"{year_month}/{file.name}")
        print(f"Added {file.name} with date {year_month} to manifest")

    # Write updated manifest file
    with open(manifest_file, "w") as file:
        for line in manifest_lines:
            file.write(line + "\n")
    
    print(f"Wrote manifest with {len(manifest_lines)} line(s)")

def get_exif_date(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    # JPEG using piexif
    if suffix in [".jpg", ".jpeg"]:
        try:
            exif_dict = piexif.load(str(file_path))
            dt_bytes = (
                exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
                    or exif_dict["Exif"].get(piexif.ExifIFD.CreateDate)
            )
            if dt_bytes:
                dt_str = dt_bytes.decode() if isinstance(dt_bytes, bytes) else dt_bytes
                return dt_str[:4] + "/" + dt_str[5:7]
        except Exception:
            pass

    # PNG / GIF / HEIC / TIFF / BMP / WebP
    # using Pillow
    if suffix in [".png", ".gif", ".heic", ".tiff", ".bmp", ".webp"]:
        try:
            img = Image.open(file_path)
            info = img.info
            dt = info.get("date") or info.get("DateTime")
            if dt:
                return dt[:4] + "/" + dt[5:7]
        except Exception:
            pass

    # Video formats using hachoir
    if suffix in [".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".wmv"]:
        try:
            parser = createParser(str(file_path))
            if parser:
                metadata = extractMetadata(parser)
                if metadata and metadata.has("creation_date"):
                    dt = metadata.get("creation_date").value
                    return dt.strftime("%Y/%m")
        except Exception:
            pass

    # Fallback using exifread
    try:
        with open(file_path, "rb") as file:
            tags = exifread.process_file(file, stop_tag="EXIF DateTimeOriginal", details=False)
            dt = (
                tags.get("EXIF DateTimeOriginal")
                    or tags.get("EXIF DateTimeDigitized")
                    or tags.get("Image DateTime")
            )
            if dt:
                dt_str = str(dt)
                return dt_str[:4] + "/" + dt_str[5:7]
    except Exception:
        pass

    raise RuntimeError(f"No exif metadata date available for {file_path}")


if __name__ == "__main__":
    album_dir = Path(sys.argv[1].rstrip("/"))
    manifest_file = album_dir / "manifest.txt"
    main(album_dir, manifest_file)
