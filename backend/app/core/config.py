import os
from typing import List
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "CommunityOS API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Google Gemini GenAI SDK
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))
    GEMINI_MAX_RETRIES: int = int(os.getenv("GEMINI_MAX_RETRIES", "1"))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    # Firebase
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "communityos-demo")
    FIREBASE_SERVICE_ACCOUNT_KEY: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "")
    
    # CORS: Parse comma-separated list of origins. In production never allow '*'
    @property
    def allowed_origins(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", ""))
        if raw:
            origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
            if origins:
                return origins
        
        # Default local origins for development
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        if frontend_url and frontend_url not in default_origins:
            default_origins.append(frontend_url)
        return default_origins

    def is_production(self) -> bool:
        return self.ENVIRONMENT in ["production", "prod"]

settings = Settings()
