"""Pydantic models for request/response schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of a colorization job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReferenceImage(BaseModel):
    """Reference color image for colorization."""

    id: str
    filename: str
    created_at: datetime
    url: str = Field(description="URL to access the image")


class ReferenceImageList(BaseModel):
    """List of reference images."""

    references: list[ReferenceImage]


class ColorizeRequest(BaseModel):
    """Request to colorize an infrared image."""

    reference_ids: list[str] = Field(
        min_length=1,
        description="IDs of reference images to use for colorization",
    )


class ColorizeJob(BaseModel):
    """A colorization job."""

    job_id: str
    status: JobStatus
    created_at: datetime
    infrared_image_url: str
    reference_ids: list[str]
    result_url: str | None = None
    error_message: str | None = None
    replicate_prediction_id: str | None = None


class ColorizeResponse(BaseModel):
    """Response after starting colorization."""

    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: JobStatus
    result_url: str | None = None
    error_message: str | None = None
