"""
Motus Freight In-Transit Integration Server

FastAPI server with endpoints for:
- In-transit polling and call triggering
- Health checks
- Manual testing
"""

import os
from fastapi import FastAPI, HTTPException, Header
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
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Motus Freight In-Transit Integration",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "in_transit_sync": "/sync-in-transit (POST)"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "motus-in-transit"
    }


@app.post("/sync-in-transit")
async def sync_in_transit_endpoint(authorization: str = Header(None)):
    """
    In-Transit Sync Endpoint (Protected)

    Polls Turvo for En Route shipments and triggers calls
    for loads within call windows.

    Authentication:
    - Requires Authorization header: Bearer <API_SECRET_KEY>
    - Set API_SECRET_KEY env var to enable authentication

    Called by:
    - External cron job (every 15 minutes during business hours)
    - Manual trigger

    Returns:
        dict: Execution summary with calls triggered
    """
    # Verify API key
    verify_api_key(authorization)

    try:
        result = in_transit.sync_in_transit()
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print(f"✗ Fatal error in sync_in_transit: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
