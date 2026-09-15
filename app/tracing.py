import json
import logging
import time
from typing import Any

from app.models import TraceEvent


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level.upper(), format="%(message)s")
    # httpx istek URL'sini INFO seviyesinde yazar. Telegram Bot API token'ı
    # URL'nin bir parçası olduğu için üçüncü taraf HTTP loglarını susturuyoruz.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


class TraceRecorder:
    """UI ve terminal için aynı olayları üreten küçük iz kaydedici.

    Ham düşünce zinciri yerine karar özeti kaydeder. Böylece sistemin davranışı
    gözlemlenirken anahtarlar veya modele ait gizli reasoning içeriği sızmaz.
    """

    def __init__(self, request_id: str, component: str) -> None:
        self.request_id = request_id
        self.component = component
        self.events: list[TraceEvent] = []
        self._logger = logging.getLogger(component)

    def add(
        self,
        event: str,
        summary: str,
        details: dict[str, Any] | None = None,
    ) -> TraceEvent:
        item = TraceEvent(
            request_id=self.request_id,
            component=self.component,
            event=event,
            summary=summary,
            details=details or {},
        )
        self.events.append(item)
        self._logger.info(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
        return item


class Timer:
    def __enter__(self) -> "Timer":
        self.started = time.perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = round((time.perf_counter() - self.started) * 1000, 2)
