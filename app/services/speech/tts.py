"""Text-to-speech service."""
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings


class TextToSpeechService:
    """Service for converting text to speech."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "tts-1",
    ) -> bytes:
        """
        Synthesize speech from text using OpenAI TTS.

        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: Model to use (tts-1 or tts-1-hd)

        Returns:
            Audio bytes (MP3 format)
        """
        try:
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
            )
            return response.content
        except Exception as e:
            raise Exception(f"TTS synthesis failed: {str(e)}")

    def generate_twiml_response(self, text: str) -> str:
        """
        Generate TwiML XML for Twilio to speak text.

        Args:
            text: Text to speak

        Returns:
            TwiML XML string
        """
        # Escape XML special characters
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna-Neural">{escaped_text}</Say>
</Response>"""

    def generate_twiml_with_gather(self, text: str, action_url: str) -> str:
        """
        Generate TwiML with Gather for collecting user input.

        Args:
            text: Text to speak before gathering
            action_url: URL to send gathered input to

        Returns:
            TwiML XML string
        """
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather action="{action_url}" method="POST" input="speech" speechTimeout="auto" language="en-US">
        <Say voice="Polly.Joanna-Neural">{escaped_text}</Say>
    </Gather>
    <Say voice="Polly.Joanna-Neural">I didn't catch that. Please try again.</Say>
    <Redirect>{action_url}</Redirect>
</Response>"""

