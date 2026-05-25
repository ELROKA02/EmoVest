from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from config import IMAGE_STORAGE_DIR, MAX_IMAGE_SIZE_MB


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CONTENT_TYPE_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class LocalImageStorage:
    def __init__(self, base_dir: str, max_image_size_mb: int) -> None:
        resolved_base_dir = Path(base_dir)
        if not resolved_base_dir.is_absolute():
            resolved_base_dir = Path(__file__).resolve().parent / resolved_base_dir
        self.base_dir = resolved_base_dir.resolve()
        self.max_bytes = max_image_size_mb * 1024 * 1024
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_operation_image(self, upload_file: UploadFile) -> str:
        if not upload_file.content_type or not upload_file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo adjunto debe ser una imagen válida",
            )

        extension = Path(upload_file.filename or "").suffix.lower()
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            extension = CONTENT_TYPE_EXTENSION_MAP.get(upload_file.content_type)

        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagen no soportado",
            )

        relative_path = Path("operaciones") / f"{uuid4().hex}{extension}"
        absolute_path = self.base_dir / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        total_size = 0
        try:
            with absolute_path.open("wb") as output_file:
                while True:
                    chunk = upload_file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"La imagen no debe superar {MAX_IMAGE_SIZE_MB}MB",
                        )
                    output_file.write(chunk)
        except Exception:
            if absolute_path.exists():
                absolute_path.unlink()
            raise

        return str(relative_path).replace("\\", "/")

    def resolve_image_path(self, relative_path: str) -> Path:
        absolute_path = (self.base_dir / relative_path).resolve()
        if self.base_dir not in absolute_path.parents and absolute_path != self.base_dir:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ruta de imagen inválida")
        return absolute_path

    def delete_image(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        absolute_path = self.resolve_image_path(relative_path)
        if absolute_path.exists():
            absolute_path.unlink()


image_storage = LocalImageStorage(IMAGE_STORAGE_DIR, MAX_IMAGE_SIZE_MB)
