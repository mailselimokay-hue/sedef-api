// Cloudflare Pages: /api/carsi-gunluk?gun=YYYY-MM-DD → günün çarşı ortalaması (SEDEF SİSTEM kur hesabı için)
import { gunlukOzet, trZaman } from "../../src/carsi.js";

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status,
  headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-cache, must-revalidate" },
});

export async function onRequestGet({ request, env }) {
  const gun = new URL(request.url).searchParams.get("gun") || trZaman(Date.now()).gun;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(gun)) return json({ hata: "gun=YYYY-MM-DD" }, 400);
  if (!env.CARSI_DB) return json({ hata: "kayıt veritabanı bağlı değil" }, 503);
  return json(await gunlukOzet(env.CARSI_DB, gun));
}
