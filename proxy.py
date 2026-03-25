import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="WhatsApp Proxy Server")

# Target base URL for WhatsApp Cloud API
WHATSAPP_API_BASE = "https://graph.facebook.com"

@app.post("/{path:path}")
async def proxy_post(path: str, request: Request):
    """
    Proxy POST requests to the WhatsApp Cloud API.
    """
    target_url = f"{WHATSAPP_API_BASE}/{path}"

    # Extract original headers
    headers = dict(request.headers)

    # Remove host header to avoid conflicts
    if "host" in headers:
        del headers["host"]

    try:
        body = await request.body()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                target_url,
                content=body,
                headers=headers,
                timeout=30.0
            )

        return JSONResponse(
            content=response.json() if response.content else None,
            status_code=response.status_code
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

@app.get("/{path:path}")
async def proxy_get(path: str, request: Request):
    """
    Proxy GET requests (e.g. for media downloads).
    """
    target_url = f"{WHATSAPP_API_BASE}/{path}"

    headers = dict(request.headers)
    if "host" in headers:
        del headers["host"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                target_url,
                headers=headers,
                params=dict(request.query_params),
                timeout=30.0
            )

        # Return exact content with original headers for media
        return JSONResponse(
            content=response.json() if "application/json" in response.headers.get("content-type", "") else None,
            status_code=response.status_code
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Typically run on a different port or server instance
    uvicorn.run("proxy:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)), reload=True)
