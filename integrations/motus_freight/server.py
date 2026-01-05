"""
Motus Freight In-Transit Integration Server

FastAPI server with endpoints for:
- In-transit polling and call triggering
- Health checks
- Manual testing
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from handlers import in_transit

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
async def sync_in_transit_endpoint():
    """
    In-Transit Sync Endpoint

    Polls Turvo for En Route shipments and triggers calls
    for loads 3-4 hours from delivery

    Called by:
    - External cron job (every 30 minutes, after hours only)
    - Manual trigger

    Returns:
        dict: Execution summary with calls triggered
    """
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
