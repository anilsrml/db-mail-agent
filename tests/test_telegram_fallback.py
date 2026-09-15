from app.models import OutOfStockEvent
from app.telegram_agent import fallback_message


def test_fallback_contains_product_and_request() -> None:
    event = OutOfStockEvent(
        request_id="REQ-42",
        product_id="P-1002",
        product_name="Mekanik Klavye",
    )

    message = fallback_message(event)

    assert "Mekanik Klavye" in message
    assert "P-1002" in message
    assert "REQ-42" in message
    assert "Stok: 0" in message

