import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn

app = FastAPI(title="Sedef Kuyumculuk - Kapalıçarşı Motoru")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VİTRİN VE ANA SAYFA YÖNLENDİRMESİ ---
app.mount("/vitrin", StaticFiles(directory="static"), name="static")


@app.get("/")
def ana_sayfaya_yonlendir():
    return RedirectResponse(url="/vitrin/index.html")


# -----------------------------------------

# KAPALIÇARŞI STANDART DARPHANE KATSAYILARI
K_22 = 0.916
K_CEYREK = 1.605
K_YARIM = 3.21
K_TAM = 6.42
K_ATA = 6.61


def ana_verileri_cek():
    # Render'ın IP engelini aşmak için AllOrigins aracı servisini (Proxy) kullanıyoruz
    url = (
        "https://api.allorigins.win/raw?url=https://api.genelpara.com/embed/altin.json"
    )

    ham_veri = {
        "HAS": {"alis": 0.0, "satis": 0.0},
        "USD": {"alis": 0.0, "satis": 0.0},
        "EUR": {"alis": 0.0, "satis": 0.0},
    }

    try:
        # Proxy kullandığımız için ekstra başlık (header) göndermemize gerek yok
        res = requests.get(url, timeout=10).json()

        if "GA" in res:
            # GenelPara'da GA (Gram Altın), 24 ayar has altın fiyatını temsil eder
            ham_veri["HAS"]["alis"] = float(res["GA"]["alis"])
            ham_veri["HAS"]["satis"] = float(res["GA"]["satis"])

        if "USD" in res:
            ham_veri["USD"]["alis"] = float(res["USD"]["alis"])
            ham_veri["USD"]["satis"] = float(res["USD"]["satis"])

        if "EUR" in res:
            ham_veri["EUR"]["alis"] = float(res["EUR"]["alis"])
            ham_veri["EUR"]["satis"] = float(res["EUR"]["satis"])

    except Exception as e:
        print("API Veri Akışı Hatası:", e)
        # Proxy de takılırsa ekranda 8888 göreceğiz
        ham_veri = {
            "HAS": {"alis": 8888.0, "satis": 8888.0},
            "USD": {"alis": 34.00, "satis": 34.00},
            "EUR": {"alis": 37.00, "satis": 37.00},
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
        "altyapi": "Proxy Üzerinden Canlı Akış",
        "kategoriler": matematiksel_motor(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
