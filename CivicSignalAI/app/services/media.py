from __future__ import annotations

import io
import os
import warnings
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import PROJECT_ROOT

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_COUNT = 4
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_FORMATS = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def storage_directory() -> Path:
    configured = os.getenv("CIVICSIGNAL_UPLOAD_DIR")
    directory = Path(configured).expanduser() if configured else PROJECT_ROOT / "data" / "private-uploads"
    return directory.resolve()


async def validate_and_store_upload(upload: UploadFile) -> dict[str, str]:
    raw = await upload.read(MAX_IMAGE_BYTES + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="Choose a non-empty image file.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Each image must be 5 MB or smaller.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                image_format = original.format
                original.verify()
            with Image.open(io.BytesIO(raw)) as original:
                if original.width * original.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(status_code=413, detail="Image dimensions are too large.")
                if getattr(original, "n_frames", 1) > 1:
                    raise HTTPException(status_code=400, detail="Animated images are not supported.")
                image = original.convert("RGBA" if "A" in original.getbands() else "RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(status_code=400, detail="Upload a valid JPG, PNG, or WebP image.") from None

    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Only JPG, PNG, and WebP images are supported.")

    extension, content_type = ALLOWED_FORMATS[image_format]
    output = io.BytesIO()
    image.save(output, format=image_format, optimize=True)
    stored = output.getvalue()
    if len(stored) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Processed image is larger than the 5 MB limit.")
    image_id = uuid4().hex
    directory = storage_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{image_id}{extension}"
    with path.open("xb") as destination:
        destination.write(stored)

    return {
        "id": image_id,
        "path": str(path),
        "content_type": content_type,
        "size": str(len(stored)),
        "filename": f"evidence{extension}",
    }


def resolve_stored_path(path: str) -> Path:
    root = storage_directory()
    candidate = Path(path).resolve()
    if candidate.parent != root or not candidate.is_file():
        raise FileNotFoundError("Evidence file is unavailable.")
    return candidate
