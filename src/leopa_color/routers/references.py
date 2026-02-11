"""Reference image management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from leopa_color.config import Settings, get_settings
from leopa_color.models import ReferenceImage, ReferenceImageList
from leopa_color.services.storage_service import StorageService

router = APIRouter(prefix="/api/references", tags=["references"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    """Get storage service instance."""
    return StorageService(settings=settings)


@router.get("", response_model=ReferenceImageList)
async def list_references(
    storage: StorageService = Depends(get_storage_service),
) -> ReferenceImageList:
    """List all reference images."""
    refs = await storage.get_reference_images()
    return ReferenceImageList(references=refs)


@router.post("", response_model=ReferenceImage, status_code=status.HTTP_201_CREATED)
async def upload_reference(
    file: UploadFile,
    storage: StorageService = Depends(get_storage_service),
) -> ReferenceImage:
    """Upload a new reference color image."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB",
        )

    ref = await storage.save_reference_image(file.filename or "image.jpg", content)
    return ref


@router.get("/{ref_id}", response_model=ReferenceImage)
async def get_reference(
    ref_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> ReferenceImage:
    """Get a specific reference image."""
    ref = await storage.get_reference_image(ref_id)
    if ref is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found",
        )
    return ref


@router.delete("/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    ref_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> None:
    """Delete a reference image."""
    deleted = await storage.delete_reference_image(ref_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference image not found",
        )
