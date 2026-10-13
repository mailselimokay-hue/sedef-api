# Sedef canlı fiyat ekranı · borsa.sedefkuyumculuk.com

Türkçe konuş. Personelin Harem Altın uygulaması yerine kullanacağı fiyat ekranı.

## Yapı
- `static/index.html` → ekran (tek sayfa, PWA) · `static/sw.js`, `manifest.json`, logolar
- `src/worker.js` → fiyat motoru (`/api/guncel-fiyatlar`) · `functions/api/guncel-fiyatlar.js` Pages için aynı motoru çağırır
- Yayın: Cloudflare Pages projesi **sedef-vitrin** → `npx wrangler pages deploy static --project-name sedef-vitrin --branch main` (bu klasörde)
- Git: `main` dalı; commit'ten sonra push kullanıcının onayıyla

## Fiyat kaynakları (sırayla)
1. **Genç Metal** (ana) — `mobil.gencmetalrafineri.com/service/index.php?islem=cur__prices`
2. **AltinAPI** (yedek, ücretsiz plan, ~500 istek/ay) — yalnızca ana kaynak yanıt vermezse; anahtar Cloudflare gizli değişkeni `ALTINAPI_KEY`. Yedekte en fazla 15 dakikada bir istek (`YEDEK_CACHE_SURESI` = 900 sn · 13.10'dan beri, ana kaynağın sertifikası dolduğu için; düzelince 30–120 sn'ye geri alınacak). Her kalem son ana fiyattan %3'ten fazla saparsa reddedilir.
3. İkisi de yoksa son fiyat **"Gecikmeli · teyit etmeden işlem yapmayın"** uyarısıyla gösterilir.

## Değişmez kurallar
- **Uydurma fiyat yok.** Kaynak yoksa ekran açıkça uyarır.
- Fiyatlar **Harem Altın ile birebir aynı** kalır (ek indirim/marj yok); günlük değişim yüzdesi de Harem'le uyumlu.
- **Gram altın alış = has alış × 0,995** (995 milyem); has altında milyem düşülmez.
- **Tedarikçi adı ekranda/yanıtta asla görünmez.**
- 24 ve 22 ayar gösterilir; eski ziynet de satılır.
- Ücretsiz hesaplarla kalınır (Cloudflare ücretsiz plan).

## Bilinenler
- DNS IdeaSoft'ta (ns1/ns2.myideasoft.com). IdeaSoft paneline CNAME eklemek **tüm zonu SERVFAIL'e düşürdü** (11 ve 12 Ekim 2026). Panele kayıt eklemeden önce kullanıcıyla konuş; IdeaSoft destek kaydı #308277.
- `*.pages.dev` bazı Türk internet sağlayıcılarında kesiliyor (TLS reset); kalıcı adres borsa.sedefkuyumculuk.com olmalı.
- `wrangler.jsonc` artık **Pages ayar dosyası** (sedef-vitrin · `pages_build_output_dir` + D1 bağlantısı `CARSI_DB`). Eski Worker (sedef-borsa) ayarı git geçmişinde. Gizli değişken `ALTINAPI_KEY` dosyada değil, Cloudflare'de.

## Çarşı fiyat kaydı (SEDEF SİSTEM kur hesabı için · 13.10.2026)
- `carsi_kayit/` → ayrı **cron Worker** `sedef-carsi-kayit` (Pages Functions cron çalıştırmaz). Yayın: `cd carsi_kayit && npx wrangler deploy`.
- Her 5 dakikada bir, **09:00–20:30 (TR)**, ana kaynaktan ALTIN, GRAMALTIN, AYAR22 ve ziynet/döviz kalemlerinin alış/satışı **D1 `sedef-carsi`** (tablo `ornek`, şema `carsi_kayit/sema.sql`) içine tek satır olarak yazılır (~139 yazma/gün, ücretsiz plan içinde).
- Ana kaynak yanıt vermezse o dakika **atlanır**; yedek kaynak (AltinAPI) bu kayıtta **kullanılmaz**. Son 3 örneğin ortancasından %3'ten fazla oynayan kalem kaydedilmez, `isaretli` sütununa yazılır.
- Okuma: `GET /api/carsi-gunluk?gun=YYYY-MM-DD` (`functions/api/carsi-gunluk.js`, ortak kod `src/carsi.js`) → kalem başına alış/satış ortalama · en düşük · en yüksek · örnek sayısı · ilk/son saat. Tedarikçi adı yanıtta yok (`kaynak: "carsi"`).
- `/api/guncel-fiyatlar` ve vitrin bu kayıttan bağımsızdır.
