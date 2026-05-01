from pathlib import Path

import pytest

from app.services.ingestion import (
    InvalidUploadFilenameError,
    content_sha256,
    decode_upload_bytes,
    derive_title,
    upload_file_path,
    validate_txt_filename,
    write_upload_bytes,
)


def test_derive_title_uses_first_short_non_empty_line() -> None:
    body = "\n  First title  \nSecond line"

    assert derive_title("fallback.txt", body) == "First title"


def test_derive_title_falls_back_to_filename_stem_for_long_first_line() -> None:
    body = f"{'x' * 200}\nSecond line"

    assert derive_title("wire-report.txt", body) == "wire-report"


def test_derive_title_falls_back_to_filename_stem_for_blank_body() -> None:
    assert derive_title("empty.txt", "\n  \n") == "empty"


def test_validate_txt_filename_accepts_txt_extension() -> None:
    assert validate_txt_filename("article.TXT") == "article.TXT"


@pytest.mark.parametrize("filename", ["article.md", "article.txt.bak", "article"])
def test_validate_txt_filename_rejects_non_txt(filename: str) -> None:
    with pytest.raises(InvalidUploadFilenameError, match=".txt extension"):
        validate_txt_filename(filename)


def test_content_sha256_is_deterministic_for_stored_body_text() -> None:
    body = "Line one\nLine two"

    assert content_sha256(body) == content_sha256(body)
    assert (
        content_sha256(body)
        == "6991ce0a6fcde71f7e4c492b1746e1f04727fe3b124691803aab99fccdb4d8c6"
    )


def test_decode_upload_bytes_accepts_utf8() -> None:
    assert decode_upload_bytes("Café".encode()) == "Café"


def test_decode_upload_bytes_raises_for_invalid_utf8() -> None:
    with pytest.raises(UnicodeDecodeError):
        decode_upload_bytes(b"\xff")


def test_upload_file_path_uses_corpus_and_article_ids(tmp_path: Path) -> None:
    assert upload_file_path(tmp_path, "corpus-id", "article-id") == (
        tmp_path / "corpus-id" / "article-id.txt"
    )


def test_write_upload_bytes_writes_under_corpus_article_path(tmp_path: Path) -> None:
    path = write_upload_bytes(tmp_path, "corpus-id", "article-id", b"raw bytes")

    assert path == tmp_path / "corpus-id" / "article-id.txt"
    assert path.read_bytes() == b"raw bytes"
