import httpx
from fastapi import FastAPI
from openai import AsyncOpenAI

from app.models import OutOfStockEvent, TelegramResult
from app.settings import get_settings
from app.tracing import TraceRecorder, configure_logging

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Telegram Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-agent"}


def fallback_message(event: OutOfStockEvent) -> str:
    """LLM erişilemezse kritik uyarının kaybolmasını önleyen sabit metin."""

    return (
        "⚠️ Stok Uyarısı\n"
        f"Ürün: {event.product_name} ({event.product_id})\n"
        "Stok: 0\n"
        f"Talep No: {event.request_id}"
    )


async def generate_message(
    event: OutOfStockEvent, trace: TraceRecorder
) -> tuple[str, bool]:
    if settings.llm_dry_run or not settings.openrouter_api_key:
        trace.add(
            "llm.fallback",
            "OpenRouter kapalı; güvenli Telegram şablonu kullanıldı.",
        )
        return fallback_message(event), True

    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            default_headers={"X-OpenRouter-Title": "DB Telegram Agent Demo"},
        )
        trace.add(
            "llm.request.started",
            "Telegram uyarı metni OpenRouter ile hazırlanıyor.",
            {"model": settings.openrouter_model},
        )
        completion = await client.chat.completions.create(
            model=settings.openrouter_model,
            max_tokens=160,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Sen dahili stok uyarıları yazan Telegram Agent'sın. "
                        "Yalnızca verilen olayı kullan. Türkçe, kısa, açık ve "
                        "eyleme dönük bir mesaj yaz; yeni bilgi uydurma."
                    ),
                },
                {
                    "role": "user",
                    "content": event.model_dump_json(),
                },
            ],
            extra_body={
                "reasoning": {"effort": settings.openrouter_reasoning_effort}
            },
        )
        content = (completion.choices[0].message.content or "").strip()
        if not content:
            raise ValueError("Model boş Telegram mesajı üretti.")
        trace.add(
            "llm.request.completed",
            "Telegram uyarı metni üretildi.",
            {"message_length": len(content)},
        )
        return content[:1000], False
    except Exception as exc:
        trace.add(
            "llm.fallback",
            "Model çağrısı başarısız; güvenli Telegram şablonuna dönüldü.",
            {"error_type": type(exc).__name__},
        )
        return fallback_message(event), True


@app.post("/events/out-of-stock", response_model=TelegramResult)
async def notify_out_of_stock(event: OutOfStockEvent) -> TelegramResult:
    trace = TraceRecorder(event.request_id, "telegram-agent")
    trace.add(
        "a2a.event.received",
        "DB Agent'tan OUT_OF_STOCK olayı alındı.",
        {"event_id": event.event_id, "product_id": event.product_id},
    )
    message_text, used_fallback = await generate_message(event, trace)

    effective_dry_run = (
        settings.telegram_dry_run
        or not settings.telegram_bot_token
        or not settings.telegram_chat_id
    )
    if effective_dry_run:
        trace.add(
            "telegram.dry_run",
            "Telegram gönderimi simüle edildi; dış servise istek yapılmadı.",
            {"used_fallback_message": used_fallback},
        )
        return TelegramResult(
            request_id=event.request_id,
            success=True,
            dry_run=True,
            message_text=message_text,
            trace=trace.events,
        )

    # Token URL'nin içinde bulunduğu için URL hiçbir log kaydına eklenmez.
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
            response = await client.post(
                api_url,
                json={"chat_id": settings.telegram_chat_id, "text": message_text},
            )
            body = response.json()
        success = response.is_success and bool(body.get("ok"))
        if success:
            trace.add("telegram.sent", "Telegram mesajı gönderildi.")
        else:
            # Telegram'ın açıklaması token içermez ve yanlış chat_id gibi
            # yapılandırma sorunlarını eğitim ekranında anlaşılır kılar.
            description = str(body.get("description", "Bilinmeyen Telegram hatası"))
            trace.add(
                "telegram.rejected",
                "Telegram API mesajı kabul etmedi.",
                {
                    "status_code": response.status_code,
                    "description": description[:200],
                },
            )
    except Exception as exc:
        success = False
        trace.add(
            "telegram.error",
            "Telegram gönderimi sırasında hata oluştu.",
            {"error_type": type(exc).__name__},
        )

    return TelegramResult(
        request_id=event.request_id,
        success=success,
        dry_run=False,
        message_text=message_text,
        trace=trace.events,
    )
