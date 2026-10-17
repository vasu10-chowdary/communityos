from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import incidents, auth
from app.services.database import init_db
from app.services.firebase_service import init_firebase

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database engine & seed initial civic resources
    init_db()
    # Initialize Firebase Admin SDK if configured
    try:
        init_firebase()
    except Exception as e:
        print(f"[Lifespan Notice] Firebase fallback init: {e}")
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
        "cors_origins": settings.allowed_origins,
        "persistence": "sqlite"
    }

app.include_router(auth.router)
app.include_router(incidents.router)
