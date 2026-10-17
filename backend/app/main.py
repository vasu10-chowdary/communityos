from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import incidents
from app.services.firebase_service import init_firebase

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Firebase Admin SDK on startup
    init_firebase()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="CommunityOS - AI-Powered Community Emergency Intelligence & Resource Coordination API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware with strict origin allowlisting (NO wildcard '*')
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "gemini_model": settings.GEMINI_MODEL,
        "cors_origins": settings.allowed_origins
    }

app.include_router(incidents.router)
