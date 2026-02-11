"""Tests for the storage service."""

import pytest

from leopa_color.config import Settings
from leopa_color.models import JobStatus
from leopa_color.services.storage_service import StorageService


@pytest.fixture
def storage_service(test_settings: Settings) -> StorageService:
    """Create a storage service with test settings."""
    return StorageService(settings=test_settings)


class TestReferenceImages:
    """Tests for reference image operations."""

    @pytest.mark.asyncio
    async def test_save_reference_image(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test saving a reference image."""
        ref = await storage_service.save_reference_image("test.jpg", sample_image_bytes)

        assert ref.id is not None
        assert ref.filename == "test.jpg"
        assert ref.url.startswith("/data/references/")
        assert ref.url.endswith(".jpg")

    @pytest.mark.asyncio
    async def test_get_reference_images_empty(
        self, storage_service: StorageService
    ) -> None:
        """Test getting reference images when none exist."""
        refs = await storage_service.get_reference_images()
        assert refs == []

    @pytest.mark.asyncio
    async def test_get_reference_images(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test getting all reference images."""
        await storage_service.save_reference_image("test1.jpg", sample_image_bytes)
        await storage_service.save_reference_image("test2.png", sample_image_bytes)

        refs = await storage_service.get_reference_images()
        assert len(refs) == 2

    @pytest.mark.asyncio
    async def test_get_reference_image_by_id(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test getting a specific reference image."""
        saved_ref = await storage_service.save_reference_image(
            "test.jpg", sample_image_bytes
        )

        ref = await storage_service.get_reference_image(saved_ref.id)
        assert ref is not None
        assert ref.id == saved_ref.id
        assert ref.filename == "test.jpg"

    @pytest.mark.asyncio
    async def test_get_reference_image_not_found(
        self, storage_service: StorageService
    ) -> None:
        """Test getting a non-existent reference image."""
        ref = await storage_service.get_reference_image("nonexistent")
        assert ref is None

    @pytest.mark.asyncio
    async def test_delete_reference_image(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test deleting a reference image."""
        saved_ref = await storage_service.save_reference_image(
            "test.jpg", sample_image_bytes
        )

        deleted = await storage_service.delete_reference_image(saved_ref.id)
        assert deleted is True

        ref = await storage_service.get_reference_image(saved_ref.id)
        assert ref is None

    @pytest.mark.asyncio
    async def test_delete_reference_image_not_found(
        self, storage_service: StorageService
    ) -> None:
        """Test deleting a non-existent reference image."""
        deleted = await storage_service.delete_reference_image("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_reference_file_path(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test getting the file path for a reference image."""
        saved_ref = await storage_service.save_reference_image(
            "test.jpg", sample_image_bytes
        )

        path = storage_service.get_reference_file_path(saved_ref.id)
        assert path is not None
        assert path.exists()
        assert path.stem == saved_ref.id


class TestUploads:
    """Tests for upload operations."""

    @pytest.mark.asyncio
    async def test_save_upload(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test saving an uploaded image."""
        upload_id, file_path = await storage_service.save_upload(
            "infrared.jpg", sample_image_bytes
        )

        assert upload_id is not None
        assert file_path.exists()
        assert file_path.suffix == ".jpg"


class TestJobs:
    """Tests for job operations."""

    @pytest.mark.asyncio
    async def test_create_job(self, storage_service: StorageService) -> None:
        """Test creating a colorization job."""
        job = await storage_service.create_job(
            infrared_image_url="/data/uploads/test.jpg",
            reference_ids=["ref1", "ref2"],
        )

        assert job.job_id is not None
        assert job.status == JobStatus.PENDING
        assert job.infrared_image_url == "/data/uploads/test.jpg"
        assert job.reference_ids == ["ref1", "ref2"]
        assert job.result_url is None

    @pytest.mark.asyncio
    async def test_get_job(self, storage_service: StorageService) -> None:
        """Test getting a job by ID."""
        created_job = await storage_service.create_job(
            infrared_image_url="/data/uploads/test.jpg",
            reference_ids=["ref1"],
        )

        job = await storage_service.get_job(created_job.job_id)
        assert job is not None
        assert job.job_id == created_job.job_id

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, storage_service: StorageService) -> None:
        """Test getting a non-existent job."""
        job = await storage_service.get_job("nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_update_job_status(self, storage_service: StorageService) -> None:
        """Test updating job status."""
        created_job = await storage_service.create_job(
            infrared_image_url="/data/uploads/test.jpg",
            reference_ids=["ref1"],
        )

        updated_job = await storage_service.update_job(
            created_job.job_id,
            status=JobStatus.PROCESSING,
        )

        assert updated_job is not None
        assert updated_job.status == JobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_job_result(self, storage_service: StorageService) -> None:
        """Test updating job with result."""
        created_job = await storage_service.create_job(
            infrared_image_url="/data/uploads/test.jpg",
            reference_ids=["ref1"],
        )

        updated_job = await storage_service.update_job(
            created_job.job_id,
            status=JobStatus.COMPLETED,
            result_url="/data/results/test.png",
        )

        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.result_url == "/data/results/test.png"

    @pytest.mark.asyncio
    async def test_update_job_error(self, storage_service: StorageService) -> None:
        """Test updating job with error."""
        created_job = await storage_service.create_job(
            infrared_image_url="/data/uploads/test.jpg",
            reference_ids=["ref1"],
        )

        updated_job = await storage_service.update_job(
            created_job.job_id,
            status=JobStatus.FAILED,
            error_message="Something went wrong",
        )

        assert updated_job is not None
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_save_result(
        self, storage_service: StorageService, sample_image_bytes: bytes
    ) -> None:
        """Test saving a result image."""
        result_path = await storage_service.save_result(
            "test_job_id", sample_image_bytes
        )

        assert result_path.exists()
        assert result_path.stem == "test_job_id"
        assert result_path.suffix == ".png"
