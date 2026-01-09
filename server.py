"""
Motus Freight In-Transit Integration Server

FastAPI server with endpoints for:
- In-transit polling and call triggering
- Health checks
- Manual testing
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from handlers import in_transit


def verify_api_key(authorization: str = Header(None)):
    """Verify API key from Authorization header"""
    api_key = os.getenv("API_SECRET_KEY")

    # If no API key configured, allow all requests (for backwards compatibility)
    if not api_key:
        return True

    # Check Bearer token format
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use: Bearer <token>")

    token = authorization.replace("Bearer ", "")
    if token != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True


app = FastAPI(
    title="Motus Freight In-Transit Integration",
    description="Turvo API integration for in-transit automated calls",
    version="2.0.0"
)

# Track sync status
sync_status = {
    "running": False,
    "last_run": None,
    "last_result": None
}


def run_sync_task():
    """Background task to run the sync"""
    global sync_status
    sync_status["running"] = True

    try:
        result = in_transit.sync_in_transit()
        sync_status["last_result"] = result
        sync_status["last_run"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        print(f"✗ Fatal error in sync_in_transit: {e}")
        sync_status["last_result"] = {"success": False, "error": str(e)}
        sync_status["last_run"] = datetime.now(timezone.utc).isoformat()
    finally:
        sync_status["running"] = False


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Motus Freight In-Transit Integration",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "in_transit_sync": "/sync-in-transit (POST)",
            "sync_status": "/sync-status (GET)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "motus-in-transit"
    }


@app.get("/sync-status")
async def get_sync_status(authorization: str = Header(None)):
    """
    Get the status of the last/current sync operation

    Returns:
        dict: Current sync status and last result
    """
    verify_api_key(authorization)

    return {
        "running": sync_status["running"],
        "last_run": sync_status["last_run"],
        "last_result": sync_status["last_result"]
    }


@app.post("/sync-in-transit")
async def sync_in_transit_endpoint(
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """
    In-Transit Sync Endpoint (Protected)

    Starts the sync process in the background and returns immediately.
    Check /sync-status for results.

    Authentication:
    - Requires Authorization header: Bearer <API_SECRET_KEY>
    - Set API_SECRET_KEY env var to enable authentication

    Called by:
    - External cron job (every 5 minutes during business hours)
    - Manual trigger

    Returns:
        dict: Acknowledgment that sync has started
    """
    # Verify API key
    verify_api_key(authorization)

    # Check if already running
    if sync_status["running"]:
        return JSONResponse(
            content={
                "success": True,
                "message": "Sync already in progress",
                "status": "running"
            },
            status_code=200
        )

    # Start background task
    background_tasks.add_task(run_sync_task)

    return JSONResponse(
        content={
            "success": True,
            "message": "Sync started in background",
            "status": "started",
            "check_status_at": "/sync-status"
        },
        status_code=202
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
