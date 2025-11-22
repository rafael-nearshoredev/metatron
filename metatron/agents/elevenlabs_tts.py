"""
ElevenLabs TTS plugin for LiveKit agents.
Converts text to speech using ElevenLabs' streaming API.
"""

import asyncio
import httpx
from typing import AsyncIterator
from livekit.agents import tts

try:
    from ..utils.logger import logger
except ImportError:
    from utils.logger import logger


class ElevenLabsTTS(tts.TTS):
    """
    Text-to-Speech implementation using ElevenLabs API with streaming support.
    Integrates with LiveKit agents framework.
    """
    
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model: str = "eleven_turbo_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        """
        Initialize ElevenLabs TTS.
        
        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID for synthesis (supports custom cloned voices)
            model: TTS model to use (eleven_turbo_v2_5, eleven_multilingual_v2, etc.)
            stability: Voice stability (0.0 to 1.0)
            similarity_boost: Voice similarity boost (0.0 to 1.0)
            style: Voice style exaggeration (0.0 to 1.0)
            use_speaker_boost: Enable speaker boost for better quality
        """
        super().__init__(
            streaming_supported=True,  # ElevenLabs supports streaming
            sample_rate=24000,
            num_channels=1,
        )
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.use_speaker_boost = use_speaker_boost
        self.api_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    async def synthesize(self, text: str) -> AsyncIterator[tts.SynthesizedAudio]:
        """
        Synthesize text to speech using ElevenLabs streaming API.
        
        Args:
            text: Text to synthesize
            
        Yields:
            SynthesizedAudio containing the audio data chunks
        """
        logger.info(f"ElevenLabs TTS: Synthesizing text ({len(text)} chars): {text[:50]}...")
        logger.info(f"Using voice_id: {self.voice_id}, model: {self.model}")
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    
                    # Stream audio chunks as they arrive
                    audio_chunks = []
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            audio_chunks.append(chunk)
                    
                    # Combine all chunks
                    audio_data = b"".join(audio_chunks)
                    
                    logger.info(f"ElevenLabs TTS: Successfully synthesized {len(audio_data)} bytes of audio")
                    
                    yield tts.SynthesizedAudio(
                        text=text,
                        data=audio_data,
                    )
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"ElevenLabs TTS: HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"ElevenLabs TTS: Error during synthesis: {e}")
            raise
        
        logger.info("ElevenLabs TTS: Synthesis complete")

