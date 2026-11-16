# Uyum turu 8 — B2 kulvarı karar tablosu (backend/doküman playbook'ları · checklist'ler · standartlar · PDF/doküman script'leri)

Kaynak: DEV_CORE `dd9ba0f..c457161` · tarih 2026-11-17 · worktree `C:/AI_WORKS/.wt/axet/t8` (dal `feat/2026-11-17-tur8`).
Kısaltmalar: `CD` = `skills-sap/sap-cds-ddic` · `RP` = `skills-sap/sap-rap` · `CA` = `skills-sap/sap-classic-abap` ·
`CR` = `skills-sap/sap-code-review` · `FT` = `skills-sap/sap-fs-ts-docs` · `F` = `skills-sap/sap-adt-foundation` ·
`OB` = `skills-sap/sap-odata-backend` · `IT` = `skills-sap/sap-intake-triage`.
Testler her biri ayrı komut, tek `-k`. Tam takım yerelde KOŞULMADI (CI'a bırakıldı).

## Karar tablosu — playbook

| Kaynak dosya | Karar | aXet hedef | Ne aktarıldı / gerekçe | Test → sonuç |
|---|---|---|---|---|
| `playbook/00-discipline-and-principles.md` (paket-türevli önek + RAP ad kuralı `<önek>`; Z · Y · `/<NS>/`) | VAR + UYARLA | `CD/references/cds.md:200-205` | Önek Z · Y · bildirilmiş `/<NS>/`, view entity adı `<önek><MOD><nnn>_<I\|C\|R\|E>_<AD>`. aXet'e özgü ek: `/NSPC/SD001_V_` tek başına 14 karakter, classic view sığmaz → view entity tercih edilir (SAP'nin namespace'li SQL view sınırı ÖLÇÜLMEDİ). `populate_cds_views` aracı aXet'te yok; ad kararı A1'in `ad_politikasi`'nde | `CR` test_checklists 15/15 |
| `playbook/adt-cds.md` | UYARLA | `CD/references/cds.md` §3.2 · `CD/references/checklists.md` (C-CDS-SQLV-02 :18 · C-CDS-FROM-04 :26) | Namespace önekiyle SQL view adı ve uzunluk; C-CDS-FROM-04 için mevcut kod muafiyeti (BE-68 şerhi) | aynı |
| `playbook/adt-tables-structures.md` | UYARLA | `CD/references/tables-structures.md:178` §3.3 kural 3 | Başka tabloya nitelenmiş para birimi başvurusu geçerli (KONP örneği); `konwa`/`konws` CUKY · `kmein`/`konms` UNIT (sözlük A1'in `ddic_semantics.py`'sinde) | — (metin) |
| `playbook/adt-rap.md` | UYARLA | `RP/references/troubleshoot.md:63` · `RP/references/layering-and-bdef.md` §1 + yeni §5a (:118-130) · `RP/references/behavior-impl.md` §8 :143 · §10 :170 · :185-192 | etag satırı managed / with additional save / with unmanaged save ve namespace'li BDEF'i kapsar; aynı tabloyu paylaşan iki managed kök; custom entity + query sınıfı (**araç desteği A2'ye bağlı** — yaratma kapısı custom entity'yi reddedebilir); `BY \_assoc` niteleyici (varsayılan `FIELDS ( … ) WITH`, `ALL FIELDS` türetilmiş alanlı view'da HANA -305); SUBMIT/iş planlama işleyicide yasak (DESTINATION NONE serbest); eski sürümde SNAPT notu; additional-save BO dışı tampon | — (metin) |
| `playbook/adt-classes.md` | UYARLA (kısmen) | `CA/references/classes.md:20-23` · `:38` §2 satırı · sahte-sıfır tekrarı | Türetilmiş RAP tipi (`OO_SOURCE_BASED 011` → `TYPES ty_failed TYPE RESPONSE FOR FAILED EARLY <bdef>.`); 409 ilk deneme notu; ABAP Unit sahte sıfır tekrar sırası (kontrol grubu → ≥4 dk → 2. koşum → yeniden aktive → DOĞRULANMADI). `adt_get_method` `ENDMETHOD. ENDCLASS.` → `sinir_belirsiz` notu **A2'ye bağlı** (tool-catalog A2'nin) | — |
| `playbook/adt-foundation.md` | UYARLA | `F/references/foundation-ops.md:253` §4.3 · `F/references/foundation-query.md:187-192` §4 | ENHO bağlı include'un tek başına aktivasyonu (karşı gözlem) + `version=inactive` ölçüm tuzağı; ATC sırası push → AKTİVE → ATC, öncesi ↔ sonrası, mevcut koddaki clean-core P1 muafiyeti, ölçülemeyen tip ≠ temiz, paket ATC'sinin maliyeti. SM12 dili (kilit silme kararı kullanıcınındır): VAR `F/references/foundation-ops.md:113` + `:328-355` · `known-errors-adt` K-09 · `CA/references/classes.md:19` | — |
| `playbook/adt-fugr-functions.md` | UYARLA | `CA/references/fugr-fm.md:24` tablo satırı · yeni §2.3 (:112-123) · okuma geri dönüşü notu · RFC satırı | Güncelleme modülü protokolü: metadata PUT, `processingType="update"` + `updateTaskKind="startImmediate"`, kanıt aktivasyon sonrası `TFDIR-UTASK='1'` (PUT sonrası boştur). Metin "Z/Y" der — A1 namespace desteği gelince güncellenecek (AÇIK KALAN) | — |
| `playbook/adt-mcp.md` | ALMA (kulvar dışı) → A2 | `F/references/tool-catalog.md` (A2) | Guardrail metni "müşteri ad alanı (Z/Y ya da `/<NS>/`)" + `adt_get_method` sınır kuralı araç kataloğu satırlarıdır; tool-catalog A2'nin | — |
| `playbook/adt-programs.md` (SM12: kalıntı kilidi kullanıcı siler) | VAR | `F/references/foundation-ops.md:113` · `:328-355` · `known-errors-adt` K-09 | aXet metni zaten "ajan kilidi silmez, kullanıcıya bildirir" diyor (ADR 0005-C ile uyumlu) | — |
| `playbook/known-errors.md` (+1: `fallbackLocale` nesne biçimi 1.71.85) | ALMA (kulvar dışı) → B1 | `sap-ui5-fiori/references/known-errors-ui5.md` | UI5 satırı; B1 kulvarı | — |
| `playbook/lessons-learned.md` (kardeş taraması: kopyalar birebir aynı olmayabilir) | ALMA (kulvar dışı) → B1 | UI5 referansı | UI5 util kopyaları dersi; B1 kulvarı | — |
| `playbook/howto-kullanici-dokumani-pdf-ekran-goruntulu.md` | UYARLA | `FT/references/pdf-with-screenshots.md` §B4 (:137-155) + Tuzaklar satırı (çıplak dosya adı cwd'ye göre) | Yerleşim düzeltmesi, `#`/`%`/boşluklu klasör, dizin listesi DURDU, localhost UNC, Git Bash `MSYS_NO_PATHCONV=1`, `PDF UYARILI` | `FT -k node` 29/29 |
| `playbook/adt-enhancement-spot-badi.md` (YENİ, 222 satır) | — | — | B2 kulvar dosyasında YOK (lane-B2.txt); başka kulvarın ya da kapsam dışı — bu kulvarda DEĞERLENDİRİLMEDİ | — |

## Karar tablosu — checklist'ler (kimlik numaraları kaynakla aynı)

| Kaynak | Karar | aXet hedef | Ne aktarıldı | Test → sonuç |
|---|---|---|---|---|
| `checklists/bug-checklist-backend.md` | UYARLA | `CR/references/checklist-abap.md:16` BE-55 · `:40` BE-12 · `CR/references/checklist-rap.md:11` BE-26 · `:12` BE-20 · yeni BE-89 (:24) · `CR/references/checklist-cds-ddic.md:19` BE-13 | BE-55 (satır içi `TABLE OF`/türetilmiş RAP tipi, gövde DATA serbest); BE-12 clean-core muafiyeti; BE-26 SUBMIT; BE-20 niteleyici; BE-89 `get_as_ranges` alanlar arası `or` → 500; BE-13 yapı dahil. Diff'te "silinen" abaplint yanlış-pozitif / AKTİVASYON-ONLY blokları kaynakta yalnız TAŞINDI (c457161 `bug-checklist-backend.md:105-123`'te duruyor) → yeniden düzenleme, içerik değişmedi; aXet karşılığı VAR `CR/references/checklist-abap.md:87-88` | `CR` test_checklists 15/15 |
| `checklists/cds-creation.md` | UYARLA | `CD/references/checklists.md:18` C-CDS-SQLV-02 | Namespace öneki, `/NSPC/SD001_V_` = 14 karakter | aynı |
| `checklists/struct-creation.md` | UYARLA | `CD/references/checklists.md:71` C-STR-FIELD-01 · `:75` C-STR-CUR-02 | C-STR-FIELD-01 INFO → WARNING (liste + onay kaydı); doğrulayıcı `check_ddic_builtin_fields` aXet'te yok (A1 ALMA) → satır elle kontrol | aynı |
| `checklists/table-update.md` | UYARLA | `CD/references/checklists.md:96` C-TBL-CUR-02 · `:98` C-TBL-DROP-01 · yeni `:104` C-TBL-CRE-01 (WARNING) · `:105` C-TBL-CRE-02 (BLOCKER) · `:166` not | Başka tabloya nitelenmiş başvuru; fiziksel tip kıyası; tablo yaratma bölümü. AX-TBL-APPROVAL-01 KORUNDU (C-TBL-CRE-02 ile örtüşür — AÇIK KALAN) | aynı (`test_cross_skill_ids_exist` C-TBL-CRE-01'i arıyordu → eklendi) |
| `checklists/rap-creation.md` · `rap-troubleshoot.md` | UYARLA | `RP/references/troubleshoot.md:63` | etag satırı üç save biçimi + namespace'li BDEF | — |
| `checklists/checklist-map.yaml` (BE-89 · FE-53..57 kayıtları) | UYARLA (BE kısmı) | `CR/references/validator-map.md` (100 satır sayımı :120, BE-89) | aXet'te `checklist-map.yaml` altyapısı yok; karşılığı validator-map elle eşlemesi. FE kayıtları B1'in | aynı |
| DE-TXT-01 (tohum `zli-obje-text-tahmin-yasak`) | UYARLA | `CD/references/checklists.md:58` | AI önerir + türetme gösterilir + kullanıcı onayı; sessiz uydurma yasak; uzunluk ölçülür | aynı |

## Karar tablosu — standartlar / modül / profil

| Kaynak | Karar | aXet hedef | Ne aktarıldı | Test |
|---|---|---|---|---|
| `standards/02-coding-backend.md` (ETag) | UYARLA | `OB/references/segw-service.md:102-103` | Otomatik `If-Match` yalnız update/remove; `callFunction` için `mParameters.eTag` açıkça; 428; FE-55 eşi; `use etag` | — |
| `standards/04-documentation-fs-ts.md` (+2: TS build'den önce) | UYARLA | `FT/references/ts-authoring.md:7` SIRA bloğu | FS onayı → TS → build → inceleme → SAP yazma; TS'i kodlayan yazmaz | `FT -k skill_structure` 7/7 |
| `playbook/modules/sd.md` (+118) | UYARLA | YENİ `IT/references/modules/sd-dersler.md` (SD-D1…SD-D11) + `IT/references/modules/sd.md` (T-SD-1/2/3/5 işaretçileri :47 :62 :73 :91 · ÇIKARILAN DERSLER :153) | Kimlikler kaynakla aynı; üretici namespace'i nötrleştirildi; SD-D10'a sessiz yanlış fiyat dersi + canlı test kâhini (standart tablo öncesi/sonrası farkı) eklendi | — |
| `profiles/s4_private.yaml` (+3: 1909) | UYARLA | `F/references/profiles.md:30-31` | 1909'da `define view entity … as select from` yok, BDEF `strict` yok | — |

## Karar tablosu — script'ler

| Kaynak | Karar | aXet hedef | Ne aktarıldı | Test → sonuç |
|---|---|---|---|---|
| `scripts/gen_field_table.py` (#410 · #412 · G1/G2) | UYARLA | `FT/scripts/gen_field_table.py` + YENİ `FT/scripts/doc_ad_metin.py` | Kaynak `utils.ad_politikasi` + `utils.cds_metin`'e bağlanıyor; aXet'te **lider kararı**: foundation'a bağımlılık yok, yalnız stdlib GRAMER yardımcısı (`AD_ADAYI`, `ad_coz`, `dosya_adi`, `yerel_ad`, `cds_kod_metni` — string'e duyarlı, `//` `--` `/* */`). custom entity adı + gövde; başlık `{`'ı gövde sanılmaz; `--` yorumu; etiket string'i korunur; `/NS/X` → `#ns#x` komşu dosya | `FT -k field_table` 12/12 · mutasyon 7/7 öldü |
| `scripts/program_to_spec.py` (G3) | UYARLA | `FT/scripts/program_to_spec.py` | `_ADAY` (ASCII namespace adayı, Türkçe sözcük kesilmez), `/` ile başlayan ada katı gramer, ayrı "Namespace'li tablolar" kovası (müşteri mi SAP mı karar vermez) | `FT -k program_to_spec` 6/6 · mutasyon 4/4 |
| `scripts/scaffold_classic_program.py` | UYARLA (kısmen) | `CA/scripts/scaffold_classic_program.py` | Ad reddinde `/` ya da sürücü harfli yol görünürse `MSYS_NO_PATHCONV=1` ipucu. Namespace'li program adı KABULÜ ALINMADI: ad kararı Z/Y'de kalır — **AÇIK KALAN: A1 `ad_politikasi`'ne bağlanabilir** (lider kararı) | kök `-k kural_hatirlatma` 5/5 · mutasyon 1/1 |
| `scripts/html_to_pdf.js` (#389) | UYARLA (elle; aXet sürümü ayrışmış) | `FT/scripts/html_to_pdf.js` | `dosyaUrl` (`url.pathToFileURL` + `\\localhost\` → `127.0.0.1`), dizin listesi dedektörü → `[DURDU] PDF FAIL` çıkış 2 + `oncekiPdfUyar`, `PDF_CSS` (`body` dışı her kural `data-ix-pdf-sar` işaretine bağlı), `yerlesimOlc` (öncesi/sonrası, kademe 1/2/3), her koşumda `YERLESIM:` satırı, kalan taşmada `PDF UYARILI` + stderr `⚠ UYARI YERLESIM` (çıkış 0); --sayfa-no/--yer-imi ölçümleri yerleşimden SONRA; `require.main` koruması + `module.exports` (birim testi). Bayraksız page.pdf seçenek nesnesi tabanla BİREBİR (test) | `FT -k node` 29/29 (7 tarayıcı testi atlandı) · mutasyon 9/9 · tarayıcıyla elle ölçüm (msedge): `#`'lı klasör → PDF OK, gövde 10.5 pt, 190/190 karakter, başlık meta doğru; 2000 px div → PDF UYARILI; dizin → rc 2 |
| `scripts/build_doc_pdf.py` · `scripts/build_kd_pdf.py` | UYARLA | `FT/scripts/build_doc_pdf.py` · `build_kd_pdf.py` docstring | "Bayraksız aynı" daraltıldı (seçenekler aynı, içerik yalnız taşmasız belgede aynı); PDF CSS'i üreticiye yazılmaz; Git Bash `MSYS_NO_PATHCONV=1` | `FT -k build_verify` 27/27 |

## Karar tablosu — tohum dersleri (BE/doküman)

| Tohum | Karar | aXet hedef |
|---|---|---|
| `feedback_abap-unit-aktivasyon-sonrasi-sahte-sifir-test` (değişen) | UYARLA | `CA/references/classes.md` (tekrar + sıra) · `CA/references/known-errors-classic.md:14` (sınıf + fonksiyon grubu) |
| `feedback_atc-priority-1-zorunlu` (değişen) | UYARLA | `F/references/foundation-query.md:187-192` · `CR/references/checklist-abap.md:40` BE-12 |
| `feedback_clean-core-released-cds-proaktif` (değişen: mevcut kod muafiyeti) | UYARLA | `CD/references/checklists.md:26` C-CDS-FROM-04 · `F/references/foundation-query.md:187` · BE-12 |
| `feedback_pdftotext-enc-utf8-olmadan-turkce-bozuk` (değişen: cwd) | UYARLA | `FT/references/pdf-with-screenshots.md` Tuzaklar satırı |
| `feedback_rap-by-assoc-read-all-fields` (değişen: niteleyici) | UYARLA | `RP/references/behavior-impl.md` §8 :143 · BE-20 |
| `feedback_tablo-yaratma-onay-gate` (değişen) | UYARLA | C-TBL-CRE-02 · AX-TBL-APPROVAL-01 korundu |
| `feedback_zli-obje-text-tahmin-yasak` (değişen) | UYARLA | DE-TXT-01 |
| `feedback_canli-test-oracle-sistem-kaydi-uygulama-durumu-degil` (YENİ) | UYARLA (SAP kısmı) | `IT/references/modules/sd-dersler.md` SD-D10 · genel disiplin yarısı → D kulvarı |
| `feedback_exit-include-e-az-yorum` (YENİ) | UYARLA | `CA/references/programs-includes.md:33` §1 |
| `feedback_rap-isleyicide-submit-yasak-destination-none-izinli` (YENİ) | UYARLA | `RP/references/behavior-impl.md:170` §10 · BE-26 |
| `feedback_read-entities-bo-disi-tamponu-gormez` (YENİ) | UYARLA | `RP/references/behavior-impl.md:189-192` |
| `feedback_sessiz-yanlis-fiyat-gorunur-eksikten-agir` (YENİ) | UYARLA | SD-D10 |
| `feedback_yeni-surum-api-yoklugu-denetim-yoklugu-degildir` (YENİ) | UYARLA (SAP kısmı) | `RP/references/behavior-impl.md:185-186` (eski sürüm SNAPT) · genel yarısı → D kulvarı |

## Kulvar dışı dokunuşlar (raporlandı)

- `tests/test_kural_hatirlatma.py` (kök test): mevcut teste `assertNotIn("MSYS_NO_PATHCONV")` + yeni `test_namespace_ya_da_msys_yolunda_ipucu`.
- `CR/references/validator-map.md` §1: `fugr/i` · `fugr_include` · `fugr-include` → `program_push` satırları. **Sebep A1/A2'nin `_reviewer.py`'ye eklediği anahtarlar;** `test_k1_push_keys_listed` kırmızıydı.
  `CR/tests/test_checklists.py` iki regex'e `-` eklendi (tireli anahtar sessizce düşüyordu). Şimdi 15/15. Mutasyon (satır sil) → K1 kırmızı, md5 eşit.
- `FT` örnek adları `ZSD001` → `ZCA001` (skill'in `test_trace_grep_clean` "ZSD0" yasağı). `test_field_table` içinde `\n@UI.` sahte e-posta isabeti satır bölünerek giderildi.

## OTONOM KARARLAR

1. Doküman üreticileri için foundation'dan bağımsız `doc_ad_metin.py` (lider onaylı AR-1 ②). Bu modüle stdlib dışı import eklenemez; `test_g9_helper_is_stdlib_only` bunu ölçer.
2. `html_to_pdf.js` birim testi için `require.main === module` koruması + `module.exports = { dosyaUrl, PDF_CSS }`. CLI davranışı değişmedi.
3. Sahte playwright'a `addStyleTag` + evaluate tür ayrımı (`dizin` · `yerlesim`, işlev kaynağından) eklendi. Taban seçenek testi korundu; belge sayfasındaki evaluate sırası artık `dizin, yerlesim, yerlesim, alt-bosluk`.
4. C-STR-FIELD-01 WARNING yapıldı ama doğrulayıcısı (`check_ddic_builtin_fields`) aXet'te yok. Satır elle kontrol olarak işaretli.

## AÇIK KALAN

- **Lider:** `maintenance/kimlik-kaydi.json` yenilenmeli. `python tests/run_tests.py -k test_kimlik_hizasi` → FAIL 8 ihlal; B2'nin payı BE-89, C-TBL-CRE-01 ve C-TBL-CRE-02 (KAYITTA-YOK). Üçü de kaynak c457161'de var (#425 · #406); FE-53..57 B1'in.
- **A2:**
  - tool-catalog: `adt_get_method` `ENDMETHOD. ENDCLASS.` → `sinir_belirsiz`; guardrail metni "müşteri ad alanı".
  - custom entity yaratma için araç desteği (`RP/references/layering-and-bdef.md` §5a notu).
- **A1/A2:** `check_rap_readonly_consumption.py`'nin `.bdef.asbdef` ve Z-only `_C_` regex'i. A1 karar tablosu bunun UYARLANDIĞINI söylüyor; B2 bunu yeniden ölçmedi (DOĞRULANMADI).
- **A1:**
  - scaffold namespace'li program adı → `ad_politikasi` bağlantısı.
  - `CA/references/fugr-fm.md` "Z/Y" ifadesi namespace desteğine göre güncellenmeli.
  - `sap-dev/references/naming.md` view entity önek kuralı (B2 sahibi değil).
- **Validator yok:** `check_ddic_builtin_fields` (A1 ALMA). C-TBL-CRE-01 ve C-STR-FIELD-01 elle kontrol.
- **AX-TBL-APPROVAL-01 ↔ C-TBL-CRE-02 örtüşmesi:** ikisi birden duruyor; birleştirme kararı lider.
- **B1:** `fallbackLocale` 1.71.85 (known-errors) · "kopyalar birebir aynı olmayabilir" (lessons-learned).
- **D:** `yeni-surum-api-yoklugu` ve `canli-test-oracle` derslerinin genel disiplin yarısı.
- **Tarayıcı testleri:** `SAP_FS_TS_DOCS_BROWSER_TESTS=1` testleri bu turda KOŞULMADI. Gerçek tarayıcı ölçümü yalnız elle 3 duman vakası.
  Kaynak `pdf_yerlesim` fikstürünün Y3 (görsel), Y5b, Y5k, Y6, Y7b, Y7c ve Y8 vakaları aXet'e test olarak TAŞINMADI → KISMİ.

## KAPSAM BEYANI

- **Bakılan:** lane-B2.txt'deki 36 kalem + `dd9ba0f..c457161` diff'i (bu kalemlerin dosyaları).
- **Bakılmayan:**
  - `adt-enhancement-spot-badi.md` (kulvar listesinde yok).
  - B1/A1/A2/D dosyalarının içeriği.
  - aXet tam test takımı.
  - Tarayıcı gerektiren yerleşim vakalarının otomatik testi.
  - "0 bulgu" diye geçen her satır yalnız koşulan hedefli testin yüzeyidir.
