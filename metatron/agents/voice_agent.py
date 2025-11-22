"""
LiveKit voice agent that processes real-time voice conversations
through the Metatron Closer pipeline.
"""

import asyncio
import sys
from typing import AsyncIterator
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    voice,
)
from livekit.agents.llm.llm import APIConnectOptions
from livekit.plugins import openai, silero, elevenlabs
from livekit.plugins.elevenlabs import VoiceSettings

try:
    from metatron.agents.closer import Closer
    from metatron.config import settings
    from metatron.utils.logger import logger
except ImportError:
    from agents.closer import Closer
    from config import settings
    from utils.logger import logger


class CloserLLMStream(llm.LLMStream):
    """Custom LLM stream that yields Closer pipeline responses."""
    
    def __init__(
        self,
        closer_llm: "CloserLLM",
        chat_ctx: llm.ChatContext,
        tools: list,
        conn_options: APIConnectOptions,
    ):
        super().__init__(
            llm=closer_llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
        )
        self._closer = closer_llm.closer
        self._response = None
    
    async def _run(self) -> None:
        """Generate response from Closer pipeline and send via event channel."""
        # Get the last user message from chat context
        user_messages = [msg for msg in self._chat_ctx.items if msg.role == "user"]
        
        if not user_messages:
            response = "¿En qué puedo ayudarte?"
        else:
            # Get text content from the message
            last_user_msg = user_messages[-1]
            user_message = last_user_msg.text_content  # Use text_content property
            logger.info(f"CloserLLM processing: {user_message}")
            
            try:
                # Process through Closer pipeline
                result = self._closer.process_message(
                    incoming_text=user_message,
                    stage=self._closer.context.stage
                )
                
                response = result['adapted_response']
                logger.info(f"CloserLLM response: {response[:100]}...")
                
            except Exception as e:
                logger.error(f"Error in Closer pipeline: {e}", exc_info=True)
                response = "Disculpa, tuve un problema procesando eso. ¿Puedes repetir?"
        
        # Send the response as a chat chunk via the event channel
        # Note: livekit-agents 1.3+ uses delta directly, not choices array
        chunk = llm.ChatChunk(
            id=f"closer-{id(response)}",  # Unique ID for this chunk
            delta=llm.ChoiceDelta(content=response, role="assistant")
        )
        await self._event_ch.send(chunk)


class CloserLLM(llm.LLM):
    """
    Custom LLM that processes messages through the Metatron Closer pipeline
    instead of calling external LLM APIs.
    """
    
    def __init__(self, closer_instance: Closer):
        super().__init__()  # Initialize EventEmitter and ABC
        self.closer = closer_instance
        logger.info("CloserLLM initialized with Closer pipeline")
    
    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool | llm.RawFunctionTool] | None = None,
        conn_options: APIConnectOptions | None = None,
        **kwargs,
    ) -> llm.LLMStream:
        """
        Process chat through the Closer pipeline.
        
        Returns:
            LLMStream that supports async context manager protocol
        """
        tools = tools or []
        conn_options = conn_options or APIConnectOptions()
        
        # Return custom stream that implements async context manager
        return CloserLLMStream(
            closer_llm=self,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options,
        )


async def entrypoint(ctx: JobContext):
    """
    Entry point called when a participant joins a LiveKit room.
    Sets up the voice agent and handles the conversation.
    
    Args:
        ctx: JobContext from LiveKit
    """
    logger.info(f"Voice agent joining room: {ctx.room.name}")
    
    # Connect to the room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Wait for participant
    participant = await ctx.wait_for_participant()
    
    # Detect if this is an outbound call
    is_outbound = (
        "phone-" in participant.identity or 
        "call-" in ctx.room.name or
        participant.identity.startswith("+")
    )
    
    logger.info(f"Participant joined: {participant.identity} (outbound call: {is_outbound})")
    
    # Validate required settings
    if not settings.openai_api_key:
        logger.error("OpenAI API key not configured")
        raise ValueError("OPENAI_API_KEY is required for voice agent")
    
    if not settings.elevenlabs_api_key:
        logger.error("ElevenLabs API key not configured")
        raise ValueError("ELEVENLABS_API_KEY is required for voice agent")
    
    # Initialize Closer instance for this session
    closer = Closer(load_context_from_files=True)
    logger.info("✅ Closer initialized for this session")
    
    # Determine greeting based on call type
    if is_outbound:
        initial_greeting = "Hola, le llamo de parte de nuestra empresa. ¿Tiene un momento para hablar sobre nuestros servicios?"
    else:
        initial_greeting = "Hola, gracias por llamar. Soy tu asesor de ventas. ¿En qué puedo ayudarte hoy?"
    
    logger.info(f"Using {'outbound' if is_outbound else 'inbound'} call configuration")
    
    # Create custom LLM that routes through Closer
    custom_llm = CloserLLM(closer)
    
    # Create voice agent session with custom LLM
    logger.info("Creating voice agent session...")
    
    # Configure ElevenLabs TTS for Spanish using official LiveKit plugin
    # Voice IDs: 
    #   - "ThT5KcBeYPX3keUQqHPh" = Matias (Spanish male)
    #   - "ODq5zmih8GrVes37Dizd" = Patrick (multilingual male)
    
    # Configure voice settings for natural, expressive speech
    voice_settings = VoiceSettings(
        stability=0.6,  # Balanced stability (0.0-1.0)
        similarity_boost=0.8,  # Higher for more natural voice
        style=0.3,  # Some expressiveness
        use_speaker_boost=True,  # Enhanced audio quality
    )
    
    elevenlabs_tts = elevenlabs.TTS(
        voice_id="ThT5KcBeYPX3keUQqHPh",  # Spanish male voice (Matias)
        model="eleven_turbo_v2_5",  # Fast, high-quality model with low latency
        api_key=settings.elevenlabs_api_key,
        language="es",  # Spanish
        voice_settings=voice_settings,  # Voice customization settings
    )
    logger.info("ElevenLabs TTS configured with Spanish voice (Matias)")
    
    session = voice.AgentSession(
        stt=openai.STT(model="whisper-1", language="es"),
        vad=silero.VAD.load(),
        llm=custom_llm,  # Use our custom Closer LLM
        tts=elevenlabs_tts,  # Use official LiveKit ElevenLabs plugin
        allow_interruptions=True,
    )
    
    # Determine instructions based on call type
    instructions = (
        "Eres un asesor de ventas profesional. Sé cortés y profesional."
        if is_outbound
        else "Eres un asesor de ventas amigable. Ayuda al cliente con sus necesidades."
    )
    
    # Start the session in the room with the agent
    logger.info("Starting voice assistant session...")
    await session.start(
        room=ctx.room,
        agent=voice.Agent(instructions=instructions),
    )
    
    # Send initial greeting (after session started)
    logger.info(f"Sending greeting: {initial_greeting[:50]}...")
    # Wait longer for session to fully initialize (especially TTS)
    await asyncio.sleep(2.0)  # Increased delay to ensure TTS is ready
    
    try:
        await session.say(initial_greeting, allow_interruptions=True)
        logger.info("✅ Initial greeting sent successfully")
    except Exception as e:
        logger.error(f"❌ Failed to send initial greeting: {e}")
    
    logger.info("Voice agent started successfully and waiting for conversation")


def run_voice_worker():
    """
    Run the LiveKit voice worker.
    This is the main entry point for the voice agent worker.
    """
    # Validate configuration
    if not settings.livekit_url:
        raise ValueError("LIVEKIT_URL is required. Please set it in your .env file")
    if not settings.livekit_api_key:
        raise ValueError("LIVEKIT_API_KEY is required. Please set it in your .env file")
    if not settings.livekit_api_secret:
        raise ValueError("LIVEKIT_API_SECRET is required. Please set it in your .env file")
    
    logger.info("Starting Metatron Voice Worker...")
    logger.info(f"LiveKit URL: {settings.livekit_url}")
    logger.info(f"OpenAI API: {'configured' if settings.openai_api_key else 'NOT CONFIGURED'}")
    logger.info(f"ElevenLabs API: {'configured' if settings.elevenlabs_api_key else 'NOT CONFIGURED'}")
    
    # Run the worker with CLI
    # Note: cli.run_app expects to parse sys.argv, so we need to provide the right format
    sys.argv = ["metatron-voice-worker", "start"]
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
            ws_url=settings.livekit_url,
        )
    )


if __name__ == "__main__":
    run_voice_worker()
