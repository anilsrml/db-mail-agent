# DB–Telegram Agent

## Sistem

Bu proje, doğal dilde gelen müşteri talebindeki ürünü OpenRouter destekli DB Agent ile belirler ve stok bilgisini özel PostgreSQL MCP araçları üzerinden salt okunur olarak sorgular. Ürün stokta varsa sonucu müşteriye döndürür; stok `0` ise ayrıca Telegram Agent'a yapılandırılmış bir olay göndererek dahili Telegram bildirimi oluşturur.

Web arayüzü, DB Agent, Telegram Agent, MCP sunucusu ve PostgreSQL ayrı servisler olarak çalışır. Agent istekleri, araç çağrıları ve karar özetleri aynı `request_id` üzerinden izlenebilir.

## Docker ile çalıştırma

Proje klasöründe `.env` dosyası oluşturun:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-oss-120b:exacto
OPENROUTER_REASONING_EFFORT=low
LLM_DRY_RUN=true

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_DRY_RUN=true

POSTGRES_DB=stock_demo
POSTGRES_USER=stock_admin
POSTGRES_PASSWORD=change-me-admin
POSTGRES_READER_PASSWORD=change-me-reader
POSTGRES_DSN=postgresql://stock_reader:change-me-reader@postgres:5432/stock_demo

MCP_SERVER_URL=http://mcp-server:8003/mcp
DB_AGENT_URL=http://db-agent:8001
TELEGRAM_AGENT_URL=http://telegram-agent:8002
HTTP_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

Servisleri oluşturup arka planda başlatın:

```powershell
docker compose up --build -d
```

Uygulamayı `http://localhost:8000` adresinden açın.

Servisleri durdurmak için:

```powershell
docker compose down
```
