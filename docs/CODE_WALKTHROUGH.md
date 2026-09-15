# Önemli kod parçaları

Bu rehber kodu dosya sırasıyla değil, bir müşteri talebinin izlediği sırayla açıklar.

## 1. Ortak mesaj modelleri — `app/models.py`

`CustomerRequest`, `CustomerResponse` ve `OutOfStockEvent` Pydantic modelleridir. FastAPI bu modeller sayesinde gelen JSON'u agent çalışmadan önce doğrular. `request_id` bütün akışı; `event_id` ise yalnızca agent'lar arası stok olayını tanımlar.

Bu modeller agent'lar arasında serbest metin yerine açık bir sözleşme oluşturur. Telegram Agent ürün kimliğini bir müşteri cümlesinden yeniden çıkarmaya çalışmaz; DB Agent'ın doğruladığı alanları alır.

## 2. İş kuralı — `app/domain.py`

`decide_stock_status` bir LLM fonksiyonu değildir. Girdisi `Product | None`, çıktısı `StockStatus` değeridir:

```python
if product is None:
    return StockStatus.PRODUCT_NOT_FOUND
if product.stock_quantity == 0:
    return StockStatus.OUT_OF_STOCK
return StockStatus.IN_STOCK
```

Bu küçük parça projenin en önemli tasarım kararlarından biridir: doğal dili model yorumlar, kesin stok kuralını kod uygular.

## 3. MCP Server — `app/mcp_server.py`

`MCPServer` resmi Python SDK'nın yüksek seviyeli sunucu sınıfıdır. `@mcp.tool()` dekoratörü fonksiyonun Python tiplerinden MCP girdi/çıktı şeması üretir.

Her araç sabit ve parametreli SQL kullanır. Örneğin ürün kodu SQL metnine eklenmez; `%s` parametresinden gönderilir. Veritabanı bağlantısı `stock_reader` kullanıcısıyla açıldığı için kodda bir hata olsa bile yazma yetkisi bulunmaz.

`mcp.streamable_http_app()` standart MCP HTTP uç noktasını üretir. DB Agent bu servise normal bir REST endpoint'i gibi özel JSON uydurarak değil, MCP istemcisiyle bağlanır.

MCP SDK'nın DNS-rebinding korumasında Docker servis adı `mcp-server` açıkça izin listesine eklenir. Koruma tamamen kapatılmadığı için beklenmeyen `Host` başlıkları MCP endpoint'ine ulaşamaz.

## 4. MCP istemcisi — `app/mcp_gateway.py`

`MCPGateway` iki işi yapar:

1. MCP araç şemalarını alıp OpenRouter'ın anlayacağı function-tool şekline dönüştürür.
2. Modelin seçtiği aracı MCP protokolüyle çağırıp yapılandırılmış sonucu döndürür.

Araç başlamadan ve tamamlandıktan sonra iz olayı üretildiği için web ekranında model ile veritabanı arasındaki sınır görünür olur.

## 5. Açık agent döngüsü — `app/db_agent_core.py`

Bu projede LangChain gibi bir çatı kullanılmadığından temel döngü doğrudan görülebilir:

1. MCP sunucusundan araç şemaları alınır.
2. Müşteri mesajı, sistem talimatı ve araçlar OpenRouter'a gönderilir.
3. Model bir tool call üretirse argümanlar ayrıştırılır.
4. Araç MCP üzerinden çalıştırılır.
5. Araç sonucu `tool` mesajı olarak modele geri verilir.
6. `get_product_stock` sonucu geldiğinde döngü sonlandırılır ve deterministik kurala geçilir.

Döngü dört turla sınırlıdır. Böylece hatalı bir modelin sürekli araç çağırması maliyet ve gecikme üretmez.

## 6. Koşullu agent haberleşmesi — `app/db_agent.py`

`IN_STOCK` dalı doğrudan müşteriye döner. `OUT_OF_STOCK` dalı ise `OutOfStockEvent` oluşturup Telegram Agent'ın endpoint'ine HTTP POST yapar.

Bu koşulu web arayüzü değil DB Agent uygular. Böylece başka bir istemci ileride DB Agent'ı çağırsa da iş kuralı korunur.

## 7. Telegram fallback — `app/telegram_agent.py`

Telegram Agent önce OpenRouter ile kısa bir uyarı yazmayı dener. LLM çağrısı başarısızsa `fallback_message` aynı zorunlu alanları içeren sabit bir metin üretir. Bildirim gibi kritik bir yan etkinin yalnızca modele bağımlı olmaması bu desenin amacıdır.

`TELEGRAM_DRY_RUN=true` iken gerçek API çağrısı yapılmaz. Üretilen metin ve bütün iz kayıtları yine DB Agent'a döner.

## 8. Loglar — `app/tracing.py`

`TraceRecorder.add` aynı olayı hem Python loguna JSON olarak yazar hem de müşteri yanıtındaki `trace` listesine ekler. UI bu listeyi sırasıyla gösterir.

Ham düşünce zinciri yerine `agent.decision`, araç adı, güvenli argümanlar, çağrı süresi ve token sayıları tutulur. Bu bilgiler davranışı açıklamak için yeterlidir ve gizli reasoning içeriğine bağımlı değildir.
