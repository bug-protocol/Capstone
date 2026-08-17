import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Capstone Drug Safety & Medical Information Service"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "capstone-agentcore-super-secret-key-2026-production"
    JWT_SECRET_KEY: str = "capstone-agentcore-super-secret-key-2026-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword2026@localhost:5432/capstonedb"

    AGENTCORE_RUNTIME_ARN: Optional[str] = "arn:aws:bedrock-agentcore:ap-south-1:025066239748:runtime/Capstone_Agent-MFGzn2CPo6"
    AGENTCORE_MEMORY_ID: Optional[str] = None
    AWS_REGION: str = "ap-south-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env", extra="ignore")


settings = Settings()
