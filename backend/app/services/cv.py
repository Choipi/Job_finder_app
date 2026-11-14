"""CV handling: store the uploaded PDF and extract its text.

The extracted text is what the LLM will actually read. It is stored in the
database and stays editable, because PDF extraction is never perfect.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

MAX_PAGES = 12


class CvError(Exception):
    """A user-facing problem with the uploaded file."""


@dataclass(frozen=True)
class StoredCv:
    path: Path
    original_name: str
    text: str


def store_cv(file: FileStorage, upload_dir: Path) -> StoredCv:
    original_name = secure_filename(file.filename or "")
    if not original_name or not original_name.lower().endswith(".pdf"):
        raise CvError("Le fichier doit être un PDF.")

    stream = file.stream
    stream.seek(0)
    if stream.read(5) != b"%PDF-":
        raise CvError("Ce fichier n’est pas un PDF valide.")
    stream.seek(0)

    target_dir = upload_dir / "cv"
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"{uuid.uuid4().hex}.pdf"
    file.save(destination)

    try:
        text = extract_pdf_text(destination)
    except Exception as error:  # noqa: BLE001 - any parser failure is a CvError
        destination.unlink(missing_ok=True)
        raise CvError("Impossible de lire ce PDF.") from error

    if not text:
        destination.unlink(missing_ok=True)
        raise CvError(
            "Aucun texte n’a pu être extrait. Si le PDF est un scan, colle le texte manuellement."
        )

    return StoredCv(path=destination, original_name=original_name, text=text)


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []

    for page in reader.pages[:MAX_PAGES]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - skip a broken page, keep the rest
            continue

    return _normalize("\n".join(parts))


def _normalize(text: str) -> str:
    """Collapse runs of spaces while keeping paragraph boundaries."""
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line).strip()
