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
from __future__ import annotations
import re
from pathlib import Path

SUPPL_META_SUFFIX = ".supplemental-metadata"
_DUP_RE = re.compile(r"\(\d+\)$")

# Sentinel returned by the Pass 1 matcher when filenames are ambiguous and the
# sidecar must be resolved by its "title" field in Pass 2.
DEFER = object()


def _split_dup_number(text: str) -> tuple[str, str]:
    """Split a trailing Google duplicate marker off a name.

    "photo(1)" -> ("photo", "(1)");  "photo" -> ("photo", "")
    Also applies to a suffix like ".supplemental-metadata(1)".
    """
    m = _DUP_RE.search(text)
    return (text[:m.start()], m.group(0)) if m else (text, "")


def _dup_order(dup: str) -> int:
    """Sort key for a duplicate marker; the numberless original sorts first."""
    return int(dup[1:-1]) if dup else 0


def _match_one_filename(json_name: str, media_by_name: dict, media_by_stem: dict):
    """Pass 1 for a single sidecar.

    Returns the matching media filename, the DEFER sentinel (needs a title read),
    or None (drop it — an orphan sidecar with no media file).
    """
    p = Path(json_name)
    suffixes = p.suffixes
    if len(suffixes) >= 2:
        second_suffix, number = _split_dup_number(suffixes[-2].lower())
        media_base = p.with_suffix("").with_suffix("")
        # A (possibly middle-truncated) ".supplemental-metadata" suffix still
        # startswith-matches (".supplemental-metad", ".s", ...). When it is
        # present, the media filename is fully recoverable from the sidecar name.
        if len(second_suffix) > 1 and SUPPL_META_SUFFIX.startswith(second_suffix):
            if len(suffixes) >= 3:
                # media extension present: "photo.jpg.supplemental-metadata.json"
                cand = (media_base.stem + number + media_base.suffix).lower()
                return media_by_name.get(cand, DEFER)
            # media extension omitted: "photo.supplemental-metadata.json"
            cands = media_by_stem.get((media_base.name + number).lower(), [])
            if len(cands) == 1:
                return cands[0]
            # >1 means the stem is shared across extensions (e.g. jpg + mp4);
            # the sidecar name can't say which, so defer. 0 means orphan.
            return DEFER if cands else None

    # Plain sidecar: passes through when it names a media file exactly.
    base = p.with_suffix("").name
    if base.lower() in media_by_name:
        return media_by_name[base.lower()]

    # The ".supplemental-metadata" marker is gone (heavy truncation) and this
    # isn't a plain sidecar, so the on-disk name is too mangled to trust. Defer
    # to the title pass, which reads the authoritative original filename.
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
    # Group unmatched media by (core stem without dup number, extension).
    media_groups: dict = {}
    for m in unmatched_media_names:
        mp = Path(m)
        core, dup = _split_dup_number(mp.stem)
        media_groups.setdefault((core.lower(), mp.suffix.lower()), []).append((_dup_order(dup), m))

    resolved: dict = {}
    used_jsons: set = set()
    # Deterministic order over clusters; within a cluster, by duplicate number.
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
