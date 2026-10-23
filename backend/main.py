from fastapi import FastAPI, HTTPException
from backend.database.connection import test_connection
from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.cricbuzz import router as cricbuzz_router
from backend.api.routes.sync import router as sync_router
from backend.api.routes.scorecard_sync import router as scorecard_sync_router

app = FastAPI(
    title="Cricbuzz LiveStats API",
    description="Real-time cricket insights and SQL-based analytics",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(cricbuzz_router)
app.include_router(sync_router)
app.include_router(scorecard_sync_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Cricbuzz LiveStats API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    try:
        result = test_connection()
        return {
            "api": "healthy",
            "database": "connected",
            "database_name": result[0],
        }
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from error
