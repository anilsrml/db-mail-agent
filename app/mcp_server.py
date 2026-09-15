import logging

import psycopg
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from psycopg.rows import dict_row

from app.models import Product, ProductSearchResult, ProductStockResult
from app.settings import get_settings
from app.tracing import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("mcp-server")

mcp = MCPServer(
    "product-stock-mcp",
    version="0.1.0",
    instructions=(
        "Ürün kataloğunu ve stok miktarını salt-okunur PostgreSQL sorgularıyla sunar. "
        "Önce search_product, ardından get_product_stock kullanın."
    ),
)


async def _fetch_all(query: str, params: tuple[object, ...] = ()) -> list[dict]:
    """Her araç çağrısında kısa ömürlü salt-okunur bağlantı açar.

    Küçük eğitim demosunda bağlantı havuzu yerine bu açık yaklaşım tercih edildi.
    Sorgular sabittir ve müşteri verisi yalnızca parametre olarak geçirilir.
    """

    async with await psycopg.AsyncConnection.connect(settings.postgres_dsn) as connection:
        async with connection.cursor(row_factory=dict_row) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchall()


@mcp.tool()
async def list_products() -> ProductSearchResult:
    """Demo kataloğundaki bütün ürünleri listeler."""

    logger.info('{"component":"mcp-server","event":"list_products"}')
    rows = await _fetch_all(
        "SELECT id, name, stock_quantity FROM products ORDER BY id"
    )
    return ProductSearchResult(products=[Product.model_validate(row) for row in rows])


@mcp.tool()
async def search_product(query: str) -> ProductSearchResult:
    """Ürün adı içinde geçen güvenli bir metinle katalogda arama yapar."""

    clean_query = query.strip()
    logger.info(
        '{"component":"mcp-server","event":"search_product","query_length":%d}',
        len(clean_query),
    )
    rows = await _fetch_all(
        """
        SELECT id, name, stock_quantity
        FROM products
        WHERE name ILIKE %s
        ORDER BY id
        LIMIT 10
        """,
        (f"%{clean_query}%",),
    )
    return ProductSearchResult(products=[Product.model_validate(row) for row in rows])


@mcp.tool()
async def get_product_stock(product_id: str) -> ProductStockResult:
    """Ürün koduna göre güncel stok miktarını getirir."""

    logger.info(
        '{"component":"mcp-server","event":"get_product_stock","product_id":"%s"}',
        product_id,
    )
    rows = await _fetch_all(
        """
        SELECT id, name, stock_quantity
        FROM products
        WHERE id = %s
        LIMIT 1
        """,
        (product_id,),
    )
    if not rows:
        return ProductStockResult(found=False)
    return ProductStockResult(found=True, product=Product.model_validate(rows[0]))


# MCP SDK kendi Streamable HTTP ASGI uygulamasını üretir. Uvicorn bu nesneyi
# doğrudan servis eder ve DB Agent /mcp adresine standart MCP istemcisiyle bağlanır.
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "mcp-server",
        "mcp-server:*",
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
    ],
    allowed_origins=[],
)
app = mcp.streamable_http_app(
    json_response=True,
    transport_security=transport_security,
)
