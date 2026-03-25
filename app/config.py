import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./finance_tracker.db")

    # WhatsApp API
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secret_token")
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "mock_token")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "mock_id")

    # LLM & Transcription
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "mock_groq_key")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "mock_openai_key") # Optional if using Whisper

    class Config:
        env_file = ".env"

settings = Settings()
