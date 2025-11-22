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
    # livekit_project_id: Optional[str] = Field(default=None, alias="LIVEKIT_PROJECT_ID")
    # livekit_url: Optional[str] = Field(default=None, alias="LIVEKIT_URL")
    # livekit_api_key: Optional[str] = Field(default=None, alias="LIVEKIT_API_KEY")
    # livekit_api_secret: Optional[str] = Field(default=None, alias="LIVEKIT_API_SECRET")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
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
    print(Fore.YELLOW + f"Groq API Key: {'***' if settings.groq_api_key else 'Not set'}")
    print(Fore.YELLOW + f"Groq Model: {settings.groq_model}\n")

    return settings


settings = load_settings()
