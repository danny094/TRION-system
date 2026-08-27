import importlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ROOT = ROOT / "mcp-servers" / "filesystem"
SERVERS_ROOT = BUNDLE_ROOT.parent


def _module(name: str):
    assert BUNDLE_ROOT.is_dir(), "R6 Filesystem MCP product slice is absent"
    if str(SERVERS_ROOT) not in sys.path:
        sys.path.insert(0, str(SERVERS_ROOT))
    return importlib.import_module(f"filesystem.{name}")


def _tree(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "status.txt").write_text("bereit\n", encoding="utf-8")
    (tmp_path / "docs" / "notes.md").write_text("notes", encoding="utf-8")
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")


def test_list_is_ordered_bounded_and_exact_target_aware(tmp_path):
    _tree(tmp_path)
    listing = _module("listing")

    result = listing.list_entries(tmp_path, max_entries=2, max_depth=2)
    assert [item["relative_path"] for item in result["entries"]] == ["docs", "docs/notes.md"]
    assert result["complete"] is False
    assert result["truncated"] is True

    exact = listing.list_entries(tmp_path, relative_path="docs/status.txt")
    assert exact["exists"] is True
    assert exact["entries"][0]["relative_path"] == "docs/status.txt"
    missing = listing.list_entries(tmp_path, relative_path="missing.txt")
    assert missing == {
        "relative_path": "missing.txt",
        "exists": False,
        "entries": [],
        "complete": True,
        "truncated": False,
    }


def test_search_matches_names_only_and_reports_limits(tmp_path):
    _tree(tmp_path)
    search = _module("search")

    result = search.search_paths(tmp_path, "t", max_results=2, max_depth=3)
    assert [item["relative_path"] for item in result["matches"]] == ["docs/notes.md", "docs/status.txt"]
    assert result["complete"] is False
    assert result["truncated"] is True


def test_search_rejects_non_string_query(tmp_path):
    contracts = _module("contracts")
    search = _module("search")

    with pytest.raises(contracts.FilesystemFailure) as failure:
        search.search_paths(tmp_path, ["status"])
    assert failure.value.code == "MALFORMED_REQUEST"


def test_list_stops_traversal_after_response_boundary(tmp_path, monkeypatch):
    listing = _module("listing")
    for index in range(20):
        (tmp_path / f"file-{index:02}.txt").write_text("x", encoding="utf-8")
    real_open_target = listing.open_target
    calls = 0

    def counted_open_target(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_open_target(*args, **kwargs)

    monkeypatch.setattr(listing, "open_target", counted_open_target)
    result = listing.list_entries(tmp_path, max_entries=2)

    assert result["truncated"] is True
    assert calls <= 4


def test_search_has_a_hard_scan_budget(tmp_path, monkeypatch):
    contracts = _module("contracts")
    listing = _module("listing")
    search = _module("search")
    for index in range(contracts.SEARCH_MAX_RESULTS + 20):
        (tmp_path / f"file-{index:03}.txt").write_text("x", encoding="utf-8")
    real_open_target = listing.open_target
    calls = 0

    def counted_open_target(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_open_target(*args, **kwargs)

    monkeypatch.setattr(listing, "open_target", counted_open_target)
    result = search.search_paths(tmp_path, "absent", max_results=2)

    assert result["matches"] == []
    assert result["complete"] is False
    assert result["truncated"] is False
    assert calls <= contracts.SEARCH_MAX_RESULTS + 2


def test_metadata_is_privacy_minimal_and_read_is_utf8_bounded(tmp_path):
    _tree(tmp_path)
    metadata = _module("metadata")
    reader = _module("reader")

    assert metadata.metadata_for(tmp_path, "docs") == {
        "relative_path": "docs",
        "entry_type": "directory",
        "size_bytes": None,
    }
    assert metadata.metadata_for(tmp_path, "docs/status.txt") == {
        "relative_path": "docs/status.txt",
        "entry_type": "file",
        "size_bytes": 7,
    }
    assert reader.read_text(tmp_path, "docs/status.txt") == {
        "relative_path": "docs/status.txt",
        "text": "bereit\n",
        "size_bytes": 7,
        "read_bytes": 7,
        "complete": True,
        "truncated": False,
    }


def test_read_rejects_large_and_non_utf8_files(tmp_path):
    contracts = _module("contracts")
    reader = _module("reader")
    (tmp_path / "large.txt").write_text("12345", encoding="utf-8")
    (tmp_path / "binary.bin").write_bytes(b"\xff")

    with pytest.raises(contracts.FilesystemFailure) as large:
        reader.read_text(tmp_path, "large.txt", max_bytes=4)
    assert large.value.code == "SIZE_LIMIT"
    with pytest.raises(contracts.FilesystemFailure) as binary:
        reader.read_text(tmp_path, "binary.bin")
    assert binary.value.code == "UNSUPPORTED_ENCODING"


def test_read_collects_short_os_reads_before_claiming_complete(tmp_path, monkeypatch):
    reader = _module("reader")
    (tmp_path / "status.txt").write_text("bereit", encoding="utf-8")
    real_read = reader.os.read
    chunks = [b"be", b"reit", b""]

    monkeypatch.setattr(reader.os, "read", lambda _fd, _size: chunks.pop(0))
    result = reader.read_text(tmp_path, "status.txt")
    monkeypatch.setattr(reader.os, "read", real_read)

    assert result["text"] == "bereit"
    assert result["read_bytes"] == 6
    assert result["complete"] is True
