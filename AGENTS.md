# DB–Telegram Agent Eğitim Projesi

## Projenin amacı

Bu proje, bir müşteri talebindeki ürünün stok durumunu PostgreSQL üzerinden kontrol eden iki agent'lı, eğitim amaçlı bir sistemdir. İlk sürüm özellikle agent sorumluluklarının ayrılmasını, araç kullanımını ve agent'lar arasındaki mesaj akışının gözlemlenmesini öğretmelidir.

Temel akış:

```text
Müşteri talebi
    -> DB Agent
    -> PostgreSQL MCP Server
    -> stok kontrolü
    -> agent mesajı
    -> Telegram Agent
    -> Telegram bildirimi
```

Telegram bu akışta müşteri iletişim kanalı değildir. Stok tükendiğinde proje sahibine veya dahili stok sorumlularına operasyonel uyarı göndermek için kullanılır.

## Kesinleşen teknik kararlar

- Uygulama dili Python olacaktır.
- LLM modellerine OpenRouter üzerinden erişilecektir.
- İlk sürümün varsayılan modeli `openai/gpt-oss-120b:exacto` olacaktır.
- Reasoning seviyesi, kısa ürün eşleştirme ve araç seçimi için varsayılan olarak `low` tutulacaktır.
- Model kimliği ve reasoning seviyesi `.env` üzerinden değiştirilebilir olacak; kod içine sabitlenmeyecektir.
- `deepseek/deepseek-v4-flash-0731` karşılaştırma ve yedek model adayı olarak kullanılabilecektir.
- Veritabanı PostgreSQL olacaktır.
- Geliştirme ortamı Docker ve Docker Compose kullanabilecektir.
- Eğitim aşamasındaki varsayılan PostgreSQL kurulumu, Docker Compose içinde yerel bir PostgreSQL konteyneridir.
- PostgreSQL verilerine DB Agent doğrudan bağlantı kurmak yerine bir PostgreSQL MCP sunucusu üzerinden erişecektir.
- PostgreSQL MCP sunucusu eğitim amacıyla Python kullanılarak bu proje içinde geliştirilecektir.
- MCP sunucusu genel amaçlı sınırsız SQL çalıştırmak yerine yalnızca açıkça tanımlanmış, salt-okunur ürün ve stok araçları sunacaktır.
- DB Agent ilk sürümde yalnızca okuma işlemleri yapacaktır.
- Stok durumu yalnızca stok miktarı `0` olduğunda `OUT_OF_STOCK` kabul edilecektir.
- Eğitim simülasyonunda iki sabit örnek ürün bulunacaktır: ürünlerden birinin stoğu `100`, diğerinin stoğu `0` olacaktır.
- Bildirim kanalı Telegram olacaktır.
- Telegram bildirimini müşteri değil, proje sahibi veya dahili stok sorumlusu alacaktır.
- İlk sürümde resmi/eksiksiz bir A2A protokol uygulaması zorunlu değildir. İki ayrı agent'ın açık bir mesaj sözleşmesiyle haberleştiği sade ve öğretici bir yaklaşım kullanılacaktır.
- DB Agent ve Telegram Agent iki ayrı FastAPI servisi olarak çalışacaktır.
- Agent'lar HTTP üzerinden JSON mesajlarıyla haberleşecek, mesaj modelleri Pydantic ile doğrulanacaktır.
- Agent'lar arasındaki istek, yanıt ve hata akışı loglardan izlenebilir olacaktır.
- Müşteri talebi, örnek ürünler, sonuç ve agent logları tek sayfalık basit bir web arayüzünde gösterilecektir.
- Stok `100` olduğunda DB Agent sorgu sonucunu müşteriye döndürür ve Telegram Agent ile haberleşme başlatılmaz.
- Stok `0` olduğunda DB Agent müşteriye stokta yok sonucunu döndürür, Telegram Agent'a `OUT_OF_STOCK` mesajı gönderir ve proje sahibine Telegram uyarısı iletilir.
- İlk sürüm stok yenileme, otomatik artırma veya gerçek üretim stok süreçlerini modellemeyecektir.
- Kod içinde önemli noktaları açıklayan, orta ayrıntıda Türkçe yorumlar bulunacaktır. Yorumlar kodun ne yaptığını tekrar etmek yerine kararın nedenini ve veri akışındaki rolünü açıklamalıdır.
- İlk sürümde kapsamlı bir agent çatısı kullanılmayacaktır. Agent döngüsü FastAPI, OpenAI uyumlu Python istemcisi, resmi MCP Python SDK, Pydantic ve HTTPX ile açık biçimde geliştirilecektir.

## PostgreSQL ortamı kararı

İlk geliştirme ve eğitim ortamında PostgreSQL, Docker Compose ile yerel olarak çalıştırılmalıdır. Bunun nedenleri:

- Her geliştirici aynı PostgreSQL sürümünü ve başlangıç şemasını çalıştırabilir.
- Veritabanı, MCP sunucusu ve Python servisleri birlikte başlatılabilir.
- Bulut hesabı, bağlantı ücreti ve internet bağlantısı gerekmez.
- Veritabanını sıfırlama, örnek veri yükleme ve sorguları inceleme eğitim sırasında kolaydır.
- Daha sonra bağlantı adresi ve gizli bilgiler değiştirilerek yönetilen bir PostgreSQL servisine geçilebilir.

Üretim benzeri yayınlama ihtiyacı doğana kadar Supabase, Neon, Railway, AWS RDS gibi yönetilen servisler zorunlu değildir. Yerel PostgreSQL parolası ve bağlantı bilgileri bile kaynak koduna yazılmamalı, `.env` üzerinden alınmalıdır.

## Agent sorumlulukları

### DB Agent

- Müşteri talebinden ürün adı/kodu gibi sorgu için gerekli alanları alır.
- PostgreSQL MCP aracını kullanarak ürün ve stok bilgisini yalnızca okur.
- Serbest metin yerine tanımlı bir sonuç modeli üretir.
- Stok `0` ise `OUT_OF_STOCK`, sıfırdan büyükse `IN_STOCK` sonucu verir.
- Ürün bulunamadığında bunu stokta yokmuş gibi varsaymaz; ayrı bir `PRODUCT_NOT_FOUND` sonucu üretir.
- Bildirimi doğrudan Telegram'a göndermez. Sonucu Telegram Agent'a iletir.

### Telegram Agent

- DB Agent tarafından gönderilen yapılandırılmış mesajı kabul eder.
- Yalnızca bildirim gerektiren olaylarda OpenRouter modelini kullanarak kısa ve anlaşılır bir Türkçe Telegram mesajı oluşturur.
- Model çağrısı başarısız olur veya geçersiz çıktı üretirse sabit ve güvenilir bir Türkçe mesaj şablonuna geri döner.
- Telegram Bot API çağrısını gerçekleştirir.
- Gönderim sonucunu başarı veya hata olarak kaydeder.
- Veritabanını doğrudan sorgulamaz.

### Demo web arayüzü

- Tek sayfalık, eğitim amaçlı ve sade bir kontrol paneli olacaktır.
- Veritabanındaki iki örnek ürünü ve başlangıç stoklarını gösterecektir.
- Müşteri talebinin yazılacağı bir metin alanı ve `Talebi Gönder` düğmesi bulunacaktır.
- Müşteri iki örnek üründen istediğini doğal dille talep edebilecektir.
- Müşteriye verilecek sonuç aynı sayfada gösterilecektir.
- DB Agent ve Telegram Agent arasındaki akışı izlemek için `request_id`, agent adı, olay ve zaman bilgilerini içeren okunabilir bir log bölümü bulunacaktır.
- İlk sürüm için ağır bir ön yüz çatısı zorunlu değildir; FastAPI ile sunulan HTML, CSS ve az miktarda JavaScript yeterlidir.

### Örnek başlangıç verileri

- `P-1001 — Kablosuz Kulaklık — stok: 100`
- `P-1002 — Mekanik Klavye — stok: 0`

Bu veriler PostgreSQL başlatılırken seed dosyasıyla oluşturulur. Uygulama çalışma sırasında stok güncellemez.

## Simülasyon senaryoları

### Senaryo A — stok 100

1. Müşteri stok miktarı `100` olan Kablosuz Kulaklık için talep gönderir.
2. DB Agent, PostgreSQL MCP aracıyla stok miktarını okur.
3. DB Agent müşteriye ürünün stokta olduğu sonucunu döndürür.
4. Telegram Agent çağrılmaz ve Telegram bildirimi gönderilmez.

### Senaryo B — stok 0

1. Müşteri stok miktarı `0` olan Mekanik Klavye için talep gönderir.
2. DB Agent, PostgreSQL MCP aracıyla stok miktarını okur.
3. DB Agent müşteriye ürünün stokta olmadığı sonucunu döndürür.
4. DB Agent, Telegram Agent'a HTTP üzerinden doğrulanmış bir `OUT_OF_STOCK` mesajı gönderir.
5. Telegram Agent proje sahibine veya dahili sorumluya Telegram uyarısı gönderir.

Bu iki senaryo sabit başlangıç verileriyle tekrar tekrar çalıştırılabilir. Sistem stok miktarını değiştirmez ve bir üretim stok yönetimi sürecini taklit etmeye çalışmaz.

## Agent mesaj sözleşmesi

İlk sürümde agent iletişimi iki ayrı FastAPI servisi arasında HTTP çağrısıyla yapılacaktır. Mesaj içeriği yapılandırılmış olmalıdır. Örnek alanlar:

```json
{
  "event_id": "benzersiz-kimlik",
  "event_type": "OUT_OF_STOCK",
  "product_id": "P-1001",
  "product_name": "Örnek Ürün",
  "stock_quantity": 0,
  "request_id": "müşteri-talebi-kimliği",
  "occurred_at": "ISO-8601 tarih-saat"
}
```

Mesaj şeması Pydantic modeliyle doğrulanmalıdır. Agent'lar arası aktarımda yalnızca doğal dil kullanmak yerine makinece doğrulanabilir alanlar kullanılmalıdır.

## Loglama ve gözlemlenebilirlik

Loglar en az şu olayları göstermelidir:

- Müşteri talebinin alınması
- DB Agent'ın çalışmaya başlaması
- MCP sorgusunun başlatılması ve tamamlanması
- Sorgu sonucundan verilen stok kararı
- DB Agent'ın Telegram Agent'a mesaj göndermesi
- Telegram Agent'ın mesajı alması
- Telegram API gönderim sonucu
- Doğrulama, bağlantı ve araç hataları
- Agent'ın kullanıcıya gösterilebilir kısa karar özeti

Tüm ilgili loglarda aynı `request_id` ve agent mesajında aynı `event_id` kullanılmalıdır. Parolalar, OpenRouter API anahtarı, Telegram bot token'ı, kişisel müşteri verileri ve tam veritabanı bağlantı adresi loglanmamalıdır. Logların terminalde kolay okunması, ileride ise JSON biçiminde toplanabilmesi hedeflenmelidir.

### Reasoning ve karar görünürlüğü

- Eğitim arayüzü agent'ın ham/gizli düşünce zincirini göstermeye veya kalıcı olarak saklamaya çalışmayacaktır.
- Bunun yerine her önemli adım için kısa ve denetlenebilir bir `decision_summary` üretilecektir. Örnek: `Talep P-1002 ile eşleşti; stok 0 olduğu için OUT_OF_STOCK olayı oluşturuldu.`
- Araç adı, temizlenmiş araç girdisi, sonuç özeti, süre, durum kodu ve sonraki agent'a gönderilen mesaj ayrı log olayları olarak gösterilecektir.
- OpenRouter/model yanıtında sağlayıcı tarafından güvenli bir reasoning özeti sunulursa geliştirme modunda ayrıca gösterilebilir; ham reasoning metni, şifreli reasoning blokları veya hassas içerik loglanmamalıdır.
- Reasoning özelliğinin modele göre hiç dönmeyebileceği kabul edilmeli; uygulamanın çalışması buna bağlı olmamalıdır.
- Token kullanımı ve varsa reasoning token sayısı maliyet/gözlem metriği olarak kaydedilebilir.

## Güvenlik sınırları

- DB Agent için kullanılan PostgreSQL kullanıcısına yalnızca gerekli tablo veya view'larda `SELECT` yetkisi verilmelidir.
- PostgreSQL MCP sunucusu da aynı salt-okunur kullanıcıyla bağlanmalıdır.
- Modelin ürettiği metin doğrudan SQL olarak güvenilmeden çalıştırılmamalıdır. Mümkün olduğunda izinli araçlar, parametreli sorgular veya sınırlandırılmış sorgu yüzeyi kullanılmalıdır.
- OpenRouter anahtarı, Telegram bot token'ı ve veritabanı parolası `.env` içinde tutulmalı; repoya eklenmemelidir.
- Telegram alıcı kimliği yapılandırmadan gelmeli ve loglarda gereksiz yere gösterilmemelidir.

## Özel PostgreSQL MCP sunucusu

- MCP sunucusu Python ile ayrı bir servis/bileşen olarak geliştirilecektir.
- İlk araç yüzeyi en az `search_product` ve `get_product_stock` araçlarını içerecektir.
- Araç girdileri ve çıktıları açık şemalarla doğrulanacaktır.
- PostgreSQL sorguları parametreli olacak ve yalnızca `SELECT` işlemleri yapacaktır.
- MCP sunucusunun veritabanı kullanıcısı yalnızca gerekli ürün görünümü veya tablosunda okuma yetkisine sahip olacaktır.
- Ham ve model tarafından serbestçe üretilmiş SQL çalıştıran genel bir araç sunulmayacaktır.
- MCP istek başlangıcı, araç adı, süre, sonuç durumu ve `request_id` loglanacaktır; gizli bilgiler ve gereksiz veri satırları loglanmayacaktır.
- README içinde MCP istemcisi, MCP sunucusu ve PostgreSQL arasındaki sınırlar ayrıca açıklanacaktır.

## Eğitim ve kodlama kuralları

- Kod küçük, tek sorumluluklu modüllere ayrılmalıdır.
- Önce açık veri modelleri ve deterministik iş kuralları kurulmalı, LLM yalnızca gerçekten anlamlandırma gereken yerlerde kullanılmalıdır.
- Önemli Python sınıfları, fonksiyonları ve agent geçişleri kısa Türkçe açıklamalar içermelidir.
- Her önemli kod parçası anlatılırken amacı, girdisi, çıktısı ve hata davranışı açıklanmalıdır.
- Stok karar kuralı gibi deterministik mantık LLM prompt'una gizlenmemeli, test edilebilir Python kodunda bulunmalıdır.
- Dış servisler testlerde taklit edilebilmelidir.
- En azından stokta var, stok sıfır, ürün bulunamadı, MCP hatası ve Telegram hatası senaryoları test edilmelidir.
- Eğitim değeri için agent çağrıları ve MCP araç kullanımı gereksiz soyutlamaların arkasına saklanmamalıdır.
- README, sistemi ilk kez agent ve MCP öğrenen bir geliştiricinin takip edebileceği sırada anlatmalıdır.
- Dokümantasyon; müşteri talebinin alınması, LLM ile ürünün belirlenmesi, MCP araç çağrısı, stok kararının verilmesi, agent'lar arası HTTP mesajı ve Telegram gönderimini adım adım açıklamalıdır.
- Agent–agent iletişimi ile agent–tool/MCP iletişimi arasındaki fark açıkça anlatılmalıdır.
- Önemli kod parçaları için yalnızca “ne yaptığı” değil, “neden bu bileşende bulunduğu”, girdisi, çıktısı ve hata davranışı da açıklanmalıdır.
- Kod örnekleri kısa parçalar halinde ele alınmalı; ilgili gerçek dosya ve fonksiyonlara yönlendirme yapılmalıdır.
- Mimari ve senaryo akışları gerektiğinde küçük metin diyagramlarıyla görünür hale getirilmelidir.

## İlk sürümün kapsam dışı konuları

- Stok güncelleme ve sipariş oluşturma
- DB Agent'a `INSERT`, `UPDATE` veya `DELETE` yetkisi verilmesi
- Eksiksiz resmi A2A protokol uyumluluğu
- Çok kiracılı kullanım ve ileri seviye kullanıcı yetkilendirmesi
- Üretim ölçeğinde mesaj kuyruğu, yüksek erişilebilirlik ve otomatik ölçeklendirme
