import time
import cloudscraper
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn

app = FastAPI(title="Sedef Kuyumculuk - Kapalıçarşı Motoru")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/vitrin", StaticFiles(directory="static"), name="static")


@app.get("/")
def ana_sayfaya_yonlendir():
    return RedirectResponse(url="/vitrin/index.html")


CACHE_SURESI = 10  # saniye · çalışan ekranı için sık yenileme
BAYAT_SURESI = 300  # bu kadar saniye taze veri gelmezse ekran uyarı verir
son_cekilen_veri = None
son_cekim_zamani = 0


def guvenli_float(deger):
    try:
        if isinstance(deger, (int, float)):
            return float(deger)

        deger = str(deger).strip()
        if "," in deger and "." in deger:
            if deger.rfind(",") > deger.rfind("."):
                deger = deger.replace(".", "").replace(",", ".")
            else:
                deger = deger.replace(",", "")
        elif "," in deger:
            deger = deger.replace(",", ".")

        return float(deger)
    except:
        return 0.0


KAYNAK_URL = "https://mobil.gencmetalrafineri.com/service/index.php?islem=cur__prices"


def ana_verileri_cek():
    """Kaynaktaki bütün kalemleri {kod: {alis, satis, kapanis}} olarak döndürür.
    Taze veri gelmezse son geçerli veri; hiç yoksa None (uydurma fiyat yok)."""
    global son_cekilen_veri, son_cekim_zamani
    simdi = time.time()
    if son_cekilen_veri is not None and (simdi - son_cekim_zamani) < CACHE_SURESI:
        return son_cekilen_veri
    try:
        res = cloudscraper.create_scraper().get(KAYNAK_URL, timeout=10)
        res.raise_for_status()
        data = res.json().get("data", {})
        ham = {}
        for kod, item in data.items():
            if isinstance(item, dict):
                ham[kod] = {
                    "alis": guvenli_float(item.get("alis")),
                    "satis": guvenli_float(item.get("satis")),
                    "kapanis": guvenli_float(item.get("kapanis")),
                }
        if ham.get("ALTIN", {}).get("alis", 0) > 0 and ham["ALTIN"]["satis"] > 0:
            son_cekilen_veri, son_cekim_zamani = ham, simdi
    except Exception as e:
        print("Fiyat kaynagi baglanti hatasi:", e)
    return son_cekilen_veri


# ---------------------------------------------------------------------------
# FİYAT STRATEJİSİ: Harem ile birebir aynı fiyat (pazarlık payı saklı kalır).
# Kaynak, ürünlerin hazır fiyatlarını Harem ile aynı veriyor (11.10.2026 kontrol edildi),
# bu yüzden doğrudan kullanılıyor. Tek istisna gram altın alışı: has alışı × 0,995
# (995 milyem, alışta 5 milyem düşülür) · Harem de böyle hesaplıyor.
# Kaynakta bir kalem yoksa has fiyatından Harem oranıyla hesaplanır (yedek).
#   (ekran adı, grup, kaynak kodu, yedek alış katsayısı, yedek satış katsayısı, basamak)
# ---------------------------------------------------------------------------
KALEMLER = [
    ("HAS ALTIN",   "altin", "ALTIN",       1.0,      1.0,       2),
    ("GRAM ALTIN",  "altin", "GRAMALTIN",   0.995,    1.003,     2),
    ("22 AYAR",     "altin", "AYAR22",      0.909698, 0.9369923, 2),
    ("YENİ ÇEYREK", "yeni",  "CEYREK_YENI", 1.63,     1.63476,   0),
    ("YENİ YARIM",  "yeni",  "YARIM_YENI",  3.26,     3.26847,   0),
    ("YENİ TAM",    "yeni",  "TEK_YENI",    6.50306,  6.518,     0),
    ("YENİ ATA",    "yeni",  "ATA_YENI",    6.61994,  6.68307,   0),
    ("ESKİ ÇEYREK", "eski",  "CEYREK_ESKI", 1.60994,  1.61374,   0),
    ("ESKİ YARIM",  "eski",  "YARIM_ESKI",  3.20299,  3.21149,   0),
    ("ESKİ TAM",    "eski",  "TEK_ESKI",    6.41007,  6.42809,   0),
    ("ESKİ ATA",    "eski",  "ATA_ESKI",    6.61298,  6.63299,   0),
    ("Dolar",       "doviz", "USDTRY",      None,     None,      3),
    ("Euro",        "doviz", "EURTRY",      None,     None,      3),
]
GRAM_MILYEM = 0.995


def _degisim(fiyat, kapanis):
    """Günlük değişim yüzdesi · kaynağın kapanış fiyatına göre.
    NOT: kapanış alanının anlamı piyasa açıkken Harem'in yüzdesiyle karşılaştırılıp doğrulanacak."""
    if not kapanis or kapanis <= 0 or not fiyat:
        return None
    return round((fiyat - kapanis) / kapanis * 100, 2)


def matematiksel_motor():
    ham = ana_verileri_cek()
    if ham is None:
        return None
    has = ham["ALTIN"]
    sonuc = {"altin": {}, "yeni": {}, "eski": {}, "doviz": {}}
    for ad, grup, kod, ka, ks, basamak in KALEMLER:
        k = ham.get(kod)
        if k and k["alis"] > 0 and k["satis"] > 0:
            alis, satis, kapanis = k["alis"], k["satis"], k["kapanis"]
        elif ka is not None:
            alis, satis, kapanis = has["alis"] * ka, has["satis"] * ks, has["kapanis"] * ks
        else:
            continue
        k_alis_ham = alis
        if kod == "GRAMALTIN":
            alis = has["alis"] * GRAM_MILYEM
        sonuc[grup][ad] = {
            "alis": round(alis, basamak),
            "satis": round(satis, basamak),
            "degisim": _degisim(alis if kod != "GRAMALTIN" else k_alis_ham, kapanis),
        }
    return sonuc


@app.get("/api/guncel-fiyatlar")
def guncel_fiyatlari_getir():
    kategoriler = matematiksel_motor()
    if kategoriler is None:
        return JSONResponse(status_code=503, content={"magaza": "Sedef Kuyumculuk", "durum": "yok"})
    yas = int(time.time() - son_cekim_zamani)
    return {
        "magaza": "Sedef Kuyumculuk",
        "durum": "bayat" if yas > BAYAT_SURESI else "canli",
        "guncelleme": int(son_cekim_zamani),
        "yas_sn": yas,
        "kategoriler": kategoriler,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
