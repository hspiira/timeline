"""Unit tests for document operations helpers (e.g. filename sanitization)."""

import pytest

from app.application.use_cases.documents.document_operations import _sanitize_filename


class TestSanitizeFilename:
    """Tests for _sanitize_filename."""

    def test_basename_only(self) -> None:
        assert _sanitize_filename("report.pdf") == "report.pdf"

    def test_path_stripped(self) -> None:
        assert _sanitize_filename("/foo/bar/report.pdf") == "report.pdf"

    def test_null_removed(self) -> None:
        assert _sanitize_filename("a\x00b.pdf") == "ab.pdf"

    def test_empty_after_sanitize_raises(self) -> None:
        with pytest.raises(ValueError, match="empty or invalid"):
            _sanitize_filename("")

    def test_reserved_name_nul_raises(self) -> None:
        with pytest.raises(ValueError, match="Reserved filename"):
            _sanitize_filename("nul")

    def test_reserved_name_con_raises(self) -> None:
        with pytest.raises(ValueError, match="Reserved filename"):
            _sanitize_filename("CON")

    def test_reserved_name_com1_raises(self) -> None:
        with pytest.raises(ValueError, match="Reserved filename"):
            _sanitize_filename("com1")

    def test_reserved_name_lpt9_raises(self) -> None:
        with pytest.raises(ValueError, match="Reserved filename"):
            _sanitize_filename("LPT9")

    def test_normal_name_with_extension_allowed(self) -> None:
        assert _sanitize_filename("myfile.txt") == "myfile.txt"
