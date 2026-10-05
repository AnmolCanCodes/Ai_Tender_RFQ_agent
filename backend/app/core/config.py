from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    HF_TOKEN: str
    HF_MODEL: str
    HF_EMBEDDING_MODEL: str

    REDIS_URL: str

    ENVIRONMENT: str = "development"
    

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

