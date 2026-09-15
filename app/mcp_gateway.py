from typing import Any

from mcp import Client

from app.tracing import Timer, TraceRecorder


class MCPGateway:
    """DB Agent'ın MCP protokol ayrıntılarını tek noktada toplar."""

    allowed_tools = {"list_products", "search_product", "get_product_stock"}

    def __init__(self, url: str, trace: TraceRecorder) -> None:
        self.url = url
        self.trace = trace

    async def list_openai_tools(self) -> list[dict[str, Any]]:
        with Timer() as timer:
            async with Client(self.url) as client:
                result = await client.list_tools()
        self.trace.add(
            "mcp.tools.listed",
            "MCP sunucusunun izinli araçları alındı.",
            {"tool_count": len(result.tools), "duration_ms": timer.elapsed_ms},
        )
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in result.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self.allowed_tools:
            raise ValueError(f"İzin verilmeyen MCP aracı: {name}")

        # UI'da yalnızca bu iki zararsız argüman gösterilir; ileride hassas araçlar
        # eklenirse burada açık bir temizleme politikası uygulanmalıdır.
        safe_arguments = {
            key: value
            for key, value in arguments.items()
            if key in {"query", "product_id"}
        }
        self.trace.add(
            "mcp.tool.started",
            f"{name} aracı çağrılıyor.",
            {"tool": name, "arguments": safe_arguments},
        )
        with Timer() as timer:
            async with Client(self.url) as client:
                result = await client.call_tool(name, arguments)

        if result.is_error:
            raise RuntimeError(f"MCP aracı hata döndürdü: {name}")

        data = result.structured_content or {}
        self.trace.add(
            "mcp.tool.completed",
            f"{name} aracı başarıyla tamamlandı.",
            {"tool": name, "duration_ms": timer.elapsed_ms},
        )
        return data
