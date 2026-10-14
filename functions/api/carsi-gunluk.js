// Cloudflare Pages: /api/carsi-gunluk?gun=YYYY-MM-DD[&bas=HH:MM&bitis=HH:MM] → günün çarşı ortalaması (SEDEF SİSTEM kur hesabı için)
import { gunlukOzet, trZaman } from "../../src/carsi.js";

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status,
  headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache, must-revalidate" },
});

export async function onRequestGet({ request, env }) {
  const gun = new URL(request.url).searchParams.get("gun") || trZaman(Date.now()).gun;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(gun)) return json({ hata: "gun=YYYY-MM-DD" }, 400);
  if (!env.CARSI_DB) return json({ hata: "kayıt veritabanı bağlı değil" }, 503);
  // isteğe bağlı saat aralığı (ör. bas=09:00&bitis=19:30); verilmezse günün tüm kaydı
  const q = new URL(request.url).searchParams;
  const saat = (x) => (x && /^\d{2}:\d{2}$/.test(x) ? x : null);
  return json(await gunlukOzet(env.CARSI_DB, gun, saat(q.get("bas")), saat(q.get("bitis"))));
}
