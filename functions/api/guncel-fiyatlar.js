// Cloudflare Pages: /api/guncel-fiyatlar → Worker ile aynı fiyat motoru
import { apiYaniti } from "../../src/worker.js";

export const onRequestGet = (context) => apiYaniti(context);
