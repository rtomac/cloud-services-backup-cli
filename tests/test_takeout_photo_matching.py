"""
Tests for the two-tier Google Takeout sidecar<->media matcher.

Runnable with pytest, or standalone: `python3 tests/test_takeout_photo_matching.py`
"""
import importlib.util
import os
import sys

# Load the matcher module directly by path so we don't import the whole
# cloud_services_backup_cli.lib package (its __init__ pulls in modules that
# require Python 3.12+ syntax, whereas this pure module runs on any 3.9+).
_MOD_PATH = os.path.join(
    os.path.dirname(__file__), "..", "src", "cloud_services_backup_cli",
    "lib", "takeout_photo_matching.py",
)
_spec = importlib.util.spec_from_file_location("takeout_photo_matching", _MOD_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

plan_filename_matches = _mod.plan_filename_matches
resolve_by_title = _mod.resolve_by_title
DEFER = _mod.DEFER
_match_one_filename = _mod._match_one_filename


def _match(json_name, media_names):
    """Run a single name through Pass 1 (mirrors plan_filename_matches setup)."""
    from pathlib import Path
    media_by_name = {m.lower(): m for m in media_names}
    media_by_stem = {}
    for m in media_names:
        media_by_stem.setdefault(Path(m).stem.lower(), []).append(m)
    return _match_one_filename(json_name, media_by_name, media_by_stem)


def _full_pipeline(json_names, media_names, titles):
    """Run both passes the way __sync_metadata does and return json->media."""
    resolved, deferred = plan_filename_matches(json_names, media_names)
    if deferred:
        claimed = set(resolved.values())
        unmatched = [m for m in media_names if m not in claimed]
        resolved.update(resolve_by_title(deferred, {j: titles.get(j) for j in deferred}, unmatched))
    return resolved


# --- Pass 1: confident filename matches (no reads) --------------------------

def test_marker_intact():
    assert _match("photo.jpg.supplemental-metadata.json", ["photo.jpg"]) == "photo.jpg"

def test_marker_truncated():
    assert _match("photo.jpg.supplemental-metad.json", ["photo.jpg"]) == "photo.jpg"
    assert _match("photo.jpg.s.json", ["photo.jpg"]) == "photo.jpg"

def test_marker_numbered():
    assert _match("photo.jpg.supplemental-metadata(1).json", ["photo.jpg", "photo(1).jpg"]) == "photo(1).jpg"

def test_marker_b_extension_omitted():
    assert _match("photo.supplemental-metadata.json", ["photo.jpg"]) == "photo.jpg"

def test_passthrough_plain_sidecar():
    assert _match("IMG_1234.HEIC.json", ["IMG_1234.HEIC"]) == "IMG_1234.HEIC"

def test_fully_truncated_defers_then_resolves_by_title():
    # Marker gone: Attachment_...c42d.JPG.supplemental-metadata.json -> Attachment_...c42.json
    media = ["Attachment_040f5ef0-3e76-40cb-ae9c-5a402dd6c42d.JPG"]
    jsons = ["Attachment_040f5ef0-3e76-40cb-ae9c-5a402dd6c42.json"]
    assert _match(jsons[0], media) is DEFER  # no marker -> defer, not resolved in Pass 1
    titles = {jsons[0]: media[0]}            # title carries the full original name
    assert _full_pipeline(jsons, media, titles) == {jsons[0]: media[0]}

def test_album_metadata_dropped():
    # metadata.json has no marker -> defers, but its title matches no media -> dropped
    assert _match("metadata.json", ["IMG_1.jpg", "IMG_2.jpg"]) is DEFER
    assert _full_pipeline(["metadata.json"], ["IMG_1.jpg", "IMG_2.jpg"],
                          {"metadata.json": "Photos from 2026"}) == {}

def test_ambiguous_defers():
    # base sidecar prefixes several siblings -> can't pick one on filename alone
    media = ["k-e.jpg", "k-e(1).jpg", "k-e.mp4"]
    assert _match("k-.json", media) is DEFER

def test_marker_b_ambiguous_extension_defers():
    # stem shared across jpg + mp4, extension omitted from sidecar name
    assert _match("photo.supplemental-metadata.json", ["photo.jpg", "photo.mp4"]) is DEFER


# --- Pass 2: title-based resolution of the real collision cluster ------------

K = "oc63_23_16_31_55_45-cm0-sid10-cstrt_bbbf-kqpq"
STEM = K + "-ewwx-4765_ut0on31_ut_"

CLUSTER_MEDIA = [f"{K}-e.jpg", f"{K}-e(1).jpg", f"{K}-e(2).jpg", f"{K}-e(3).jpg", f"{K}-e.mp4"]
CLUSTER_JSONS = [f"{K}-.json", f"{K}-(1).json", f"{K}-(2).json", f"{K}-(3).json", f"{K}-(4).json"]
CLUSTER_TITLES = {
    f"{K}-.json":    f"{STEM}2732s.jpg",
    f"{K}-(1).json": f"{STEM}5j96a.jpg",
    f"{K}-(2).json": f"{STEM}11j2mmjelly.mp4",   # the Motion Photo video
    f"{K}-(3).json": f"{STEM}0euf1.jpg",
    f"{K}-(4).json": f"{STEM}0fdjtd.jpg",
}

def test_cluster_all_defer_in_pass1():
    _, deferred = plan_filename_matches(CLUSTER_JSONS, CLUSTER_MEDIA)
    assert set(deferred) == set(CLUSTER_JSONS)

def test_cluster_resolves_correctly_via_title():
    result = _full_pipeline(CLUSTER_JSONS, CLUSTER_MEDIA, CLUSTER_TITLES)
    assert result == {
        f"{K}-.json":    f"{K}-e.jpg",
        f"{K}-(1).json": f"{K}-e(1).jpg",
        f"{K}-(2).json": f"{K}-e.mp4",     # video metadata lands on the .mp4, not a .jpg
        f"{K}-(3).json": f"{K}-e(2).jpg",
        f"{K}-(4).json": f"{K}-e(3).jpg",
    }

def test_video_metadata_never_lands_on_jpg():
    result = _full_pipeline(CLUSTER_JSONS, CLUSTER_MEDIA, CLUSTER_TITLES)
    mp4_json = f"{K}-(2).json"
    assert result[mp4_json].endswith(".mp4")


# --- Pass 2: one sidecar, two media (photo + variant share the prefix) -------

def test_single_json_two_media_assigns_one():
    media = ["u_a.jpg", "u_b.jpg"]  # both truncate to same prefix
    jsons = ["u_.json"]
    titles = {"u_.json": "u_averylongoriginalname.jpg"}
    result = _full_pipeline(jsons, media, titles)
    # exactly one media claimed; deterministic (lowest dup / sorted first)
    assert len(result) == 1
    assert result["u_.json"] in media


# --- extra edge cases -------------------------------------------------------

def test_marker_match_is_case_insensitive():
    # sidecar name lower-case, media file upper-case extension -> still matches,
    # returning the media file's ORIGINAL casing
    assert _match("img.jpg.supplemental-metadata.json", ["IMG.JPG"]) == "IMG.JPG"

def test_marker_present_but_media_missing_defers():
    # marker recovers a media name that isn't on disk -> defer (don't drop),
    # so the title pass gets a chance rather than silently losing it
    assert _match("photo.jpg.supplemental-metadata.json", ["other.jpg"]) is DEFER

def test_pass2_unreadable_title_is_skipped():
    # one deferred sidecar has no readable title -> it's skipped, the other
    # still resolves, and nothing raises
    media = ["a-e.jpg", "a-e(1).jpg"]
    jsons = ["a-.json", "a-(1).json"]
    titles = {"a-.json": "a-efirst.jpg", "a-(1).json": None}
    result = _full_pipeline(jsons, media, titles)
    assert result == {"a-.json": "a-e.jpg"}
    assert "a-(1).json" not in result

def test_pass2_dup_ordering_is_numeric_not_lexical():
    # jpg sidecars carry dup numbers 0, 2, 10 (a gap left by the .mp4 at 5),
    # media carry 0, 1, 2. Pairing is by position after a NUMERIC sort, so
    # (10) -> the 3rd media (index 2). A lexical sort would order (10) before
    # (2) and mis-pair it to the 2nd media.
    media = ["a-e.jpg", "a-e(1).jpg", "a-e(2).jpg", "a-e.mp4"]
    jsons = ["a-.json", "a-(2).json", "a-(10).json", "a-(5).json"]
    titles = {
        "a-.json":    "a-eAAA.jpg",
        "a-(2).json":  "a-eBBB.jpg",
        "a-(10).json": "a-eCCC.jpg",
        "a-(5).json":  "a-eMMM.mp4",
    }
    result = _full_pipeline(jsons, media, titles)
    assert result == {
        "a-.json":    "a-e.jpg",
        "a-(2).json":  "a-e(1).jpg",
        "a-(10).json": "a-e(2).jpg",   # numeric ordering; lexical would give a-e(1).jpg
        "a-(5).json":  "a-e.mp4",
    }

def test_pass2_extra_sidecar_is_dropped():
    # more sidecars than media in the cluster -> the leftover sidecar is dropped
    media = ["a-e.jpg"]
    jsons = ["a-.json", "a-(1).json"]
    titles = {"a-.json": "a-efirst.jpg", "a-(1).json": "a-esecond.jpg"}
    result = _full_pipeline(jsons, media, titles)
    assert result == {"a-.json": "a-e.jpg"}


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(TESTS) - failed}/{len(TESTS)} passed")
    sys.exit(1 if failed else 0)
