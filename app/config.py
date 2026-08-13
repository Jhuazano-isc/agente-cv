from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_key: str
    openai_api_key: str
    default_openai_model: str
    api_url: str
    debug_mode: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
