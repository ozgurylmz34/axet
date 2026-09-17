# sinif-proje-sablonu — proje ve paket şablonları (`templates/**`)

## Tetik
Plandaki dosya `templates/project/**`, `templates/project-sap/**` ya da `templates/package/**`.

## Zorunlu ek adımlar
1. Dosyayı klonda al/birleştir.
2. Kullanıcıya açıkça söyle: **bu değişiklik mevcut projelere kendiliğinden ULAŞMAZ**; her proje
   için ayrıca `%guncelle-proje` çalıştırılır. Plan bunu MANUEL özel adım olarak işaretler
   (`guncelle.py ozel-adim <sinif>` → `MANUEL ADIM (...)` satırı); o satırı AYNEN aktar.
3. Test: `python tests/run_tests.py -k new_project` (paket şablonu için `-k new_package`).
4. `templates/package/**` `%guncelle-proje` kapsamı DIŞINDADIR: raporda yalnız bilgi satırı olur.

## DUR
Proje dosyalarına bu akış içinde dokunma. Klon güncellemesi ile proje güncellemesi ayrı
komutlardır ve ayrı onay ister.
