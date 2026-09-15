# Mimari ve veri akışı

## Bileşen sınırları

```text
┌────────────┐       HTTP        ┌────────────┐
│ Web Paneli │ ────────────────→ │  DB Agent  │
└────────────┘                   └─────┬──────┘
                                      │ MCP / Streamable HTTP
                                ┌─────▼──────┐      read-only SQL
                                │ MCP Server │ ─────────────────→ PostgreSQL
                                └────────────┘

Stok yalnızca 0 ise:

┌────────────┐   HTTP + OutOfStockEvent   ┌────────────────┐
│  DB Agent  │ ─────────────────────────→ │ Telegram Agent │ ──→ Telegram API
└────────────┘                            └────────────────┘
```

Web, DB Agent ve Telegram Agent ayrı süreçlerdir. MCP Server da standart MCP Streamable HTTP taşıması üzerinden ayrı çalışır. Docker Compose servis adları yerel DNS adları olarak kullanılır.

## Neden stok kararı Python kodunda?

Model müşteri cümlesinden ürünün hangisi olduğunu yorumlar ve doğru aracı seçer. Fakat `0 → OUT_OF_STOCK` kuralı yoruma açık değildir. Bu nedenle `app/domain.py` içindeki saf Python fonksiyonu kararı verir.

Bu ayrım üç yarar sağlar:

1. Aynı stok değeri her zaman aynı sonucu üretir.
2. Kural API maliyeti olmadan test edilir.
3. Model yanlış açıklama üretse bile Telegram dalı veri tabanındaki gerçek sayıya göre seçilir.

## MCP araç yüzeyi

MCP Server üç araç sunar:

- `list_products`: Web kataloğu ve dry-run eşleştirme için bütün demo ürünlerini döndürür.
- `search_product(query)`: Modelin çıkardığı kısa ürün adıyla arama yapar.
- `get_product_stock(product_id)`: Seçilen ürünün güncel stok miktarını getirir.

Genel bir `execute_sql` aracının bulunmaması bilinçli bir güvenlik kararıdır. Model yalnızca önceden belirlenmiş iş yeteneklerini çağırabilir.

## Basitleştirilmiş A2A mesajı

DB Agent stoğu `0` bulduğunda `OutOfStockEvent` üretir. Mesaj; olay kimliği, istek kimliği, ürün kimliği, ürün adı, stok miktarı ve zamanı içerir. Telegram Agent bu Pydantic şemasına uymayan istekleri FastAPI doğrulamasıyla reddeder.

Bu ilk sürüm resmi A2A protokolünü uygulamaz. Ama önemli A2A ilkelerini korur:

- Agent'ların ayrı sorumlulukları vardır.
- Mesaj sözleşmesi açık ve makinece doğrulanabilirdir.
- Gönderen ve alan bağımsız HTTP servisleridir.
- `request_id` ve `event_id` ile çağrı izlenebilir.

## Hata davranışı

- Ürün bulunamazsa müşteriye açıklayıcı yanıt verilir ve Telegram çağrılmaz.
- OpenRouter kapalıysa geliştirme eşleştiricisi kullanılabilir.
- Telegram Agent'taki LLM hata verirse sabit uyarı şablonu kullanılır.
- Telegram gönderimi hata verirse stok sonucu değişmez; hata iz kaydında görünür.
- MCP veya DB erişimi hata verirse müşteri genel bir servis hatası görür, hassas hata ayrıntısı UI'a taşınmaz.

