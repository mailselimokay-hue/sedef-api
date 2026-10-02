import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Sedef Kuyumculuk - Kapalıçarşı Motoru")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# KAPALIÇARŞI STANDART DARPHANE KATSAYILARI
K_22 = 0.916
K_CEYREK = 1.605
K_YARIM = 3.21
K_TAM = 6.42
K_ATA = 6.61


def ana_verileri_cek():
    # CollectAPI yerine doğrudan Harem Altın'ın canlı web akışı kullanılıyor
    url = "https://www.haremaltin.com/dashboard/ajax/doviz"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    ham_veri = {
        "HAS": {"alis": 0.0, "satis": 0.0},
        "USD": {"alis": 0.0, "satis": 0.0},
        "EUR": {"alis": 0.0, "satis": 0.0},
    }

    try:
        res = requests.post(url, headers=headers, timeout=5).json()
        data = res.get("data", {})

        # Harem'den fiziki Has Altın ve Döviz çekiliyor
        if "ALTIN" in data:
            ham_veri["HAS"]["alis"] = float(data["ALTIN"]["alis"])
            ham_veri["HAS"]["satis"] = float(data["ALTIN"]["satis"])

        if "USDTRY" in data:
            ham_veri["USD"]["alis"] = float(data["USDTRY"]["alis"])
            ham_veri["USD"]["satis"] = float(data["USDTRY"]["satis"])

        if "EURTRY" in data:
            ham_veri["EUR"]["alis"] = float(data["EURTRY"]["alis"])
            ham_veri["EUR"]["satis"] = float(data["EURTRY"]["satis"])

    except Exception as e:
        print("Çarşı Veri Akışı Hatası:", e)
        # Yedek Veriler
        ham_veri = {
            "HAS": {"alis": 6545.0, "satis": 6585.0},
            "USD": {"alis": 34.20, "satis": 34.25},
            "EUR": {"alis": 37.80, "satis": 37.90},
        }

    return ham_veri


def matematiksel_motor():
    baz = ana_verileri_cek()
    h_alis = baz["HAS"]["alis"]
    h_satis = baz["HAS"]["satis"]

    maliyet = {
        "GRAM": {"alis": h_alis, "satis": h_satis},
        "22_AYAR": {"alis": h_alis * K_22, "satis": h_satis * K_22},
        "CEYREK": {"alis": h_alis * K_CEYREK, "satis": h_satis * K_CEYREK},
        "YARIM": {"alis": h_alis * K_YARIM, "satis": h_satis * K_YARIM},
        "TAM": {"alis": h_alis * K_TAM, "satis": h_satis * K_TAM},
        "ATA": {"alis": h_alis * K_ATA, "satis": h_satis * K_ATA},
    }

    islenmis = {"ozet": {}, "altin": {}, "eski_altin": {}, "doviz": {}}

    # SATIŞLAR KAPALIÇARŞI İLE 1:1 AYNI (MİNİMUM MARJ STRATEJİSİ)

    islenmis["ozet"]["HAS ALTIN"] = {"alis": h_alis - 5, "satis": h_satis}
    islenmis["ozet"]["GRAM ALTIN"] = {
        "alis": maliyet["GRAM"]["alis"] - 10,
        "satis": maliyet["GRAM"]["satis"],
    }

    islenmis["altin"]["22 AYAR BİLEZİK"] = {
        "alis": maliyet["22_AYAR"]["alis"] - 25,
        "satis": maliyet["22_AYAR"]["satis"],
    }

    islenmis["altin"]["YENİ ÇEYREK"] = {
        "alis": maliyet["CEYREK"]["alis"] - 35,
        "satis": maliyet["CEYREK"]["satis"],
    }
    islenmis["altin"]["YENİ YARIM"] = {
        "alis": maliyet["YARIM"]["alis"] - 70,
        "satis": maliyet["YARIM"]["satis"],
    }
    islenmis["altin"]["YENİ TAM"] = {
        "alis": maliyet["TAM"]["alis"] - 140,
        "satis": maliyet["TAM"]["satis"],
    }
    islenmis["altin"]["YENİ ATA"] = {
        "alis": maliyet["ATA"]["alis"] - 150,
        "satis": maliyet["ATA"]["satis"],
    }

    islenmis["eski_altin"]["ESKİ ÇEYREK"] = {
        "alis": islenmis["altin"]["YENİ ÇEYREK"]["alis"] - 30,
        "satis": islenmis["altin"]["YENİ ÇEYREK"]["satis"] - 30,
    }
    islenmis["eski_altin"]["ESKİ YARIM"] = {
        "alis": islenmis["altin"]["YENİ YARIM"]["alis"] - 60,
        "satis": islenmis["altin"]["YENİ YARIM"]["satis"] - 60,
    }
    islenmis["eski_altin"]["ESKİ TAM"] = {
        "alis": islenmis["altin"]["YENİ TAM"]["alis"] - 120,
        "satis": islenmis["altin"]["YENİ TAM"]["satis"] - 120,
    }
    islenmis["eski_altin"]["ESKİ ATA"] = {
        "alis": islenmis["altin"]["YENİ ATA"]["alis"] - 120,
        "satis": islenmis["altin"]["YENİ ATA"]["satis"] - 120,
    }

    islenmis["doviz"]["Dolar"] = {
        "alis": baz["USD"]["alis"] - 0.05,
        "satis": baz["USD"]["satis"],
    }
    islenmis["doviz"]["Euro"] = {
        "alis": baz["EUR"]["alis"] - 0.05,
        "satis": baz["EUR"]["satis"],
    }

    return islenmis


@app.get("/api/guncel-fiyatlar")
def guncel_fiyatlari_getir():
    return {
        "magaza": "Sedef Kuyumculuk",
        "altyapi": "Kapalıçarşı Doğrudan Akış",
        "kategoriler": matematiksel_motor(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
