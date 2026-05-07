from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.v1 import auth, patients, reminders, attendance, reports, chat, unified_reminders, users, profile

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(patients.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(reminders.router, prefix="/api/v1/reminders", tags=["Reminders"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(unified_reminders.router, prefix="/api/v1/unified-reminders", tags=["Unified Reminders"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])


@app.get("/")
async def root():
    return {"message": "Burjeel Smart Care Backend API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
