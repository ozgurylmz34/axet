# sinif-config-izin — izin ve yapılandırma (`config/**`, `.axetcode-denylist`)

## Tetik
Plandaki dosya `config/permissions.json`, `.axetcode-denylist` ya da proje şablonunun config dosyası. `kritik_yol`.

## Zorunlu ek adımlar
1. Dosyayı al/birleştir.
2. **Özel adım (plan zorunlu kılar):** `guncelle.py ozel-adim <sinif>` → `python scripts/install.py`.
   Bu adım koşmadan kapanış 0 dönmez.
3. `python tests/run_tests.py -k install` koş.
4. Kullanıcıya söyle: **aXet'i kapatıp aç** — izinler oturum başında okunur.

## DUR
Kullanıcının kendi izin kuralı template'in bir `deny` satırını eziyorsa bu RAPOR'a yazılır,
ama güncelleme engellenmez. Kullanıcı adına izin gevşetme kararı VERME.
