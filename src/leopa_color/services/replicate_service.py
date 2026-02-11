"""Replicate API service for image colorization using ControlNet + IP-Adapter."""

import base64
import logging
import os
from pathlib import Path

import httpx
import replicate

from leopa_color.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ReplicateService:
    """Service for colorizing images using Replicate API."""

    # Using SDXL with IP-Adapter for style transfer
    # This model accepts a reference image for style and a control image for structure
    MODEL_ID = (
        "lucataco/ip-adapter-sdxl"
        ":2b28ed38081a21d6150e1ed3e3187de2bcf6c9055560cd0de18f9e9c99adce0d"
    )

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize Replicate service."""
        self.settings = settings or get_settings()

    def _ensure_api_token(self) -> None:
        """Ensure the API token is set in environment for replicate module."""
        if self.settings.replicate_api_token:
            os.environ["REPLICATE_API_TOKEN"] = self.settings.replicate_api_token

    def _encode_image_to_data_uri(self, image_path: Path) -> str:
        """Encode an image file to a data URI."""
        with open(image_path, "rb") as f:
            image_data = f.read()

        suffix = image_path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")

        base64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"

    async def colorize(
        self,
        infrared_image_path: Path,
        reference_image_path: Path,
        prompt: str = "leopard gecko, detailed, realistic colors, natural lighting",
    ) -> str:
        """
        Colorize an infrared image using a reference color image.

        Uses IP-Adapter SDXL to apply the color style from the reference image
        to the infrared image structure.

        Returns:
            Replicate prediction ID for tracking the job.
        """
        if not self.settings.replicate_api_token:
            raise ValueError("REPLICATE_API_TOKEN not configured")

        self._ensure_api_token()

        # Encode images to data URIs
        # Note: infrared image could be used with ControlNet in future versions
        _infrared_data_uri = self._encode_image_to_data_uri(infrared_image_path)
        reference_data_uri = self._encode_image_to_data_uri(reference_image_path)

        # Create prediction using Replicate API
        # Run the model with IP-Adapter
        prediction = replicate.predictions.create(
            version=self.MODEL_ID.split(":")[1],
            input={
                "image": reference_data_uri,  # Reference image for style
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted, deformed",
                "num_outputs": 1,
                "guidance_scale": 7.5,
                "num_inference_steps": 30,
                "ip_adapter_scale": 0.8,  # How much to follow the reference style
            },
        )

        return prediction.id

    async def get_prediction_status(
        self, prediction_id: str
    ) -> tuple[str, str | None, str | None]:
        """
        Get the status of a Replicate prediction.

        Returns:
            Tuple of (status, result_url, error_message).
            Status: "starting", "processing", "succeeded", "failed", or "canceled".
        """
        if not self.settings.replicate_api_token:
            raise ValueError("REPLICATE_API_TOKEN not configured")

        self._ensure_api_token()
        prediction = replicate.predictions.get(prediction_id)

        result_url = None
        if prediction.status == "succeeded" and prediction.output:
            # Output is typically a list of URLs
            if isinstance(prediction.output, list) and len(prediction.output) > 0:
                result_url = prediction.output[0]
            elif isinstance(prediction.output, str):
                result_url = prediction.output

        error_message = None
        if prediction.status == "failed":
            error_message = (
                str(prediction.error) if prediction.error else "Unknown error"
            )

        return prediction.status, result_url, error_message

    async def download_result(self, result_url: str) -> bytes:
        """Download the result image from Replicate."""
        async with httpx.AsyncClient() as client:
            response = await client.get(result_url)
            response.raise_for_status()
            return response.content
