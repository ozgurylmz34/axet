# maintenance/ — template bakım alanı

Bu klasör **template bakımcıları** içindir; aXet kullanıcılarının günlük işiyle ilgisi yoktur.
aXet oturumları bu klasörü yüklemez, `install.py` ve `doctor.py` dokunmaz.

İçerik: IX metodoloji kaynağı (DEV_CORE + örnek proje) ile bu template arasındaki aktarım haritası ve güncelleme
prosedürü. Kaynak yollar DEV_CORE köküne göre yazılır; makineye özel mutlak yol ya da kaynağa çalışma zamanı
bağlantısı yoktur.

- [`UPDATE-PROCEDURE.md`](UPDATE-PROCEDURE.md) — adım adım güncelleme
- `sync-rules.json` — kaynak → karar/hedef haritası (elle)
- `sync-lock.json` — son aktarımın hash kilidi (`sync_check.py --update-lock` üretir)
- `sync_check.py` — fark denetimi
- [`rule-coverage.md`](rule-coverage.md) — kural dosyalarının (CLAUDE.core, kesin yasaklar, proje CLAUDE.md, hafıza tohumu) MADDE bazında aXet karşılığı
- [`IS-LISTESI.md`](IS-LISTESI.md) — bakım işlerinin **tek** açık madde listesi (parti denetimi, aktif iş, kararlar, tetikler)
- [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md) — kaynak çekirdekte görülen kusuru bildirme (ölç → taslak → onay → gönder → iş listesi)
- [`howto-gelen-bildirim-degerlendirme.md`](howto-gelen-bildirim-degerlendirme.md) — aXet kullanıcısından gelen bildirimi değerlendirme (kimlik taraması → iddia başına yeniden ölçüm → etki analizi → sahip onayı → düzeltme + yayın → kapanış; durum etiketleri)
- [`canli-test-plani.md`](canli-test-plani.md) — "DOĞRULANMADI" kalemlerinin aXet üzerinden canlı ölçüm planı
- `axet_iz.py` — aXet oturum izi (motorun kaydı, model beyanı değil): oturum DB'si + log'dan kök/alt oturum zaman çizelgesi, §0 sırası hükmü (session_brief + kanarya), okunan/yazılan dosyalar, izin/ret satırları. `python maintenance/axet_iz.py --proje <proje> [--oturum 1]`; kalibrasyonu `tests/test_axet_iz.py`
