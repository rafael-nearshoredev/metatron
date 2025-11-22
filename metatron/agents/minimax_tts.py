"""
MiniMax TTS plugin for LiveKit agents.
Converts text to speech using MiniMax's T2A API.
"""

import asyncio
import httpx
import base64
from typing import AsyncIterator
from livekit.agents import tts

try:
    from ..utils.logger import logger
except ImportError:
    from utils.logger import logger


class MiniMaxTTS(tts.TTS):
    """
    Text-to-Speech implementation using MiniMax API.
    Integrates with LiveKit agents framework.
    """
    
    def __init__(
        self,
        api_key: str,
        group_id: str,
        model: str = "speech-01-turbo",
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
    ):
        """
        Initialize MiniMax TTS.
        
        Args:
            api_key: MiniMax API key
            group_id: MiniMax group ID
            model: TTS model to use (speech-01-turbo or speech-01)
            voice_id: Voice ID for the synthesis
            speed: Speech speed (0.5 to 2.0)
            vol: Volume (0.1 to 10.0)
            pitch: Pitch adjustment (-12 to 12)
        """
        super().__init__(
            streaming_supported=False,  # MiniMax doesn't support streaming
            sample_rate=24000,
            num_channels=1,
        )
        self.api_key = api_key
        self.group_id = group_id
        self.model = model
        self.voice_id = voice_id
        self.speed = speed
        self.vol = vol
        self.pitch = pitch
        self.api_url = "https://api.minimax.chat/v1/t2a_v2"

    async def synthesize(self, text: str) -> AsyncIterator[tts.SynthesizedAudio]:
        """
        Synthesize text to speech using MiniMax API.
        
        Args:
            text: Text to synthesize
            
        Yields:
            SynthesizedAudio containing the audio data
        """
        logger.info(f"MiniMax TTS: Synthesizing text ({len(text)} chars): {text[:50]}...")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.voice_id,
                "speed": self.speed,
                "vol": self.vol,
                "pitch": self.pitch
            },
            "audio_setting": {
                "sample_rate": 24000,
                "bitrate": 128000,
                "format": "pcm"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    params={"GroupId": self.group_id}
                )
                response.raise_for_status()
                result = response.json()
                
                # MiniMax returns base64 encoded audio
                if "data" in result and "audio" in result["data"]:
                    audio_data = base64.b64decode(result["data"]["audio"])
                    
                    logger.info(f"MiniMax TTS: Successfully synthesized {len(audio_data)} bytes of audio")
                    
                    yield tts.SynthesizedAudio(
                        text=text,
                        data=audio_data,
                    )
                else:
                    logger.error(f"MiniMax TTS: Unexpected response format: {result}")
                    raise ValueError("Invalid response from MiniMax API")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"MiniMax TTS: HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"MiniMax TTS: Error during synthesis: {e}")
            raise
        
        logger.info("MiniMax TTS: Synthesis complete")

