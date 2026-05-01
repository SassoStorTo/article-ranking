from __future__ import annotations

from hashlib import sha256
from pathlib import Path

MAX_TITLE_CHARS = 200


class InvalidUploadFilenameError(ValueError):
    """Raised when an uploaded filename is not accepted."""


def validate_txt_filename(filename: str) -> str:
    if not filename.lower().endswith(".txt"):
        raise InvalidUploadFilenameError("uploaded files must use .txt extension")
    return filename


def decode_upload_bytes(data: bytes) -> str:
    return data.decode("utf-8")


def derive_title(filename: str, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < MAX_TITLE_CHARS:
            return stripped
        return Path(filename).stem
    return Path(filename).stem


def content_sha256(body: str) -> str:
    return sha256(body.encode("utf-8")).hexdigest()


def upload_file_path(uploads_dir: str | Path, corpus_id: str, article_id: str) -> Path:
    return Path(uploads_dir) / corpus_id / f"{article_id}.txt"


def write_upload_bytes(
    uploads_dir: str | Path,
    corpus_id: str,
    article_id: str,
    data: bytes,
) -> Path:
    path = upload_file_path(uploads_dir, corpus_id, article_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path
