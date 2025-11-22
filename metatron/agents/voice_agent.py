"""
LiveKit voice agent that processes real-time voice conversations
through the Metatron Closer pipeline.
"""

import asyncio
from typing import Optional
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    voice,
)
from livekit.plugins import openai, silero

try:
    from ..agents.closer import Closer
    from ..agents.elevenlabs_tts import ElevenLabsTTS
    from ..config import settings
    from ..utils.logger import logger
except ImportError:
    from agents.closer import Closer
    from agents.elevenlabs_tts import ElevenLabsTTS
    from config import settings
    from utils.logger import logger


class MetatronVoiceAgent:
    """
    Voice agent wrapper for Metatron Closer.
    Handles real-time voice conversations using LiveKit.
    """
    
    def __init__(self):
        """Initialize the voice agent with a Closer instance."""
        self.closer = Closer(load_context_from_files=True)
        logger.info("MetatronVoiceAgent initialized with Closer")
    
    async def entrypoint(self, ctx: JobContext):
        """
        Entry point called when a participant joins a LiveKit room.
        Sets up the voice pipeline and handles the conversation.
        
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
        
        # Get voice_id from room metadata or use default
        import json
        voice_id = settings.elevenlabs_default_voice_id
        try:
            if ctx.room.metadata:
                metadata = json.loads(ctx.room.metadata)
                if "voice_id" in metadata:
                    voice_id = metadata["voice_id"]
                    logger.info(f"Using custom voice_id from room metadata: {voice_id}")
        except Exception as e:
            logger.warning(f"Could not parse room metadata, using default voice_id: {e}")
        
        # Initialize TTS with ElevenLabs
        logger.info(f"Initializing ElevenLabs TTS with voice_id: {voice_id}...")
        elevenlabs_tts = ElevenLabsTTS(
            api_key=settings.elevenlabs_api_key,
            model=settings.elevenlabs_model,
            voice_id=voice_id,
        )
        
        # Initialize STT with OpenAI Whisper
        logger.info("Initializing OpenAI Whisper STT...")
        stt = openai.STT(
            model="whisper-1",
            language="es",
        )
        
        # Initialize VAD (Voice Activity Detection)
        logger.info("Loading Silero VAD...")
        vad = silero.VAD.load()
        
        # Create voice agent
        logger.info("Creating voice agent...")
        assistant = voice.Agent(
            vad=vad,
            stt=stt,
            llm=self._create_llm_adapter(),
            tts=elevenlabs_tts,
        )
        
        # Start the agent
        logger.info("Starting voice assistant...")
        await assistant.start(ctx.room, participant)
        
        # Send greeting based on call type
        if is_outbound:
            greeting = "Hola, le llamo de parte de nuestra empresa. ¿Tiene un momento para hablar sobre nuestros servicios?"
            logger.info("Using outbound call greeting")
        else:
            greeting = "Hola, gracias por llamar. Soy tu asesor de ventas. ¿En qué puedo ayudarte hoy?"
            logger.info("Using inbound call greeting")
        
        await assistant.say(greeting, allow_interruptions=True)
        
        logger.info("Voice pipeline started successfully")
    
    def _create_llm_adapter(self) -> llm.LLM:
        """
        Creates an LLM adapter that routes through Metatron's Closer pipeline.
        
        Returns:
            LLM instance configured to process messages through Closer
        """
        async def process_function(
            function_name: str,
            call_ctx: llm.FunctionCallContext,
        ) -> str:
            """
            Process user message through Closer.
            
            Args:
                function_name: Name of the function being called
                call_ctx: Function call context with arguments
                
            Returns:
                Response text from the Closer pipeline
            """
            user_message = call_ctx.arguments.get("message", "")
            logger.info(f"Processing user input: {user_message}")
            
            try:
                # Process through Closer pipeline
                result = self.closer.process_message(
                    incoming_text=user_message,
                    stage=self.closer.context.stage
                )
                
                response = result['adapted_response']
                logger.info(f"Agent response: {response[:100]}...")
                
                # Update conversation stage based on sentiment/context if needed
                # This could be enhanced based on the evaluation results
                
                return response
                
            except Exception as e:
                logger.error(f"Error in Closer pipeline: {e}", exc_info=True)
                return "Disculpa, tuve un problema procesando eso. ¿Puedes repetir?"
        
        # Create LLM with function calling
        return llm.LLM.with_function(
            name="process_sales_conversation",
            description="Process customer message through sales pipeline",
            function=process_function,
        )


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
    
    agent = MetatronVoiceAgent()
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=agent.entrypoint,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
            ws_url=settings.livekit_url,
        )
    )


if __name__ == "__main__":
    run_voice_worker()

