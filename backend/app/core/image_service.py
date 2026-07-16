"""
Image Service for CarDetailing AI.

Handles file upload, validation, thumbnail generation,
and file storage (local / S3).
"""

import os
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.core.config import settings

# Allowed mime-types
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
THUMBNAIL_SIZE = (200, 200)


def _ext_to_mime(ext: str) -> str:
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(ext.lower(), "application/octet-stream")


def validate_image(file_bytes: bytes, filename: str) -> str:
    """Validate file size, extension, and image integrity.

    Returns the validated MIME type string.
    Raises ValueError if invalid.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Недопустимый формат: {ext}. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(
            f"Файл слишком большой: {len(file_bytes)} байт. "
            f"Максимум: {MAX_FILE_SIZE} байт (10 MB)"
        )

    # Verify it's a valid image
    try:
        img = Image.open(BytesIO(file_bytes))
        img.verify()
    except Exception as e:
        raise ValueError(f"Файл не является изображением: {e}")

    return _ext_to_mime(ext)


def create_thumbnail(file_bytes: bytes, size: tuple[int, int] = THUMBNAIL_SIZE) -> bytes:
    """Create a thumbnail from image bytes.

    Returns the thumbnail as JPEG bytes.
    """
    img = Image.open(BytesIO(file_bytes))
    img = img.convert("RGB")
    img.thumbnail(size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def generate_filename(original_name: str) -> str:
    """Generate a unique filename preserving the extension."""
    ext = Path(original_name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def save_file_local(
    file_bytes: bytes,
    subdir: str,
    filename: str,
) -> tuple[str, str | None]:
    """Save file to local storage.

    Returns (url_path, thumbnail_url_path).
    """
    upload_root = Path(settings.STORAGE_PATH or "./uploads")
    target_dir = upload_root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Save original
    file_path = target_dir / filename
    file_path.write_bytes(file_bytes)
    url_path = f"/uploads/{subdir}/{filename}"

    # Save thumbnail
    thumb_bytes = create_thumbnail(file_bytes)
    thumb_name = f"thumb_{filename}"
    thumb_path = target_dir / thumb_name
    thumb_path.write_bytes(thumb_bytes)
    thumb_url = f"/uploads/{subdir}/{thumb_name}"

    return url_path, thumb_url


def delete_file_local(url_path: str):
    """Delete a file from local storage."""
    upload_root = Path(settings.STORAGE_PATH or "./uploads")
    file_path = upload_root / url_path.lstrip("/uploads/")
    if file_path.exists():
        file_path.unlink()
    # Also delete thumbnail
    thumb_path = file_path.parent / f"thumb_{file_path.name}"
    if thumb_path.exists():
        thumb_path.unlink()
