"""Speech-to-text service."""
import base64
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings


class SpeechToTextService:
    """Service for converting speech to text."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe_audio(
        self, audio_data: bytes, format: str = "wav"
    ) -> str:
        """
        Transcribe audio to text using OpenAI Whisper.

        Args:
            audio_data: Raw audio bytes
            format: Audio format (wav, mp3, etc.)

        Returns:
            Transcribed text
        """
        # For Twilio, audio comes as base64-encoded WAV
        # We'll handle it directly
        try:
            # OpenAI Whisper API expects a file-like object
            # We'll create a temporary file or use the bytes directly
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.wav", audio_data, f"audio/{format}"),
            )
            return transcript.text
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")

    async def transcribe_twilio_recording(self, recording_url: str) -> str:
        """
        Transcribe a Twilio recording URL.

        Args:
            recording_url: URL to Twilio recording

        Returns:
            Transcribed text
        """
        import httpx

        async with httpx.AsyncClient() as client:
            # Fetch the recording
            response = await client.get(recording_url)
            response.raise_for_status()

            # Transcribe the audio
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=("recording.wav", response.content, "audio/wav"),
            )
            return transcript.text

