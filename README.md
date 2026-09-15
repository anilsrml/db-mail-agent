# DB–Telegram Agent Eğitim Projesi

Bu proje, doğal dilde gelen bir müşteri talebini PostgreSQL stok verisiyle değerlendiren ve yalnızca stok `0` olduğunda ikinci bir agent üzerinden Telegram uyarısı gönderen küçük bir eğitim simülasyonudur.

## Ne öğretiyor?

- Bir LLM agent'ın araç seçme döngüsünü
- Python ile özel bir MCP sunucusu geliştirmeyi
- MCP istemcisi ile PostgreSQL arasındaki güvenli sınırı
- İki FastAPI agent'ın HTTP + JSON/Pydantic ile haberleşmesini
- Deterministik iş kuralını LLM kararından ayırmayı
- Agent, MCP ve Telegram adımlarını aynı `request_id` ile izlemeyi

## İki temel senaryo

### Kablosuz Kulaklık — stok 100

```text
Müşteri talebi
  → DB Agent
  → OpenRouter ürün yorumlama
  → PostgreSQL MCP aracı
  → stok 100 / IN_STOCK
  → müşteriye yanıt
```

Bu dalda Telegram Agent çağrılmaz.

### Mekanik Klavye — stok 0

```text
Müşteri talebi
  → DB Agent
  → OpenRouter ürün yorumlama
  → PostgreSQL MCP aracı
  → stok 0 / OUT_OF_STOCK
  → Telegram Agent'a HTTP olayı
  → OpenRouter ile uyarı metni
  → size Telegram mesajı
```

## Mimari

| Bileşen | Port | Sorumluluk |
|---|---:|---|
| Web | 8000 | Demo ekranını sunar ve müşteri talebini DB Agent'a iletir. |
| DB Agent | 8001 | Talebi yorumlar, MCP araçlarını çağırır ve stok kararını verir. |
| Telegram Agent | 8002 | `OUT_OF_STOCK` olayını Telegram uyarısına dönüştürür. |
| MCP Server | 8003 | Güvenli ürün/stok araçlarını PostgreSQL üzerinde çalıştırır. |
| PostgreSQL | 5433 (host) / 5432 (Docker ağı) | İki sabit demo ürününü saklar. |

Daha ayrıntılı açıklama için [mimari dokümanına](docs/ARCHITECTURE.md) ve [kod rehberine](docs/CODE_WALKTHROUGH.md) bakın.

## Neden MCP ve agent HTTP çağrısı farklı?

DB Agent → MCP Server iletişimi bir **agent–tool** ilişkisidir. MCP; aracın adını, girdi şemasını ve yapılandırılmış sonucunu standartlaştırır. Agent, modelin seçtiği aracı MCP istemcisiyle çağırır.

DB Agent → Telegram Agent iletişimi ise sadeleştirilmiş bir **agent–agent** ilişkisidir. İlk sürümde resmi A2A protokolü yerine HTTP ve Pydantic ile doğrulanan `OUT_OF_STOCK` olayı kullanılır. Böylece iki kavram kodda birbirine karışmaz.

## Kurulum

Gerekenler:

- Docker Desktop ve Docker Compose
- Bir OpenRouter API anahtarı (ilk deneme için zorunlu değil)
- Gerçek bildirim için Telegram bot token'ı ve chat ID (ilk deneme için zorunlu değil)

PowerShell'de örnek ayar dosyasını oluşturun:

```powershell
Copy-Item .env.example .env
```

İlk çalıştırmada `.env` içindeki iki PostgreSQL parolasını değiştirin. Ardından:

```powershell
docker compose up --build
```

Tarayıcıda `http://localhost:8000` adresini açın.

## Günlük çalıştırma

İlk kurulum tamamlandıktan sonra sistemi her açışınızda proje klasöründe şu
komut yeterlidir:

```powershell
docker compose up -d
```

Ardından `http://localhost:8000` adresine gidin. Sayfada iki örnek istek
deneyebilirsiniz:

- `Kablosuz kulaklık istiyorum` → stok `100`, Telegram Agent çağrılmaz.
- `Mekanik klavye istiyorum` → stok `0`, Telegram Agent çağrılır.

Servislerin durumunu ve agent haberleşmesini terminalden izlemek için:

```powershell
docker compose ps
docker compose logs -f
```

Log takibinden çıkmak için `Ctrl+C` kullanabilirsiniz; servisler çalışmaya
devam eder. Sistemi durdurmak için:

```powershell
docker compose down
```

Bu komut veritabanı volume'ünü silmez; sonraki açılışta demo verileri korunur.

### PostgreSQL için iki farklı adres

Port eşlemesi nedeniyle bağlantı adresi, bağlantıyı kimin kurduğuna göre
değişir:

- Docker servisleri (MCP Server): `postgres:5432`
- Windows üzerindeki pgAdmin/DBeaver: `127.0.0.1:5433`

Bu nedenle `.env` içindeki `POSTGRES_DSN` mutlaka Docker içi adresi
`postgres:5432` kullanmalıdır. `127.0.0.1:5433` yalnızca Windows'taki harici
istemciler içindir; bir konteyner içinde `127.0.0.1` o konteynerin kendisini
ifade eder.

pgAdmin veya DBeaver ile bağlanmak için host `127.0.0.1`, port `5433`,
veritabanı `stock_demo` ve kullanıcı `stock_admin` değerlerini kullanın.

Demo tablosunu ve iki ürünü terminalden yeniden oluşturmak/doldurmak için:

```powershell
docker compose exec -T postgres psql -U stock_admin -d stock_demo -f /workspace/db/seed.sql
```

Bu seed dosyası tekrar çalıştırılabilir; aynı ürünleri çoğaltmaz.

## Önce dry-run ile deneyin

Örnek ayarlarda şu iki değer açıktır:

```env
LLM_DRY_RUN=true
TELEGRAM_DRY_RUN=true
```

Bu modda OpenRouter yerine basit yerel ürün eşleştiricisi, Telegram yerine de simüle edilmiş gönderim kullanılır. MCP ve PostgreSQL gerçekten çalışır; agent akışı web ekranında görünür. Böylece API anahtarları olmadan önce mimariyi doğrulayabilirsiniz.

## OpenRouter'ı açma

`.env` dosyasını düzenleyin:

```env
OPENROUTER_API_KEY=buraya-openrouter-anahtari
OPENROUTER_MODEL=openai/gpt-oss-120b:exacto
OPENROUTER_REASONING_EFFORT=low
LLM_DRY_RUN=false
```

Anahtarı kod içine veya loglara yazmayın. Ayar değişikliğinden sonra servisleri yeniden başlatın.

## Telegram'ı açma

1. Telegram'da BotFather üzerinden bir bot oluşturun.
2. Botunuza özel sohbetten `/start` mesajı gönderin.
3. Bot API'nin `getUpdates` yanıtından kendi `chat_id` değerinizi bulun.
4. `.env` dosyasına yalnızca yerel olarak ekleyin:

```env
TELEGRAM_BOT_TOKEN=buraya-bot-tokeni
TELEGRAM_CHAT_ID=buraya-chat-id
TELEGRAM_DRY_RUN=false
```

`.env` Git tarafından yok sayılır. Token'ı ekran görüntülerinde, terminal geçmişinde veya hata raporlarında paylaşmayın.

## Gözlemlenebilirlik ve reasoning

Web arayüzü ham düşünce zincirini göstermez. Bunun yerine şu denetlenebilir bilgileri gösterir:

- Model isteğinin başladığı ve tamamlandığı an
- Seçilen MCP aracı ve temizlenmiş argümanları
- MCP çağrısının süresi
- Ürün eşleşmesi ve stok karar özeti
- DB Agent → Telegram Agent HTTP geçişi
- Telegram'ın gerçek veya dry-run gönderim sonucu
- Sağlayıcı döndürüyorsa reasoning token sayısı

Terminalde bütün servislerin JSON loglarını birlikte görmek için:

```powershell
docker compose logs -f
```

## Testler

Konteyner içindeki saf Python testlerini çalıştırmak için:

```powershell
docker compose run --rm web python -m pytest
```

Testler stok `100`, stok `0`, ürün bulunamaması, yerel ürün eşleştirme ve Telegram fallback metnini kapsar.

## Veritabanı güvenliği

MCP Server `stock_reader` kullanıcısıyla bağlanır. Bu kullanıcı yalnızca `products` tablosunda `SELECT` yetkisine sahiptir. MCP araçlarında ham SQL girişi yoktur; sorgular kodda sabittir ve müşteri girdileri parametre olarak geçirilir.

Demo verisini baştan oluşturmak gerekirse konteynerleri durdurup PostgreSQL volume'ünü ayrıca kaldırabilirsiniz. Bu işlem yerel veritabanı verisini siler; yalnızca demo verisini sıfırlamak istediğinizde yapılmalıdır.
