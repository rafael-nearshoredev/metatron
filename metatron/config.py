from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
from colorama import Fore, Style, init

init(autoreset=True)  # ensures colors auto-reset after each print


class Settings(BaseSettings):
    """
    Application settings with environment variable support and default values.
    """

    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # LiveKit settings
    livekit_project_id: Optional[str] = Field(default=None, alias="LIVEKIT_PROJECT_ID")
    livekit_url: Optional[str] = Field(default=None, alias="LIVEKIT_URL")
    livekit_api_key: Optional[str] = Field(default=None, alias="LIVEKIT_API_KEY")
    livekit_api_secret: Optional[str] = Field(default=None, alias="LIVEKIT_API_SECRET")
    livekit_sip_trunk_id: Optional[str] = Field(default=None, alias="LIVEKIT_SIP_TRUNK_ID")
    
    # OpenAI settings (for Whisper STT)
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    
    # Groq settings (for LLM processing)
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    
    # ElevenLabs TTS settings
    elevenlabs_api_key: Optional[str] = Field(default=None, alias="ELEVENLABS_API_KEY")
    elevenlabs_model: str = Field(default="eleven_turbo_v2_5", alias="ELEVENLABS_MODEL")
    elevenlabs_default_voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", alias="ELEVENLABS_DEFAULT_VOICE_ID")

    # MiniMax TTS settings
    minimax_api_key: Optional[str] = Field(default=None, alias="MINIMAX_API_KEY")
    minimax_group_id: Optional[str] = Field(default=None, alias="MINIMAX_GROUP_ID")
    minimax_tts_model: str = Field(default="speech-01-turbo", alias="MINIMAX_TTS_MODEL")
    minimax_voice_id: str = Field(default="male-qn-qingse", alias="MINIMAX_VOICE_ID")
    
    # Server settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=5885, alias="PORT")
    debug: bool = Field(default=True, alias="DEBUG")
    reload: bool = Field(default=True, alias="RELOAD")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def load_settings() -> Settings:
    """
    Load application settings from environment variables and .env file.
    """
    possible_env_paths = [
        Path("/opt/pysetup/.env"),
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    
    env_file_loaded = False
    for env_file_path in possible_env_paths:
        if env_file_path.exists():
            load_dotenv(env_file_path)
            print(Fore.GREEN + f"✔ Loaded environment variables from: {env_file_path}")
            env_file_loaded = True
            break
    
    if not env_file_loaded:
        paths = [str(p) for p in possible_env_paths]
        print(Fore.RED + f"✘ No .env file found in any of these locations: {paths}")
    
    settings = Settings()

    print(Fore.CYAN + "\nSettings:")
    print(
        Fore.YELLOW +
        f"Debug mode: {settings.debug} "
        f"--> Environment: {settings.environment if settings.environment else 'Not set'} "
        f"Server: {settings.host}:{settings.port}"
    )
    print(Fore.YELLOW + f"OpenAI API Key: {'***' if settings.openai_api_key else 'Not set'}")
    print(Fore.YELLOW + f"Groq API Key: {'***' if settings.groq_api_key else 'Not set'}")
    print(Fore.YELLOW + f"Groq Model: {settings.groq_model}")
    print(Fore.YELLOW + f"LiveKit Project ID: {'***' if settings.livekit_project_id else 'Not set'}")
    print(Fore.YELLOW + f"LiveKit URL: {settings.livekit_url if settings.livekit_url else 'Not set'}")
    print(Fore.YELLOW + f"LiveKit API Key: {'***' if settings.livekit_api_key else 'Not set'}")
    print(Fore.YELLOW + f"LiveKit SIP Trunk: {'***' if settings.livekit_sip_trunk_id else 'Not set'}")
    print(Fore.YELLOW + f"MiniMax API Key: {'***' if settings.minimax_api_key else 'Not set'}")
    print(Fore.YELLOW + f"MiniMax Group ID: {'***' if settings.minimax_group_id else 'Not set'}")
    print(Fore.YELLOW + f"MiniMax TTS Model: {settings.minimax_tts_model}")
    print(Fore.YELLOW + f"MiniMax Voice ID: {settings.minimax_voice_id}")
    print(Fore.YELLOW + f"ElevenLabs API Key: {'***' if settings.elevenlabs_api_key else 'Not set'}\n")

    return settings


settings = load_settings()
