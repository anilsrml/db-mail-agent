import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.mcp_gateway import MCPGateway
from app.models import Product, ProductSearchResult, ProductStockResult
from app.settings import Settings
from app.tracing import TraceRecorder


SYSTEM_PROMPT = """
Sen salt-okunur bir ürün stok agent'ısın.
Müşterinin doğal dilde istediği ürünü katalogda bulmak için MCP araçlarını kullan.
Önce search_product aracını anlamlı ve kısa bir ürün adıyla çağır.
Bir ürün bulduğunda ürün kodunu get_product_stock aracına gönder.
Asla stok uydurma ve araç sonucu olmadan stok kararı verme.
Ürün bulunamazsa yeni ürün üretme.
""".strip()


def _reasoning_token_count(completion: Any) -> int | None:
    usage = getattr(completion, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    return getattr(details, "reasoning_tokens", None)


class DBStockAgent:
    """Müşteri metnini MCP araç çağrılarına dönüştüren açık agent döngüsü."""

    def __init__(self, settings: Settings, trace: TraceRecorder) -> None:
        self.settings = settings
        self.trace = trace
        self.mcp = MCPGateway(settings.mcp_server_url, trace)

    async def resolve_product(self, customer_message: str) -> Product | None:
        if self.settings.llm_dry_run or not self.settings.openrouter_api_key:
            return await self._resolve_without_llm(customer_message)
        return await self._resolve_with_openrouter(customer_message)

    async def _resolve_with_openrouter(self, customer_message: str) -> Product | None:
        tools = await self.mcp.list_openai_tools()
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.settings.openrouter_api_key,
            default_headers={"X-OpenRouter-Title": "DB Telegram Agent Demo"},
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": customer_message},
        ]

        # Döngü özellikle görünür bırakıldı: model araç seçer, uygulama MCP aracını
        # çalıştırır ve sonucu modele geri verir. En fazla dört tur sonsuz döngüyü önler.
        for turn in range(1, 5):
            self.trace.add(
                "llm.request.started",
                "OpenRouter modelinden sonraki araç adımı isteniyor.",
                {"model": self.settings.openrouter_model, "turn": turn},
            )
            completion = await client.chat.completions.create(
                model=self.settings.openrouter_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=500,
                extra_body={
                    "reasoning": {
                        "effort": self.settings.openrouter_reasoning_effort
                    }
                },
            )
            assistant_message = completion.choices[0].message
            self.trace.add(
                "llm.request.completed",
                "Model yanıtı alındı; ham reasoning yerine kullanım özeti kaydedildi.",
                {
                    "turn": turn,
                    "tool_call_count": len(assistant_message.tool_calls or []),
                    "reasoning_tokens": _reasoning_token_count(completion),
                },
            )
            messages.append(assistant_message.model_dump(exclude_none=True))

            if not assistant_message.tool_calls:
                break

            for tool_call in assistant_message.tool_calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments or "{}")
                data = await self.mcp.call(name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(data, ensure_ascii=False),
                    }
                )

                if name == "search_product":
                    search = ProductSearchResult.model_validate(data)
                    if not search.products:
                        self.trace.add(
                            "agent.decision",
                            "Katalogda müşteri talebiyle eşleşen ürün bulunamadı.",
                        )
                        return None

                if name == "get_product_stock":
                    stock = ProductStockResult.model_validate(data)
                    product = stock.product if stock.found else None
                    summary = (
                        f"{product.id} ürünü bulundu; stok miktarı "
                        f"{product.stock_quantity}."
                        if product
                        else "Araç belirtilen ürün kodunu bulamadı."
                    )
                    self.trace.add("agent.decision", summary)
                    return product

        raise RuntimeError("Model gerekli stok aracını izin verilen tur içinde çağırmadı.")

    async def _resolve_without_llm(self, customer_message: str) -> Product | None:
        """Anahtar olmadan ekranı deneyebilmek için küçük geliştirme eşleştiricisi."""

        self.trace.add(
            "llm.dry_run",
            "OpenRouter kapalı; yerel ürün eşleştiricisi kullanılıyor.",
        )
        data = await self.mcp.call("list_products", {})
        products = ProductSearchResult.model_validate(data).products
        normalized_message = _normalize(customer_message)

        ranked = sorted(
            (
                (_match_score(normalized_message, _normalize(product.name)), product)
                for product in products
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] == 0:
            self.trace.add("agent.decision", "Yerel eşleştirici ürün bulamadı.")
            return None

        selected = ranked[0][1]
        stock_data = await self.mcp.call(
            "get_product_stock", {"product_id": selected.id}
        )
        product = ProductStockResult.model_validate(stock_data).product
        if product:
            self.trace.add(
                "agent.decision",
                f"Talep {product.id} ile eşleşti; stok miktarı {product.stock_quantity}.",
            )
        return product


def _normalize(value: str) -> str:
    translation = str.maketrans("ÇĞİÖŞÜçğıöşü", "CGIOSUcgiosu")
    return re.sub(r"[^a-z0-9 ]", " ", value.translate(translation).lower())


def _match_score(message: str, product_name: str) -> int:
    message_tokens = message.split()
    product_tokens = product_name.split()
    score = 0
    for product_token in product_tokens:
        if any(
            token == product_token
            or (
                len(token) >= 5
                and len(product_token) >= 5
                and token[:5] == product_token[:5]
            )
            for token in message_tokens
        ):
            score += 1
    return score

