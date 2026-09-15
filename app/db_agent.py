from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.db_agent_core import DBStockAgent
from app.domain import decide_stock_status
from app.mcp_gateway import MCPGateway
from app.models import (
    CustomerRequest,
    CustomerResponse,
    OutOfStockEvent,
    ProductSearchResult,
    StockStatus,
    TelegramResult,
)
from app.settings import get_settings
from app.tracing import TraceRecorder, configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="DB Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "db-agent"}


@app.get("/products")
async def products() -> dict:
    request_id = str(uuid4())
    trace = TraceRecorder(request_id, "db-agent")
    data = await MCPGateway(settings.mcp_server_url, trace).call("list_products", {})
    catalog = ProductSearchResult.model_validate(data)
    return {
        "request_id": request_id,
        "products": [item.model_dump() for item in catalog.products],
        "trace": [item.model_dump(mode="json") for item in trace.events],
    }


@app.post("/requests", response_model=CustomerResponse)
async def handle_customer_request(payload: CustomerRequest) -> CustomerResponse:
    trace = TraceRecorder(payload.request_id, "db-agent")
    trace.add(
        "customer.request.received",
        "Müşteri talebi DB Agent tarafından alındı.",
        {"message_length": len(payload.message)},
    )

    try:
        product = await DBStockAgent(settings, trace).resolve_product(payload.message)
        status = decide_stock_status(product)

        if status == StockStatus.PRODUCT_NOT_FOUND:
            trace.add(
                "stock.decision",
                "Ürün bulunamadı; Telegram Agent çağrılmayacak.",
                {"status": status},
            )
            return CustomerResponse(
                request_id=payload.request_id,
                status=status,
                customer_message=(
                    "İstediğiniz ürünü katalogda bulamadım. Lütfen ürün adını "
                    "daha açık yazar mısınız?"
                ),
                trace=trace.events,
            )

        if product is None:  # Tip denetleyicisi için koruyucu kontrol.
            raise RuntimeError("Stok durumu için ürün bilgisi eksik.")

        if status == StockStatus.IN_STOCK:
            trace.add(
                "stock.decision",
                "Stok mevcut; akış DB Agent'ta tamamlandı.",
                {"status": status, "stock_quantity": product.stock_quantity},
            )
            return CustomerResponse(
                request_id=payload.request_id,
                status=status,
                customer_message=(
                    f"{product.name} stoklarımızda mevcut. "
                    f"Güncel stok: {product.stock_quantity}."
                ),
                product=product,
                trace=trace.events,
            )

        trace.add(
            "stock.decision",
            "Stok 0; OUT_OF_STOCK olayı oluşturulacak.",
            {"status": status, "stock_quantity": product.stock_quantity},
        )
        event = OutOfStockEvent(
            request_id=payload.request_id,
            product_id=product.id,
            product_name=product.name,
        )
        trace.add(
            "a2a.request.started",
            "OUT_OF_STOCK olayı Telegram Agent'a gönderiliyor.",
            {"event_id": event.event_id, "target": "telegram-agent"},
        )

        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.post(
                f"{settings.telegram_agent_url}/events/out-of-stock",
                json=event.model_dump(mode="json"),
            )
            response.raise_for_status()
        telegram_result = TelegramResult.model_validate(response.json())
        # Telegram Agent'ın kendi adımları, A2A tamamlandı olayından kronolojik
        # olarak önce gerçekleştiği için iz listesine önce onlar eklenir.
        trace.events.extend(telegram_result.trace)
        trace.add(
            "a2a.request.completed",
            "Telegram Agent yanıtı alındı.",
            {"success": telegram_result.success, "dry_run": telegram_result.dry_run},
        )

        return CustomerResponse(
            request_id=payload.request_id,
            status=status,
            customer_message=f"Üzgünüz, {product.name} şu anda stokta bulunmuyor.",
            product=product,
            trace=trace.events,
        )
    except Exception as exc:
        trace.add(
            "agent.error",
            "Talep işlenirken kontrollü bir hata oluştu.",
            {"error_type": type(exc).__name__},
        )
        return CustomerResponse(
            request_id=payload.request_id,
            status=StockStatus.ERROR,
            customer_message="Talebiniz şu anda işlenemedi. Lütfen tekrar deneyin.",
            trace=trace.events,
        )
