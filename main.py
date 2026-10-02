import requests
import time
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

app.mount("/vitrin", StaticFiles(directory="static"), name="static")


@app.get("/")
def ana_sayfaya_yonlendir():
    return RedirectResponse(url="/vitrin/index.html")


K_22 = 0.916
K_CEYREK = 1.605
K_YARIM = 3.21
K_TAM = 6.42
K_ATA = 6.61

CACHE_SURESI = 60
son_cekilen_veri = None
son_cekim_zamani = 0


def guvenli_float(deger):
    try:
        if isinstance(deger, str):
            if "," in deger and "." in deger:
                deger = deger.replace(".", "").replace(",", ".")
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

    # EKSİK OLAN KİMLİK BİLGİSİ EKLENDİ (Güvenlik duvarını aşmak için)
    headers = {
        "content-type": "application/json",
        "authorization": "apikey 1WBfKZO0tR3RyuVoOYzTZC:1WM34vX7arahMT36SlPAUr",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    ham_veri = {
        "HAS": {"alis": 0.0, "satis": 0.0},
        "USD": {"alis": 0.0, "satis": 0.0},
        "EUR": {"alis": 0.0, "satis": 0.0},
    }

    try:
        res_gold = requests.get(
            "https://api.collectapi.com/economy/goldPrice", headers=headers, timeout=10
        )
        veri_gold = res_gold.json()

        if veri_gold.get("success"):
            for item in veri_gold["result"]:
                if item["name"] == "Gram Altın":
                    ham_veri["HAS"]["alis"] = guvenli_float(item["buying"])
                    ham_veri["HAS"]["satis"] = guvenli_float(item["selling"])
                    break

        res_cur = requests.get(
            "https://api.collectapi.com/economy/allCurrency",
            headers=headers,
            timeout=10,
        )
        veri_cur = res_cur.json()

        if veri_cur.get("success"):
            for item in veri_cur["result"]:
                if item["code"] == "USD":
                    ham_veri["USD"]["alis"] = guvenli_float(item["buying"])
                    ham_veri["USD"]["satis"] = guvenli_float(item["selling"])
                elif item["code"] == "EUR":
                    ham_veri["EUR"]["alis"] = guvenli_float(item["buying"])
                    ham_veri["EUR"]["satis"] = guvenli_float(item["selling"])

        if ham_veri["HAS"]["alis"] > 0:
            son_cekilen_veri = ham_veri
            son_cekim_zamani = guncel_zaman

    except Exception as e:
        print("API Baglanti Hatasi:", e)
        if son_cekilen_veri is not None:
            return son_cekilen_veri
        else:
            ham_veri = {
                "HAS": {"alis": 9999.0, "satis": 9999.0},
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
        "altyapi": "CollectAPI Kurumsal VIP",
        "kategoriler": matematiksel_motor(),
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
