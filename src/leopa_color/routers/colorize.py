"""Colorization endpoints."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from leopa_color.config import Settings, get_settings
from leopa_color.models import (
    ColorizeResponse,
    JobStatus,
    JobStatusResponse,
)
from leopa_color.services.replicate_service import ReplicateService
from leopa_color.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["colorize"])

# Store background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task[None]] = set()

templates = Jinja2Templates(directory="templates")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    """Get storage service instance."""
    return StorageService(settings=settings)


def get_replicate_service(
    settings: Settings = Depends(get_settings),
) -> ReplicateService:
    """Get Replicate service instance."""
    return ReplicateService(settings=settings)


@router.get("/colorize", response_class=HTMLResponse)
async def colorize_page(
    request: Request,
    storage: StorageService = Depends(get_storage_service),
) -> HTMLResponse:
    """Render the colorization UI page."""
    references = await storage.get_reference_images()
    return templates.TemplateResponse(
        request,
        "colorize.html",
        {"references": references},
    )


@router.post("/api/colorize", response_model=ColorizeResponse)
async def start_colorization(
    file: UploadFile,
    reference_ids: str = Form(...),  # Comma-separated list of reference IDs
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> ColorizeResponse:
    """
    Start colorization of an infrared image.

    Upload an infrared image and specify which reference images to use.
    Returns a job ID for tracking progress.
    """
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

    ref_id_list = [r.strip() for r in reference_ids.split(",") if r.strip()]
    if not ref_id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one reference image must be selected",
        )

    # Validate reference IDs
    for ref_id in ref_id_list:
        ref = await storage.get_reference_image(ref_id)
        if ref is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reference image not found: {ref_id}",
            )

    # Save uploaded image
    _upload_id, upload_path = await storage.save_upload(
        file.filename or "infrared.jpg", content
    )
    upload_url = f"/data/uploads/{upload_path.name}"

    # Create job
    job = await storage.create_job(upload_url, ref_id_list)

    # Start colorization in background
    task = asyncio.create_task(_process_colorization(job.job_id, settings))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ColorizeResponse(
        job_id=job.job_id,
        status=JobStatus.PENDING,
        message="Colorization started",
    )


async def _process_colorization(job_id: str, settings: Settings) -> None:
    """Process colorization in background."""
    storage = StorageService(settings=settings)
    replicate_service = ReplicateService(settings=settings)

    try:
        job = await storage.get_job(job_id)
        if job is None:
            logger.error(f"Job not found: {job_id}")
            return

        await storage.update_job(job_id, status=JobStatus.PROCESSING)

        # Get paths
        infrared_filename = job.infrared_image_url.split("/")[-1]
        infrared_path = settings.uploads_dir / infrared_filename

        # Use the first reference image for now
        # Future: could combine multiple references or let user choose
        ref_id = job.reference_ids[0]
        ref_path = storage.get_reference_file_path(ref_id)

        if ref_path is None:
            await storage.update_job(
                job_id,
                status=JobStatus.FAILED,
                error_message="Reference image file not found",
            )
            return

        # Start Replicate prediction
        prediction_id = await replicate_service.colorize(
            infrared_image_path=infrared_path,
            reference_image_path=ref_path,
        )

        await storage.update_job(job_id, replicate_prediction_id=prediction_id)

        # Poll for completion
        max_attempts = 60  # 5 minutes max
        for _ in range(max_attempts):
            (
                status_str,
                result_url,
                error_message,
            ) = await replicate_service.get_prediction_status(prediction_id)

            if status_str == "succeeded" and result_url:
                # Download and save result
                result_content = await replicate_service.download_result(result_url)
                result_path = await storage.save_result(job_id, result_content)
                result_url_local = f"/data/results/{result_path.name}"

                await storage.update_job(
                    job_id,
                    status=JobStatus.COMPLETED,
                    result_url=result_url_local,
                )
                return

            elif status_str == "failed":
                await storage.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    error_message=error_message or "Colorization failed",
                )
                return

            elif status_str == "canceled":
                await storage.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    error_message="Colorization was canceled",
                )
                return

            await asyncio.sleep(5)

        # Timeout
        await storage.update_job(
            job_id,
            status=JobStatus.FAILED,
            error_message="Colorization timed out",
        )

    except Exception as e:
        logger.exception(f"Error processing colorization job {job_id}")
        await storage.update_job(
            job_id,
            status=JobStatus.FAILED,
            error_message=str(e),
        )


@router.get("/api/colorize/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    storage: StorageService = Depends(get_storage_service),
) -> JobStatusResponse:
    """Get the status of a colorization job."""
    job = await storage.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        result_url=job.result_url,
        error_message=job.error_message,
    )


@router.get("/api/colorize/{job_id}/result")
async def get_job_result(
    job_id: str,
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Get the result image for a completed job."""
    job = await storage.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status != JobStatus.COMPLETED or job.result_url is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed or result not available",
        )

    result_filename = job.result_url.split("/")[-1]
    result_path = settings.results_dir / result_filename

    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found",
        )

    return FileResponse(
        path=result_path,
        media_type="image/png",
        filename=f"colorized_{job_id}.png",
    )
