> **Tur 6 karar kaydı (2026-10-19, Z199) — tarihçedir, devam noktası değildir.** Satır numaraları KOD DONDU anındaki hâldir; kayabilir. Açık iş `maintenance/IS-LISTESI.md`'de.

# K8 — Z199 tohum dersi karar tablosu (çekirdek 6b6c11d..254134f)

Kaynak kök: `claude/memory-seed/` (çekirdek @254134f). aXet kök: kulvar dalı `wip/t6-k8-ders-sd`.
Sayım: 42 yeni ders (A) + 1 indeks (`_indeks-terfi-2026-10-18.md`, ALMA: aXet kendi `memory/MEMORY.md` indeksini tutar)
+ 5 değişen (M). Hedef satır numaraları KOD DONDU anındaki hâle göre güncellenir (aşağıda "→" sonrası).

**Sayılar (42 ders):** AL 33 · VAR 5 · ALMA 4. (AL = aXet'e yeni metin girdi; VAR = aXet'te zaten var, yer gösterildi;
VAR+ = var, küçük ek yapıldı → AL'ye sayıldı.)

| # | Ders dosyası (çekirdek :gövde satırı) | Özet | KARAR → hedef | Kanıt (aXet) |
|---|---|---|---|---|
| 1 | `feedback_abap-unit-aktivasyon-sonrasi-sahte-sifir-test.md:12` | aktivasyon sonrası ilk `adt_unit_run` dolu testte `method_count:0` dönebilir; kontrol grubu + 2. koşu | AL → `sap-classic-abap/references/classes.md` §5 "Sahte yeşil" + `known-errors-classic.md` satırı | önce: classes.md:101 yalnız "include BOŞ" sahte yeşilini anıyordu |
| 2 | `feedback_adt-get-dtel-ana-dil-metnini-dondurur.md:12` | std DTEL'de `adt_get` ana dil (EN) metnini verir; TR alıntısı DD04T'den | AL → `sap-adt-foundation/references/known-errors-adt.md` K-29 (muaf K- ailesi) | grep `DD04T` aXet = 0 |
| 3 | `feedback_ambalaj-talimati-coklu-p-eml-yaratamaz-vhupo-fm.md:12` | çok P kalemli talimatı EML/OData yaratamaz; FM `VHUPO_PACK_INSTRUCTION_CREATE` kuralları | AL → `sap-cds-ddic/references/packing-instruction.md` §6 (yaratma) + `modules/sd.md` T-SD-4 tuzak | packing-instruction.md:4-5 "yazma kapsam dışı"; grep `VHUPO` = 0 |
| 4 | `feedback_api-teslimat-yolu-vorlage-kopieren-e-ugramaz.md:12` | OData teslimat yaratma VL01N exit yolundan geçmez; ikiz nokta; ABLAD bölünmesi | AL → `modules/sd.md` T-SD-3 tuzak + `modules/referans/sd/enhancements.md` | grep `VORLAGE_KOPIEREN\|RV_DELIVERY_CREATE` = 0 |
| 5 | `feedback_atc-fle-bulgusu-ci-fldext-ok-not-numarali.md:12` | FLE bulgusu `"#EC CI_FLDEXT_OK[<not no>]` | VAR → `sap-code-review/references/atc-fix-patterns.md:18-21` | aynı biçim + not numarası şartı yazılı |
| 6 | `feedback_atc-pretty-print-birim-basina-ilk-fark.md:9` | Pretty Print bulgusu birim başına ilk fark | VAR → `sap-classic-abap/references/classes.md:133` §7.1 + `atc-fix-patterns.md:24` (BE-88 kontrol listesi = K6) | §7.1 mekanizma + reçete |
| 7 | `feedback_atc-pseudo-comment-satir-basina-tek-ve-bulgu-satirina.md:12` | satır başına tek `"#EC`; VALUE/FOR içi WHERE'de bulgunun satırı; ad belge bağlantısından | AL → `atc-fix-patterns.md` §0 pseudo-comment maddesi | önce: :18-23 yalnız ad + not no; "satır başına tek" yoktu |
| 8 | `feedback_cds-endusertext-label-40-karakter.md:9` | `@EndUserText.label` ≤40 (W), obje açıklaması 60 — readback uyarıyı göstermez | AL (VAR+) → `sap-cds-ddic/references/cds.md` etiket şablonu notu | VAR kısmı: `sap-rap/references/layering-and-bdef.md:65`, `service-publish.md:88` (≤40); cds-ddic'te sınır yoktu |
| 9 | `feedback_cl-bcs-set-message-subject-uzun-konu-canli-dogrulandi.md:12` | uzun/Türkçe konu → CL_BCS `set_message_subject` | VAR → `sap-classic-abap/references/email.md:96-98` + `sap-pdf-output/references/mail-eki.md:4,20` | 95 karakter ölçümü dahil yazılı |
| 10 | `feedback_cl-fdt-xl-mutlak-iliski-target-core005.md:12` | `CL_FDT_XL_SPREADSHEET` mutlak Target'lı xlsx'i okuyamaz (FDT_EXCEL_CORE 005) | AL → `sap-classic-abap/references/known-errors-classic.md` satır + ek not | grep `FDT_EXCEL\|CL_FDT_XL` = 0 |
| 11 | `feedback_exit-yeni-satira-updkz-u-vy701-sm13-dump-yok.md:12` | exit yeni satıra UPDKZ='U' → VY 701, SM13 V1, ST22 boş | AL → `modules/referans/sd/enhancements.md` + `modules/sd.md` T-SD-3 + `known-errors-classic.md` satır | grep `UPDKZ\|VY 701\|SM13` = 0 |
| 12 | `feedback_hashed-satir-field-symbol-changing-parametresine-baglanamaz.md:12` | sorted/hashed satır FS'si CHANGING'e bağlanınca dump | AL → `known-errors-classic.md` satır (kontrol listesi BE-84 = K6) | grep `MOVE_TO_LIT` md = 0 |
| 13 | `feedback_klasik-alv-quickinfo-char30-symsgv-char50.md:9` | QUICKINFO CHAR30, SYMSGV CHAR50 kesilir | AL → `sap-classic-abap/references/alv-report.md` §7 | grep `ICONQUICK\|SYMSGV` md'de uzunluk notu yok |
| 14 | `feedback_referansli-talep-oncesi-kopyalama-kontrolunu-olc-tvcpa.md:12` | referanslı talepten önce TVCPA ölç (kontrol grubu); bağ alanı doluluğu | AL → `modules/sd.md` SD-K2 kontrolüne ölçüm notu + `modules/referans/sd/spro.md` VTAF/TVCPA + `tables.md` | grep `TVCPA` = 0 |
| 15 | `feedback_sap-standart-kur-cevrimi-ters-yon-kaydina-sessizce-duser.md:12` | kur çevrimi istenen yön yoksa ters yön kaydına sessizce düşer (XINVR) | AL → `modules/sd.md` T-SD-2 tuzak | grep `XINVR` = 0 (coding-patterns.md K6'nın — öneri raporda) |
| 16 | `feedback_stxl-clustr-bos-metin-sondasi.md:9` | uzun metin boş mu: STXL-CLUSTR uzunluğu + kontrol grubu | AL → `known-errors-classic.md` ek not | cds.md:97 yalnız "STXH/STXL + READ_TEXT" |
| 17 | `feedback_basecontroller-navto-sarmalayici-replace-dusurur.md:9` | `navTo` sarmalayıcısı 3. argümanı düşürür → geri tuşu döngüsü | AL → `sap-ui5-fiori/references/app-skeleton.md` §9 | grep `bReplace\|BaseController` = 0 |
| 18 | `feedback_daterangeselection-ikinci-tarih-gun-sonu.md:12` | `secondDateValue` 23:59:59 → aralık sınırı yanlış | AL → `list-grid-alv.md` §6.1 | :126 yalnız "tarih = DateRangeSelection" |
| 19 | `feedback_gateway-substringof-maxlength-400-ve-tr-harf-sinifi.md:12` | substringof terimi MaxLength'i aşarsa tüm istek 400; {i,I,ı} tek sınıf, İ ayrı | AL → `list-grid-alv.md` §6.2 + `sap-odata-backend/references/filter-search.md` §1 harf notu | :136 / filter-search :21 "harf-duyarsız" diyor, TR istisnası yok |
| 20 | `feedback_m-table-esnek-kolon-dar-ekranda-sifir-px.md:12` | fixedLayout m.Table'da genişliksiz kolon 0 px; margin + 100% taşma | AL → `list-grid-alv.md` §7 | grep `fixedLayout\|calc(100%` = 0 |
| 21 | `feedback_multiinput-yazili-metin-validator-zorunlu.md:11` | MultiInput validator yoksa yazılı değer `$filter`'a girmez | AL → `list-grid-alv.md` §6.1 reçete (FE-50 kontrol listesi = K6) | grep `addValidator` = 0 |
| 22 | `feedback_playwright-httpcredentials-sap-bsp-401-onden-basic.md:12` | doğrudan BSP'de `httpCredentials` 401, önden Basic 200 | AL → `sap-ui5-fiori/references/runtime-verification.md` §4.6 | :232 "`httpCredentials` yeterli; `extraHTTPHeaders` ÖLÇÜLMEDİ" — doğrudan BSP ayrımı yok |
| 23 | `feedback_ui5-float-source-decimal-nokta-tr-yerelde-x1000.md:12` | `type.Float` source'ta yalnız decimalSeparator → TR'de ×1000 | AL → `known-errors-ui5.md` satır (reçete metni freestyle-odata-v2 §5 = K6 için öneri) | grep `groupingSeparator` = 0 |
| 24 | `feedback_ui5-suspended-binding-tablo-render-istegi-atar.md:9` | `suspended:true` render'da istek atar; bindRows controller'da | AL → `list-grid-alv.md` §2 | grep `suspended` = 0 |
| 25 | `feedback_v2-date-only-filtre-utc-gece-yarisi.md:12` | date-only alana UTC gece yarısı | VAR → `sap-ui5-fiori/references/checklists.md:120` FE-45 + `freestyle-odata-v2.md:194` | `Date.UTC` reçetesi yazılı |
| 26 | `feedback_vh-kosul-sekmesi-kucuk-harf-sessiz-bos-sonuc.md:12` | VH koşul sekmesi küçük harf → hatasız 0 satır | AL → `list-grid-alv.md` §6.1 | grep `toUpperCase` UI md = 0 |
| 27 | `feedback_vhd-exclude-bos-dizi-gizlemez-sessiz-dusme.md:12` | `setExcludeRangeOperations([])` gizlemez; exclude token sessiz atlanır | AL → `list-grid-alv.md` §6.1 | grep `setExcludeRangeOperations` = 0 |
| 28 | `feedback_ui5-table-ctrl-a-testi-odakla-tik-sahte-negatif.md:11` | Ctrl+A testinde tık değil `focus()` | AL → `runtime-verification.md` §4.2 (FE-51 kontrol listesi = K6) | grep `Ctrl+A` md = 0 |
| 29 | `feedback_doc-builder-diagram-png-render-gurultusu-geri-al.md:9` | mermaid PNG her derlemede bayt farkı | AL → `sap-fs-ts-docs/references/pdf-with-screenshots.md` tuzaklar | `doc_tools.py:150-158` her koşuda yeniden render eder |
| 30 | `feedback_html-yorumu-icinde-mermaid-ok-yorumu-erken-kapatir.md:9` | `<!-- -->` içinde mermaid `-->` yorumu erken kapatır | AL → `pdf-with-screenshots.md` tuzaklar (DOC-KD-15 genişletmesi = K6) | `verify_doc_html.py:138` yalnız `<pre>` metnini tarar |
| 31 | `feedback_kd-mock-yanit-sekli-gercek-be-yi-izlemeli.md:12` | KD mock'u BE'nin gerçek yanıt ŞEKLİNİ izlemeli | AL → `sap-ui5-user-guide/references/mock-ortam.md` + `gorsel-kontrol.md` (DOC-KD-01 / FE-52 = K6) | mock-ortam.md'de şekil ekseni yok |
| 32 | `feedback_pdftotext-enc-utf8-olmadan-turkce-bozuk.md:9` | `pdftotext -enc UTF-8` yoksa sahte mojibake | AL (kısmi) → `pdf-with-screenshots.md` tuzaklar; html_to_pdf yarısı ALMA: aXet `html_to_pdf.js:270` `path.resolve` | aXet testi zaten `-enc UTF-8` (`test_node_scripts.py:103`) |
| 33 | `feedback_git-stash-u-salt-okunur-bos-dizinde-yarim-kalir.md:12` | `git stash -u` yarım kalır, dosya diskten silinir | AL → `memory/feedback_git-stash-u-yarim-kalabilir.md` (yeni) | grep `stash` memory = 0 |
| 34 | `feedback_gmail-smtp-gecersiz-kimlikte-535-degil-baglanti-keser.md:12` | Gmail SMTP geçersiz kimlikte bağlantı keser | ALMA — kaynak ekibin iç aracı (`send_mail.py`, `conn/.gmail_app_password`); aXet'te SMTP istemcisi yok. Genel ilke VAR: `memory/feedback_ortam-normal-hukmu-hata-metnini-oku.md` + `feedback_sifir-sonuc-kanitla-once-kontrol-grubu.md` | grep `smtp` aXet: yalnız email.md (SAP SCOT) + ortam-normal:18 |
| 35 | `feedback_paralel-oturum-ayni-calisma-agacinda-degisikligi-tasir.md:12` | aynı ağaçta paralel oturum commit'siz işi taşır | AL → `memory/feedback_paralel-oturum-ayni-calisma-agaci.md` (yeni) | grep "paralel oturum" = 0 |
| 36 | `feedback_windowsta-posix-ekseni-simule-edilemez-kanit-gercek-ci.md:9` | dört platform ekseni; POSIX kanıtı gerçek CI | AL (VAR+) → `memory/feedback_yerel-suit-ci-ikizi-degil.md` (eksen maddesi eklendi) | ana fikir zaten :8-17'de |
| 37 | `feedback_ajan-idle-bildirimi-bayat-durum-yeni-durum-degil.md:12` | idle_notification bayat durum | ALMA — Claude Code `SendMessage`/`idle_notification` mekanizmasına özgü | aXet'te bu bildirim yok |
| 38 | `feedback_alt-ajan-spawn-edince-bekci-baslat-onay-beklemesin.md:12` | spawn öncesi bekçi (Monitor/agent_stall_watch) | ALMA — Claude Code Monitor + kaynak ekip betiği | aXet'te karşılığı yok |
| 39 | `feedback_public-core-brifinde-tuketici-proje-adlarini-yasakla.md:12` | public çekirdek brifinde tüketici proje adları | ALMA — kaynak ekibin iç süreci (public çekirdek ↔ tüketici projeler); aXet karşılığı VAR: `memory/feedback_sizinti-taramasi-arama-uzayi-git-deltasidir.md` | — |
| 40 | `feedback_kalite-hizdan-once-tasarim-olcutu.md:12` | kalite > hız; araştırma bulgusu doğrulanmadan dayanak olmaz | VAR → `memory/feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma.md` ("süre baskısında kesilecek şey tur sayısı, inceleme değil") + `feedback_yesil-sinyal-kapsamini-sor.md` (öneri/onay da iddia) + `feedback_performans-onerisi-de-iddiadir.md` | — |
| 41 | `feedback_lider-is-kurali-sessizce-gomulmez-kullaniciya-sunulur.md:12` | kendi koyduğun iş kuralını koda sessizce gömme, sun | AL → `memory/feedback_is-kurali-sessizce-gomulmez.md` (yeni) | komşu `kararlari-once-topla` zamanlama dersi; build sırasında doğan kural yok |
| 42 | `feedback_yeni-onay-kurali-verilmis-karari-yeniden-sordurmaz.md:12` | verilmiş kararı yeniden sorma; karar kaydını tara | AL → `memory/feedback_verilmis-karar-yeniden-sorulmaz.md` (yeni) | grep "yeniden sor" memory = 0 |

### Değişen (M) dosyalar

| Dosya | Fark | KARAR | Kanıt |
|---|---|---|---|
| `MEMORY.md` | indeks satırı | ALMA — aXet kendi `memory/MEMORY.md`'sini tutar | — |
| `feedback_core-index-dala-bagli.md` | madde 5 tersine döndü | ALMA (önceki karar `alinmaz` aynen) — çekirdeğin CORE-INDEX mekanizması | `maintenance/sync-rules.json:1540-1545` |
| `feedback_detached-leading-abapdoc-class-push-400.md` | yetim yorum yalnız IMPLEMENTATION bölümünde | VAR → `sap-classic-abap/references/classes.md:50-56` tablo zaten DEFINITION serbest / IMPLEMENTATION 400 ayrımında | — |
| `feedback_grid-ui-local-run-popup.md` | ŞERH: `FIORI_TOOLS_USER/PASSWORD` run-proxy'de de çalışır (proxy `$metadata` 200) | AL (düzeltme) → `sap-ui5-fiori/references/deploy-and-local-run.md` §1 çürüyen cümle düzeltildi | önce :19-21 "yalnız deploy içindir; çalıştırma proxy'sinde kullanılmaz" |
| `feedback_paralel-infra-pr-ortak-dosya-rebase-sonrasi-tam-suit.md` | tam süit CI'da | ALMA (önceki karar `alinmaz` aynen) | `sync-rules.json:2882-2887` |

### Kalem dışı aday (lider talimatıyla ALINMADI)
- Çekirdek `playbook/intake-triage.md` "Çözüm merdiveni" (+17 satır, 6b6c11d..254134f, `playbook/intake-triage.md:95-110`) — onaylı tur
  kalemlerinden hiçbirine ait değil → aday, alınmadı.
