-- Çarşı (ana fiyat kaynağı) günlük fiyat kaydı · her 5 dakikada bir satır (09:00–20:30 TR)
CREATE TABLE IF NOT EXISTS ornek (
  ts       INTEGER PRIMARY KEY,   -- unix saniye
  gun      TEXT NOT NULL,          -- YYYY-MM-DD (TR saati)
  saat     TEXT NOT NULL,          -- HH:MM (TR saati)
  veri     TEXT NOT NULL,          -- kabul edilen kalemler {KOD: {alis, satis}}
  isaretli TEXT                    -- %3'ten fazla oynadığı için kaydedilmeyen kalemler {KOD: {alis, satis, ref}}
);
CREATE INDEX IF NOT EXISTS ornek_gun ON ornek(gun);
