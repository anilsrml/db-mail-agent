from app.models import Product, StockStatus


def decide_stock_status(product: Product | None) -> StockStatus:
    """LLM'den bağımsız, test edilebilir stok kuralı.

    Model yalnızca müşterinin hangi ürünü kastettiğini belirlemeye yardım eder.
    Stok kararını modele bırakmamak aynı veri için her zaman aynı sonucu sağlar.
    """

    if product is None:
        return StockStatus.PRODUCT_NOT_FOUND
    if product.stock_quantity == 0:
        return StockStatus.OUT_OF_STOCK
    return StockStatus.IN_STOCK

