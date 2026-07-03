"""Almacenamiento de adjuntos en filesystem (Decisión 5 de research.md).

Ruta: uploads/tickets/{ticket_id}/{uuid}-{filename}. El directorio uploads/ vive en la
raíz del repo (montado como volumen en Docker: /repo/uploads).
"""
import os
import re
import uuid
from pathlib import Path

MAX_ATTACHMENT_BYTES = int(os.environ.get("MAX_ATTACHMENT_BYTES", 10 * 1024 * 1024))  # 10 MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".log", ".zip", ".json", ".xml", ".msg",
}

_UPLOADS_ROOT = Path(os.environ.get("UPLOADS_DIR", "uploads"))


class AttachmentError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "archivo")
    return re.sub(r"[^\w.\-]", "_", name)[:120]


def validate(filename: str, size_bytes: int) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AttachmentError(f"Tipo de archivo no permitido: {ext or '(sin extensión)'}")
    if size_bytes > MAX_ATTACHMENT_BYTES:
        mb = MAX_ATTACHMENT_BYTES // (1024 * 1024)
        raise AttachmentError(f"El archivo supera el tamaño máximo permitido ({mb} MB)")


def save(ticket_id: uuid.UUID, filename: str, data: bytes) -> str:
    """Guarda el archivo y devuelve la ruta relativa de almacenamiento."""
    validate(filename, len(data))
    safe = _safe_filename(filename)
    rel_path = Path("tickets") / str(ticket_id) / f"{uuid.uuid4().hex}-{safe}"
    abs_path = _UPLOADS_ROOT / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)
    return str(rel_path).replace("\\", "/")


def open_path(storage_path: str) -> Path:
    """Resuelve la ruta absoluta de un adjunto, validando que no escape de uploads/."""
    abs_path = (_UPLOADS_ROOT / storage_path).resolve()
    root = _UPLOADS_ROOT.resolve()
    if not str(abs_path).startswith(str(root)):
        raise AttachmentError("Ruta de adjunto inválida")
    if not abs_path.is_file():
        raise AttachmentError("Adjunto no encontrado en el almacenamiento")
    return abs_path
