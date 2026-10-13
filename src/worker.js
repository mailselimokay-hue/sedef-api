// Sedef Kuyumculuk · Canlı fiyat sunucusu (Cloudflare Workers)
// Render'daki main.py'nin birebir karşılığı: aynı kaynak, aynı kalemler, aynı hesaplar.
// Uyumaz: ilk ziyaretçi beklemez.

const KAYNAK_URL = "https://mobil.gencmetalrafineri.com/service/index.php?islem=cur__prices";
const CACHE_SURESI = 10;   // saniye · kaynağa en fazla 10 sn'de bir gidilir
const BAYAT_SURESI = 300;  // bu kadar saniye taze veri gelmezse ekran uyarı verir
const SON_GECERLI_KEY = "https://sedef.internal/son-gecerli-veri";

// (ekran adı, grup, kaynak kodu, yedek alış katsayısı, yedek satış katsayısı, basamak)
const KALEMLER = [
  ["HAS ALTIN",   "altin", "ALTIN",       1.0,      1.0,       2],
  ["GRAM ALTIN",  "altin", "GRAMALTIN",   0.995,    1.003,     2],
  ["22 AYAR",     "altin", "AYAR22",      0.909698, 0.9369923, 2],
  ["YENİ ÇEYREK", "yeni",  "CEYREK_YENI", 1.63,     1.63476,   0],
  ["YENİ YARIM",  "yeni",  "YARIM_YENI",  3.26,     3.26847,   0],
  ["YENİ TAM",    "yeni",  "TEK_YENI",    6.50306,  6.518,     0],
  ["YENİ ATA",    "yeni",  "ATA_YENI",    6.61994,  6.68307,   0],
  ["ESKİ ÇEYREK", "eski",  "CEYREK_ESKI", 1.60994,  1.61374,   0],
  ["ESKİ YARIM",  "eski",  "YARIM_ESKI",  3.20299,  3.21149,   0],
  ["ESKİ TAM",    "eski",  "TEK_ESKI",    6.41007,  6.42809,   0],
  ["ESKİ ATA",    "eski",  "ATA_ESKI",    6.61298,  6.63299,   0],
  ["Dolar",       "doviz", "USDTRY",      null,     null,      3],
  ["Euro",        "doviz", "EURTRY",      null,     null,      3],
];
const GRAM_MILYEM = 0.995;

export function guvenliFloat(deger) {
  if (typeof deger === "number") return Number.isFinite(deger) ? deger : 0;
  if (deger === null || deger === undefined) return 0;
  let s = String(deger).trim();
  if (s.includes(",") && s.includes(".")) {
    s = s.lastIndexOf(",") > s.lastIndexOf(".") ? s.replace(/\./g, "").replace(",", ".") : s.replace(/,/g, "");
  } else if (s.includes(",")) {
    s = s.replace(",", ".");
  }
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : 0;
}

const yuvarla = (x, b) => { const p = 10 ** b; return Math.round(x * p) / p; };

function degisim(fiyat, kapanis) {
  if (!kapanis || kapanis <= 0 || !fiyat) return null;
  return yuvarla((fiyat - kapanis) / kapanis * 100, 2);
}

export function hamVeriyiAyikla(json) {
  const data = (json && json.data) || {};
  const ham = {};
  for (const [kod, item] of Object.entries(data)) {
    if (item && typeof item === "object") {
      ham[kod] = { alis: guvenliFloat(item.alis), satis: guvenliFloat(item.satis), kapanis: guvenliFloat(item.kapanis) };
    }
  }
  return ham;
}

export function matematikselMotor(ham) {
  const has = ham.ALTIN;
  const sonuc = { altin: {}, yeni: {}, eski: {}, doviz: {} };
  for (const [ad, grup, kod, ka, ks, basamak] of KALEMLER) {
    const k = ham[kod];
    let alis, satis, kapanis;
    if (k && k.alis > 0 && k.satis > 0) {
      ({ alis, satis, kapanis } = k);
    } else if (ka !== null) {
      alis = has.alis * ka; satis = has.satis * ks; kapanis = has.kapanis * ks;
    } else continue;
    const kAlisHam = alis;
    if (kod === "GRAMALTIN") alis = has.alis * GRAM_MILYEM;
    sonuc[grup][ad] = {
      alis: yuvarla(alis, basamak),
      satis: yuvarla(satis, basamak),
      degisim: degisim(kod !== "GRAMALTIN" ? alis : kAlisHam, kapanis),
    };
  }
  return sonuc;
}

// ── Yedek kaynak: AltinAPI (yalnızca ana kaynak yanıt vermezse) ─────────
// Anahtar Cloudflare'de gizli değişken olarak durur: ALTINAPI_KEY
const YEDEK_URL = "https://altinapi.com/api/v1/prices";
const YEDEK_CACHE_SURESI = 900; // yedekteyken en fazla 15 dk.da bir istek (aylık kotayı korur · Selim 13.10)
const MAX_SAPMA = 0.03;         // yedek fiyat, son ana fiyattan %3'ten fazla saparsa kullanılmaz

function makulMu(yeni, ref) {
  if (!yeni || !(yeni.alis > 0) || !(yeni.satis > 0) || yeni.alis > yeni.satis) return false;
  if (!ref || !(ref.alis > 0)) return false;
  return Math.abs(yeni.alis - ref.alis) / ref.alis <= MAX_SAPMA;
}

// AltinAPI cevabını ana kaynakla aynı biçime çevirir; her kalemi son ana fiyatla kıyaslar.
async function yedektenGetir(env, ana) {
  if (!env || !env.ALTINAPI_KEY || !ana || !ana.ALTIN) return null;  // referans yoksa uydurma yok
  try {
    const res = await fetch(YEDEK_URL, {
      headers: { "X-API-Key": env.ALTINAPI_KEY, "Accept": "application/json" },
      signal: AbortSignal.timeout(6000),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const liste = ((await res.json()) || {}).data || [];
    const ham = {};
    for (const x of liste) {
      if (!x || !x.symbol) continue;
      const kod = String(x.symbol).toUpperCase();
      const aday = { alis: guvenliFloat(x.bid), satis: guvenliFloat(x.ask) };
      if (!makulMu(aday, ana[kod])) continue;               // şüpheli kalem atlanır
      aday.kapanis = ana[kod].kapanis || 0;                   // günlük değişim için ana kaynağın kapanışı
      ham[kod] = aday;
    }
    return ham.ALTIN ? ham : null;  // has altın yoksa yedek kullanılmaz
  } catch (e) {
    console.log("Yedek kaynak hatasi:", String(e));
    return null;
  }
}

// Kaynaktan çek; taze değilse son geçerli veriyi kullan. Uydurma fiyat yok.
// Sıra: Genç Metal → AltinAPI (yedek) → son geçerli veri ("Gecikmeli" uyarısıyla)
async function verileriGetir(ctx, env) {
  const cache = caches.default;
  const anahtar = new Request(SON_GECERLI_KEY);
  const kayitli = await cache.match(anahtar);
  let son = kayitli ? await kayitli.json() : null;   // { ham, zaman, kaynak, ana }
  if (son && !son.kaynak) { son.kaynak = "ana"; son.ana = son.ham; }  // eski kayıt biçimi
  const simdi = Date.now() / 1000;
  const sure = son && son.kaynak === "yedek" ? YEDEK_CACHE_SURESI : CACHE_SURESI;
  if (son && simdi - son.zaman < sure) return son;

  const kaydet = (yeni) => {
    const kayit = new Response(JSON.stringify(yeni), {
      headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=604800" },
    });
    ctx.waitUntil(cache.put(anahtar, kayit));
  };

  try {
    const res = await fetch(KAYNAK_URL, {
      headers: {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Accept": "application/json, text/plain, */*",
      },
      signal: AbortSignal.timeout(6000),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const ham = hamVeriyiAyikla(await res.json());
    if (ham.ALTIN && ham.ALTIN.alis > 0 && ham.ALTIN.satis > 0) {
      son = { ham, zaman: simdi, kaynak: "ana", ana: ham };
      kaydet(son);
      return son;
    }
    throw new Error("gecersiz veri");
  } catch (e) {
    console.log("Fiyat kaynagi baglanti hatasi:", String(e));
  }

  // Ana kaynak yok → yedek
  const yedekHam = await yedektenGetir(env, son && son.ana);
  if (yedekHam) {
    son = { ham: yedekHam, zaman: simdi, kaynak: "yedek", ana: son.ana };
    kaydet(son);
  }
  return son;
}

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status,
  headers: {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-cache, must-revalidate",
    "Access-Control-Allow-Origin": "*",
  },
});

// /api/guncel-fiyatlar yanıtı · hem Worker hem Pages Functions kullanır
export async function apiYaniti(ctx, env) {
  const son = await verileriGetir(ctx, env);
  if (!son) return json({ magaza: "Sedef Kuyumculuk", durum: "yok" }, 503);
  const yas = Math.floor(Date.now() / 1000 - son.zaman);
  return json({
    magaza: "Sedef Kuyumculuk",
    durum: yas > BAYAT_SURESI ? "bayat" : "canli",
    kaynak: son.kaynak || "ana",
    guncelleme: Math.floor(son.zaman),
    yas_sn: yas,
    kategoriler: matematikselMotor(son.ham),
  });
}


export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const yol = url.pathname;

    if (yol === "/api/guncel-fiyatlar") return apiYaniti(ctx, env);

    if (yol === "/" || yol === "/vitrin" || yol === "/vitrin/") {
      return Response.redirect(url.origin + "/vitrin/index.html", 307);
    }

    if (yol.startsWith("/vitrin/")) {
      const dosyaUrl = new URL(url);
      dosyaUrl.pathname = yol.slice("/vitrin".length);
      const res = await env.ASSETS.fetch(new Request(dosyaUrl, request));
      // index.html → / gibi otomatik yönlendirmeleri /vitrin altında tut
      if (res.status >= 300 && res.status < 400) {
        const hedef = res.headers.get("Location");
        if (hedef && hedef.startsWith("/")) return Response.redirect(url.origin + "/vitrin" + hedef, res.status);
      }
      if (/\.(html|js|json)$/.test(yol)) {
        const yeni = new Response(res.body, res);
        yeni.headers.set("Cache-Control", "no-cache, must-revalidate");
        return yeni;
      }
      return res;
    }

    return new Response("Bulunamadı", { status: 404 });
  },
};
