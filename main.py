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


def ana_verileri_cek():
    global son_cekilen_veri, son_cekim_zamani
    guncel_zaman = time.time()

    if (
        son_cekilen_veri is not None
        and (guncel_zaman - son_cekim_zamani) < CACHE_SURESI
    ):
        return son_cekilen_veri

    ham_veri = {
        "HAS": {"alis": 0.0, "satis": 0.0},
        "USD": {"alis": 0.0, "satis": 0.0},
        "EUR": {"alis": 0.0, "satis": 0.0},
    }

    try:
        scraper = cloudscraper.create_scraper()
        res = scraper.get(
            "https://mobil.gencmetalrafineri.com/service/index.php?islem=cur__prices",
            timeout=10,
        )
        res.raise_for_status()
        veri = res.json()

        if "data" in veri:
            data = veri["data"]

            if "ALTIN" in data:
                ham_veri["HAS"]["alis"] = guvenli_float(data["ALTIN"].get("alis"))
                ham_veri["HAS"]["satis"] = guvenli_float(data["ALTIN"].get("satis"))

            for key, item in data.items():
                if not isinstance(item, dict):
                    continue

                if key in ["USD", "USDTRY", "USDTRL"]:
                    ham_veri["USD"]["alis"] = guvenli_float(item.get("alis"))
                    ham_veri["USD"]["satis"] = guvenli_float(item.get("satis"))
                elif key in ["EUR", "EURTRY", "EURTRL"]:
                    ham_veri["EUR"]["alis"] = guvenli_float(item.get("alis"))
                    ham_veri["EUR"]["satis"] = guvenli_float(item.get("satis"))

        if ham_veri["HAS"]["alis"] > 0:
            son_cekilen_veri = ham_veri
            son_cekim_zamani = guncel_zaman

    except Exception as e:
        print("Fiyat kaynagi baglanti hatasi:", e)

    # Uydurma fiyat yok: taze veri gelmediyse son geçerli veri (yaşıyla birlikte) ya da hiç veri
    if ham_veri["HAS"]["alis"] > 0:
        return ham_veri
    return son_cekilen_veri


# ---------------------------------------------------------------------------
# FİYAT STRATEJİSİ: Harem ile birebir aynı fiyat.
# Kaynağın has altın fiyatı Harem'in has fiyatıyla aynı; diğer bütün kalemler
# has fiyatından Harem'in oranlarıyla türetilir (11.10.2026 Harem ekranından ölçüldü).
#   kalem: (alış katsayısı, satış katsayısı, yuvarlama basamağı)
# Satışta "en uygun fiyat" için SATIS_INDIRIM ile tüm satışları binde X aşağı çekebilirsiniz (0 = Harem ile aynı).
# ---------------------------------------------------------------------------
SATIS_INDIRIM = 0.0  # örn. 0.001 = satışlar Harem'den binde 1 ucuz

ALTIN_KATSAYI = {
    "HAS ALTIN":   (1.0,     1.0,     2),
    "GRAM ALTIN":  (0.995,   1.003,   2),   # 995 milyem: alışta 5 milyem düşülür
    "22 AYAR":     (0.909698, 0.9369923, 2),
}
SIKKE_KATSAYI = {
    "YENİ ÇEYREK": (1.63,    1.63476, 0),   # sikke fiyatları Harem gibi tam lira
    "YENİ YARIM":  (3.26,    3.26847, 0),
    "YENİ TAM":    (6.50306, 6.518,   0),
    "YENİ ATA":    (6.61994, 6.68307, 0),
}


def _fiyat(h_alis, h_satis, katsayi):
    ka, ks, basamak = katsayi
    return {
        "alis": round(h_alis * ka, basamak),
        "satis": round(h_satis * ks * (1 - SATIS_INDIRIM), basamak),
    }


def matematiksel_motor():
    baz = ana_verileri_cek()
    if baz is None:
        return None
    h_alis = baz["HAS"]["alis"]
    h_satis = baz["HAS"]["satis"]

    islenmis = {"ozet": {}, "altin": {}, "eski_altin": {}, "doviz": {}}
    for ad, k in ALTIN_KATSAYI.items():
        islenmis["ozet" if ad != "22 AYAR" else "altin"][ad] = _fiyat(h_alis, h_satis, k)
    for ad, k in SIKKE_KATSAYI.items():
        islenmis["altin"][ad] = _fiyat(h_alis, h_satis, k)

    islenmis["doviz"]["Dolar"] = {"alis": baz["USD"]["alis"], "satis": baz["USD"]["satis"]}
    islenmis["doviz"]["Euro"] = {"alis": baz["EUR"]["alis"], "satis": baz["EUR"]["satis"]}
    return islenmis


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
