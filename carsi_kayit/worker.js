// Sedef · çarşı fiyat kaydı (Cloudflare cron Worker)
// Her 5 dakikada bir, 09:00–20:30 (TR), ana kaynaktan fiyatları alır ve D1'e (sedef-carsi) yazar.
// Ana kaynak yanıt vermezse o dakika ATLANIR (yedek kaynak bu kayıtta kullanılmaz).
import { hamVeriyiAyikla } from "../src/worker.js";
import { BASLA_DK, BITIS_DK, sapmaAyikla, trZaman } from "../src/carsi.js";

const KAYNAK_URL = "https://mobil.gencmetalrafineri.com/service/index.php?islem=cur__prices";

export async function kaydet(env, zamanMs) {
  const t = trZaman(zamanMs);
  if (t.dk < BASLA_DK || t.dk > BITIS_DK) return { durum: "saat dışı", ...t };
  let ham;
  try {
    const res = await fetch(KAYNAK_URL, {
      headers: {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
        "Accept": "application/json, text/plain, */*",
      },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    ham = hamVeriyiAyikla(await res.json());
    if (!ham.ALTIN || !(ham.ALTIN.alis > 0)) throw new Error("gecersiz veri");
  } catch (e) {
    console.log("Kaynak yanit vermedi, bu dakika atlandi:", String(e));
    return { durum: "atlandı", hata: String(e), ...t };
  }
  const ts = Math.floor(zamanMs / 60000) * 60;
  // sapma referansı: son 6 saatteki en çok 3 örneğin ham değeri (ortanca)
  const { results } = await env.CARSI_DB.prepare(
    "SELECT veri, isaretli FROM ornek WHERE ts > ?1 ORDER BY ts DESC LIMIT 3").bind(ts - 6 * 3600).all();
  const onceki = (results || []).map((r) => ({ ...JSON.parse(r.isaretli || "{}"), ...JSON.parse(r.veri || "{}") }));
  const { veri, isaretli } = sapmaAyikla(ham, onceki);
  await env.CARSI_DB.prepare(
    "INSERT OR REPLACE INTO ornek (ts, gun, saat, veri, isaretli) VALUES (?1, ?2, ?3, ?4, ?5)")
    .bind(ts, t.gun, t.saat, JSON.stringify(veri), Object.keys(isaretli).length ? JSON.stringify(isaretli) : null).run();
  if (Object.keys(isaretli).length) console.log("Sapma: kaydedilmedi", JSON.stringify(isaretli));
  return { durum: "kaydedildi", kalem: Object.keys(veri).length, isaretli: Object.keys(isaretli), ...t };
}

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(kaydet(env, event.scheduledTime));
  },
};
