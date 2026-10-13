// Çarşı günlük ortalaması · kayıt (cron Worker) ve okuma (Pages /api/carsi-gunluk) ortak kodu.
// Kaynak: ana fiyat kaynağı (vitrinle aynı). Yedek kaynak bu kayıtta KULLANILMAZ. Tedarikçi adı yanıtta yok.

export const KAYIT_KALEMLERI = [
  "ALTIN", "GRAMALTIN", "AYAR22",
  "CEYREK_YENI", "YARIM_YENI", "TEK_YENI", "ATA_YENI",
  "CEYREK_ESKI", "YARIM_ESKI", "TEK_ESKI", "ATA_ESKI",
  "USDTRY", "EURTRY",
];
export const MAX_SAPMA = 0.03;          // son örneklerin ortancasından %3'ten fazla oynayan değer kaydedilmez
export const BASLA_DK = 9 * 60;         // 09:00 TR
export const BITIS_DK = 20 * 60 + 30;   // 20:30 TR (dükkân 20:00'de kapanır; son dakika işlemleri için)
const TR_FARK_SN = 3 * 3600;            // Türkiye UTC+3 (yaz saati yok)

export function trZaman(ms) {
  const d = new Date(ms + TR_FARK_SN * 1000);
  const iso = d.toISOString();
  return { gun: iso.slice(0, 10), saat: iso.slice(11, 16), dk: d.getUTCHours() * 60 + d.getUTCMinutes() };
}

const ortanca = (a) => { const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

// ham: {KOD: {alis, satis}} · onceki: son örneklerin ham değerleri [{KOD: {alis, satis}}, ...]
export function sapmaAyikla(ham, onceki) {
  const veri = {}, isaretli = {};
  for (const kod of KAYIT_KALEMLERI) {
    const k = ham[kod];
    if (!k || !(k.alis > 0) || !(k.satis > 0) || k.alis > k.satis) continue;
    const refler = onceki.map((o) => o[kod]).filter((x) => x && x.alis > 0 && x.satis > 0);
    if (refler.length) {
      const ra = ortanca(refler.map((x) => x.alis)), rs = ortanca(refler.map((x) => x.satis));
      if (Math.abs(k.alis - ra) / ra > MAX_SAPMA || Math.abs(k.satis - rs) / rs > MAX_SAPMA) {
        isaretli[kod] = { alis: k.alis, satis: k.satis, ref_alis: ra, ref_satis: rs };
        continue;
      }
    }
    veri[kod] = { alis: k.alis, satis: k.satis };
  }
  return { veri, isaretli };
}

const r2 = (x) => Math.round(x * 100) / 100;

// D1'deki günün örneklerinden kalem bazında ortalama / en düşük / en yüksek
export async function gunlukOzet(db, gun) {
  const { results } = await db.prepare("SELECT ts, saat, veri, isaretli FROM ornek WHERE gun = ?1 ORDER BY ts").bind(gun).all();
  const kalemler = {};
  let isaretliSayisi = 0;
  for (const r of results || []) {
    const veri = JSON.parse(r.veri || "{}");
    if (r.isaretli && r.isaretli !== "{}") isaretliSayisi += Object.keys(JSON.parse(r.isaretli)).length;
    for (const [kod, v] of Object.entries(veri)) {
      const k = kalemler[kod] || (kalemler[kod] = { alis: [], satis: [], ilk_saat: r.saat, son_saat: r.saat });
      k.alis.push(v.alis); k.satis.push(v.satis); k.son_saat = r.saat;
    }
  }
  const ozet = (a) => ({ ortalama: r2(a.reduce((s, x) => s + x, 0) / a.length), en_dusuk: r2(Math.min(...a)), en_yuksek: r2(Math.max(...a)) });
  const cikti = {};
  for (const [kod, k] of Object.entries(kalemler)) {
    cikti[kod] = { alis: ozet(k.alis), satis: ozet(k.satis), ornek_sayisi: k.alis.length, ilk_saat: k.ilk_saat, son_saat: k.son_saat };
  }
  const n = (results || []).length;
  return {
    gun, kaynak: "carsi", birim: "TL",
    ornek_sayisi: n,
    ilk_saat: n ? results[0].saat : null,
    son_saat: n ? results[n - 1].saat : null,
    kayit_saatleri: "09:00–20:30 (5 dakikada bir)",
    isaretli_sayisi: isaretliSayisi,
    kalemler: cikti,
  };
}
