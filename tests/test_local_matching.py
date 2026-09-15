from app.db_agent_core import _match_score, _normalize


def test_turkish_product_suffix_can_match() -> None:
    message = _normalize("Mekanik klavyeniz var mı?")
    product = _normalize("Mekanik Klavye")

    assert _match_score(message, product) > 0


def test_unrelated_request_does_not_match() -> None:
    message = _normalize("Bir kahve makinesi istiyorum")
    product = _normalize("Kablosuz Kulaklık")

    assert _match_score(message, product) == 0

