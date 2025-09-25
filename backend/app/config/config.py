from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str
    MODEL_NAME: str
    TEMPERATURE: float

    class Config:
        env_file = ".env"

settings = Settings()