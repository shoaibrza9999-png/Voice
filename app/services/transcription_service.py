import httpx
import os
import aiofiles
import logging
from app.config import settings
from groq import AsyncGroq

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.whatsapp_token = settings.WHATSAPP_API_TOKEN

    async def download_media(self, media_id: str) -> str:
        """
        Downloads a media file from WhatsApp given its media_id.
        Returns the local file path.
        """
        url = f"https://graph.facebook.com/v19.0/{media_id}"
        headers = {"Authorization": f"Bearer {self.whatsapp_token}"}

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get media URL
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                media_url = response.json().get("url")

                if not media_url:
                    logger.error("Failed to retrieve media URL")
                    return None

                # 2. Download actual media file
                media_response = await client.get(media_url, headers=headers)
                media_response.raise_for_status()

                # Save temporarily
                file_path = f"/tmp/{media_id}.ogg"
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(media_response.content)

                return file_path
        except Exception as e:
            logger.error(f"Error downloading media {media_id}: {e}")
            return None

    async def transcribe_audio(self, file_path: str) -> str:
        """
        Transcribes the audio file using Groq Whisper.
        """
        try:
            with open(file_path, "rb") as file:
                transcription = await self.groq_client.audio.transcriptions.create(
                  file=(file_path, file.read()), # Required format
                  model="whisper-large-v3-turbo",
                  prompt="Please transcribe the voice note",
                  response_format="json",
                  language="en",
                  temperature=0.0
                )

            # Cleanup temp file
            if os.path.exists(file_path):
                os.remove(file_path)

            return transcription.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            # Ensure cleanup on failure
            if os.path.exists(file_path):
                os.remove(file_path)
            return ""

transcription_service = TranscriptionService()
