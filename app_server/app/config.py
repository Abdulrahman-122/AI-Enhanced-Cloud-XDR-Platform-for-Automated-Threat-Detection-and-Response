import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "XDR Security Platform - El Shorouk Academy"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Database URL (PostgreSQL)

    DATABASE_URL: str 

    # JWT Settings
    SECRET_KEY: str 
    ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30

    # Wazuh API Integration Settings
    WAZUH_API_URL: str = "https://localhost:55000"
    WAZUH_API_USERNAME: str = "wazuh-wui"
    WAZUH_API_PASSWORD: str = "wazuh-wui"
    WAZUH_VERIFY_SSL: bool = False
    WAZUH_REQUEST_TIMEOUT: float = 8.0

    # CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://192.168.50.101:5173",
        "https://brunette-headset-former-ben.trycloudflare.com",

    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
