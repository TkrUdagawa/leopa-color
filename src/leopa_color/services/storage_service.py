"""Storage service for managing image files."""

import json
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles

from leopa_color.config import Settings, get_settings
from leopa_color.models import ColorizeJob, JobStatus, ReferenceImage


class StorageService:
    """Service for managing image storage."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize storage service."""
        self.settings = settings or get_settings()
        self.settings.ensure_directories()

    def _get_jobs_file(self) -> Path:
        """Get path to jobs JSON file."""
        return self.settings.data_dir / "jobs.json"

    def _get_references_meta_file(self) -> Path:
        """Get path to references metadata JSON file."""
        return self.settings.data_dir / "references.json"

    async def _load_jobs(self) -> dict[str, dict]:
        """Load jobs from JSON file."""
        jobs_file = self._get_jobs_file()
        if not jobs_file.exists():
            return {}
        async with aiofiles.open(jobs_file) as f:
            content = await f.read()
            return json.loads(content) if content else {}

    async def _save_jobs(self, jobs: dict[str, dict]) -> None:
        """Save jobs to JSON file."""
        async with aiofiles.open(self._get_jobs_file(), "w") as f:
            await f.write(json.dumps(jobs, default=str, indent=2))

    async def _load_references_meta(self) -> dict[str, dict]:
        """Load references metadata from JSON file."""
        meta_file = self._get_references_meta_file()
        if not meta_file.exists():
            return {}
        async with aiofiles.open(meta_file) as f:
            content = await f.read()
            return json.loads(content) if content else {}

    async def _save_references_meta(self, refs: dict[str, dict]) -> None:
        """Save references metadata to JSON file."""
        async with aiofiles.open(self._get_references_meta_file(), "w") as f:
            await f.write(json.dumps(refs, default=str, indent=2))

    async def save_reference_image(
        self, filename: str, content: bytes
    ) -> ReferenceImage:
        """Save a reference color image."""
        ref_id = str(uuid.uuid4())
        ext = Path(filename).suffix or ".jpg"
        stored_filename = f"{ref_id}{ext}"
        file_path = self.settings.references_dir / stored_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        ref = ReferenceImage(
            id=ref_id,
            filename=filename,
            created_at=datetime.now(),
            url=f"/data/references/{stored_filename}",
        )

        refs = await self._load_references_meta()
        refs[ref_id] = ref.model_dump()
        await self._save_references_meta(refs)

        return ref

    async def get_reference_images(self) -> list[ReferenceImage]:
        """Get all reference images."""
        refs = await self._load_references_meta()
        return [
            ReferenceImage(
                id=r["id"],
                filename=r["filename"],
                created_at=datetime.fromisoformat(r["created_at"])
                if isinstance(r["created_at"], str)
                else r["created_at"],
                url=r["url"],
            )
            for r in refs.values()
        ]

    async def get_reference_image(self, ref_id: str) -> ReferenceImage | None:
        """Get a reference image by ID."""
        refs = await self._load_references_meta()
        if ref_id not in refs:
            return None
        r = refs[ref_id]
        return ReferenceImage(
            id=r["id"],
            filename=r["filename"],
            created_at=datetime.fromisoformat(r["created_at"])
            if isinstance(r["created_at"], str)
            else r["created_at"],
            url=r["url"],
        )

    async def delete_reference_image(self, ref_id: str) -> bool:
        """Delete a reference image."""
        refs = await self._load_references_meta()
        if ref_id not in refs:
            return False

        ref = refs[ref_id]
        url = ref["url"]
        filename = url.split("/")[-1]
        file_path = self.settings.references_dir / filename

        if file_path.exists():
            file_path.unlink()

        del refs[ref_id]
        await self._save_references_meta(refs)
        return True

    def get_reference_file_path(self, ref_id: str) -> Path | None:
        """Get the file path for a reference image."""
        for file_path in self.settings.references_dir.iterdir():
            if file_path.stem == ref_id:
                return file_path
        return None

    async def save_upload(self, filename: str, content: bytes) -> tuple[str, Path]:
        """Save an uploaded infrared image."""
        upload_id = str(uuid.uuid4())
        ext = Path(filename).suffix or ".jpg"
        stored_filename = f"{upload_id}{ext}"
        file_path = self.settings.uploads_dir / stored_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return upload_id, file_path

    async def save_result(self, job_id: str, content: bytes, ext: str = ".png") -> Path:
        """Save a colorization result image."""
        stored_filename = f"{job_id}{ext}"
        file_path = self.settings.results_dir / stored_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return file_path

    async def create_job(
        self,
        infrared_image_url: str,
        reference_ids: list[str],
    ) -> ColorizeJob:
        """Create a new colorization job."""
        job_id = str(uuid.uuid4())
        job = ColorizeJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            infrared_image_url=infrared_image_url,
            reference_ids=reference_ids,
        )

        jobs = await self._load_jobs()
        jobs[job_id] = job.model_dump()
        await self._save_jobs(jobs)

        return job

    async def get_job(self, job_id: str) -> ColorizeJob | None:
        """Get a job by ID."""
        jobs = await self._load_jobs()
        if job_id not in jobs:
            return None
        j = jobs[job_id]
        return ColorizeJob(
            job_id=j["job_id"],
            status=JobStatus(j["status"]),
            created_at=datetime.fromisoformat(j["created_at"])
            if isinstance(j["created_at"], str)
            else j["created_at"],
            infrared_image_url=j["infrared_image_url"],
            reference_ids=j["reference_ids"],
            result_url=j.get("result_url"),
            error_message=j.get("error_message"),
            replicate_prediction_id=j.get("replicate_prediction_id"),
        )

    async def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        result_url: str | None = None,
        error_message: str | None = None,
        replicate_prediction_id: str | None = None,
    ) -> ColorizeJob | None:
        """Update a job."""
        jobs = await self._load_jobs()
        if job_id not in jobs:
            return None

        if status is not None:
            jobs[job_id]["status"] = status.value
        if result_url is not None:
            jobs[job_id]["result_url"] = result_url
        if error_message is not None:
            jobs[job_id]["error_message"] = error_message
        if replicate_prediction_id is not None:
            jobs[job_id]["replicate_prediction_id"] = replicate_prediction_id

        await self._save_jobs(jobs)
        return await self.get_job(job_id)
