from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.models import CustomerRequest
from app.settings import get_settings
from app.tracing import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Stok Agent Demo", version="0.1.0")
index_path = Path(__file__).parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(index_path)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "web"}


@app.get("/api/products")
async def products() -> dict:
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.get(f"{settings.db_agent_url}/products")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Ürün servisine ulaşılamadı.") from exc


@app.post("/api/customer-requests")
async def customer_requests(payload: CustomerRequest) -> dict:
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.post(
                f"{settings.db_agent_url}/requests",
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="DB Agent'a ulaşılamadı.") from exc

