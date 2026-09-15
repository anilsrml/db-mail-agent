from app.domain import decide_stock_status
from app.models import Product, StockStatus


def test_stock_100_is_in_stock() -> None:
    product = Product(id="P-1001", name="Kablosuz Kulaklık", stock_quantity=100)

    assert decide_stock_status(product) == StockStatus.IN_STOCK


def test_stock_zero_is_out_of_stock() -> None:
    product = Product(id="P-1002", name="Mekanik Klavye", stock_quantity=0)

    assert decide_stock_status(product) == StockStatus.OUT_OF_STOCK


def test_missing_product_has_separate_status() -> None:
    assert decide_stock_status(None) == StockStatus.PRODUCT_NOT_FOUND

