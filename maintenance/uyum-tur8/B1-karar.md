# Uyum turu 8 — B1 kulvarı (UI5 freestyle) karar tablosu

Kaynak: kaynak çekirdek `dd9ba0f..c457161` · tarih 2026-11-17.
Kulvar: `skills-sap/sap-ui5-fiori/**` (şablon, referanslar, script'ler, testler). `sap-ui5-user-guide` bu turda değişmedi.
Testler worktree `C:/AI_WORKS/.wt/axet/t8/skills-sap/sap-ui5-fiori` içinde, her biri ayrı komut
(`python tests/run_tests.py -k <ad>`).

## Karar tablosu

| Kaynak dosya | Karar | aXet hedef | Ne aktarıldı / gerekçe | Test → sonuç |
|---|---|---|---|---|
| `playbook/templates/ui5-freestyle/**` (40 dosya: README, `app/` ortak gövde, `surum/1.71` + `surum/1.120`, `backend-referans/`) | UYARLA | `skills-sap/sap-ui5-fiori/templates/ui5-freestyle/` | Birebir kod; satır sonu LF; kaynak çekirdek atıfları aXet yollarına çevrildi (std/03 → `references/*.md` §, playbook § → `freestyle-odata-v2.md` §, FE- → `references/checklists.md`), iç Issue/ADR numaraları nötrlendi ("tüketici ölçümü", "liste ekranı ALV paritesi — SAP çekirdeği"). README aXet için yeniden yazıldı (§0 bilinen sınırlar + ölçülmeyenler, §1 kopyalama sırası, §4 sürüm yüzeyi + yasak desenler, §6 kopya sonrası script'ler). `package.json` `deploy`/`deploy-test` script'leri kaldı (app-skeleton §4: model koşmaz) | `-k ui5_sablon` → 16/16 OK |
| `tests/fixtures/ui5_freestyle_sablon/run.py` | UYARLA | `tests/test_ui5_sablon.py` (yeni, 16 test) | V0–V10 + sızıntı + LF + N1–N3 negatif kontrolleri; dört validator iki sürüm kopyasında koşar, KAPSAM satırı sayısı eşit | `-k ui5_sablon` → 16/16 OK; mutasyon S1–S10 ÖLDÜ |
| `standards/03-coding-ui-fiori.md` §2.6 (sürüm + tema ölçümü, sürüme bağlı kontroller tablosu) | UYARLA | `references/app-skeleton.md` §7.1 (yeni) + §1/§7/§8/§9/§13 | `minUI5Version` = `sap-ui-version.json`; tema = Horizon 200 **ve** md5 ≠ base; `@since` tablosu (IllustratedMessage 1.98, ListBase noData 1.101, rowmodes.Auto 1.119, Avatar 1.73, IAsyncContentCreation 1.89, VariantManagement 1.103, kebab bootstrap, i18n nesne biçimi, rowsUpdated 1.86, sortOrder None 1.120, Spreadsheet ListBinding); manifest i18n **dizgi** biçime çevrildi; `sap.ui.version` ≠ `sap-ui-version.json` notu | `-k ui5_sablon` (V6/V7 manifest+index biçimi) → OK; çapraz § referansı tarama 0 kırık |
| `standards/03` §10.0.1 (kolon filtresi kutu + Filtre… penceresi, wildcard daraltma), §15/§16 (kanonik kaynak = şablon) | UYARLA | `references/list-grid-alv.md` §2/§3/§5/§6.2/§6.4 (yeni)/§7/§8 | §3 tersine çevrildi (util şablondan kopyalanır); §6.4 kutu düz arama + koşul penceresi + ölçüm sınırı; satır modu/`rowsUpdated` sürüme bağlandı; m.Table util'i yok → DUR → sor | `-k ui5_sablon` (V10) → OK |
| `standards/03` §2.5 (`sap.ui.version` notu), §14 kontrol listesi | UYARLA | `app-skeleton.md` §7, §13 | Yukarıda | — |
| `playbook/ui-freestyle-odata-v2.md` (minUI5/tema ölçümü, flexibilityservices 1.71 adı, A1 kök neden, kanonik util = şablon, kopyalar 278–844 satır, satır modu, rowsUpdated @since) | UYARLA | `app-skeleton.md` §7/§7.1 · `list-grid-alv.md` başlık/§2/§3 · `freestyle-odata-v2.md` §8/§9 | A1 (CDN kök neden) aXet'te zaten backend UI5'i — VAR (`known-errors-ui5.md:12`); diğerleri aktarıldı | — |
| `playbook/checklists/bug-checklist-frontend.md` FE-53..FE-57 | AL (kaynak numarasıyla) | `references/checklists.md` | Beş satır aXet sütun biçiminde; dış bildirim/Issue numaraları alınmadı; FE-57 → `%sap-code-review` BE-89 | `sync_check.py --kimlik-denetle` → FE-53..57 **KAYITTA-YOK** (kayıt bayat — lider dosyası; AÇIK KALAN 1) |
| `bug-checklist-frontend.md` FE-32 (c)/(e), FE-46 (b) | UYARLA | `references/checklists.md` | (c) wildcard yalnız seçim/VH; (e) kutu düz arama + pencere; FE-46 runtime kanıtı core sürümü | — |
| `playbook/checklists/ui-freestyle-creation.md` UI-BOOT-01, UI-PERSO-01 | UYARLA | `references/checklists.md` | ölçülen sürüm/tema/`@since`; util şablondan | — |
| `claude/rules/ui5-freestyle.md` | UYARLA | `SKILL.md` §1/§4 + tablo | Şablondan başla; sürüm/tema ölçümü; description 938 karakter (≤ 1024) | `-k sap_skill_bilgi` (kök) → 24 OK · `-k skill_yonlendirme` → 13 OK |
| `governance/decisions/0008-*` (şerh: kanonik yol = şablon, kopyalar ayrışık) | UYARLA | `list-grid-alv.md` başlık + §3 | Karar değişmedi; kopya kaynağı şablon. `core/sap/00-sap.md` (D kulvarı) dokunulmadı | — |
| `scripts/deploy_ui.py` (BSP adı politikası, ICF yolu, yinelenen anahtar) | UYARLA | `scripts/deploy_ui.py` · `scripts/_bspnet.py` · `references/deploy-and-local-run.md` §2/§3 | `prepare` ad kararı A1 `ad_politikasi`'na bağlandı (Z/Y + bildirilmiş `/<NS>/`, `--project-dir`), politika yüklenemezse fail-closed; `bsp_icf_yolu` (ns → `/sap/bc/ui5_ui5/<ns>/<app>/`, bozuk ad ValueError); `deploy-to-abap` görevinde yinelenen anahtar ihlal. `gate.check_write`'a dokunulmadı | `-k bsp_adi` → 15/15 · `-k deploy_ui` → 66/66 · mutasyon M1–M7 ÖLDÜ |
| `deploy_ui.py --all` (`all_kipi`, FAIL özeti) | ALMA | — | aXet'te uygulama listesi açıkça verilir (lider onayı) | — |
| `scripts/verify_ui_static_assets.py` (ICF yolu tek kaynak) | VAR | `scripts/verify_ui_static_assets.py:113` → `_bspnet.bsp_url` → `bsp_icf_yolu` | Kod değişmedi; yol artık namespace dalını kapsar. `--all` ALMA | `-k static_assets` → 4/4 OK |
| `scripts/check_ui_odata_refs.py` (namespace'li servis) | UYARLA | `scripts/check_ui_odata_refs.py` | `/sap/opu/odata/<ns>/<AD>/` → `/NS/<AD>`; ana servis otomatik seçimi yalnız bildirilmiş namespace'te; `--project-dir` | `-k odata_refs` → 9/9 · mutasyon O1–O3 ÖLDÜ |
| `scripts/validators/check_ui5_freestyle_traps.py` (XML yorum maskesi) | VAR | `scripts/_ui5scan.py` `xml_yorumsuz` | aXet'te maske zaten vardı; kaynağın senaryoları test olarak eklendi | `-k xml_yorumu` → 11/11 · mutasyon X1/X2 ÖLDÜ |
| `tests/fixtures/ui5_xml_yorumu/run.py` | UYARLA | `tests/test_ui5_xml_yorumu.py` (yeni) | N0–N4c, K4–K4c, E1, U1 | yukarıda |
| `tests/fixtures/check_ui5_freestyle_traps/good/.../Booking.view.xml` | VAR | `tests/test_ui5_xml_yorumu.py` N0 | Yorumdaki `<f:fields>` metni T4 sayılmaz senaryosu | yukarıda |
| `tests/fixtures/ui5_blok_yorumu/run.py` | VAR | `tests/test_static_checks.py` TestTraps | Yalnız yorum metni değişti ("T1/T2/T3/T4 yok") | `-k TestTraps` → 3/3 OK |
| `playbook/howto-ui-kaynagi-geri-kurma.md` (BSP adı politikası, ICF yolu) | UYARLA | `references/deploy-and-local-run.md` §2 | Ad kararı + ICF yolu + ölçülmeyen namespace sınırı | — |
| `howto-ui-kaynagi-geri-kurma.md` (tazelik damgası store'ları, `CLAUDE_PROJECT_DIR`) | ALMA | — | Kaynak ortama özgü oturum/worktree mekanizması; aXet'te karşılığı yok | — |
| `check_i18n_keys.py` (şablonun `getText("kfp.op." + sOp)` yanlış pozitifi — tur içi bulgu) | UYARLA | `scripts/check_i18n_keys.py` | Dinamik önek: `"x."` ile biten anahtar en az bir önekli anahtar ister (temel + her dil) | `-k TestI18n` → 6/6 · mutasyon I1/I2 ÖLDÜ |
| `claude/agents/frontend-expert.md` | ATLA | `skills-sap/sap-dev/references/role-briefs.md` | D kulvarının işi (brif) | — |
| tohum `feedback_grid-liste-standardi` | UYARLA | `list-grid-alv.md` §2/§3 | Kanonik kaynak şablon, sürüme bağlı satır modu | — |
| tohum `feedback_rapor-filtre-select-options-contains-standardi` | UYARLA | `list-grid-alv.md` §6.2/§6.4 | Wildcard yalnız seçim/VH; kolon kutusu düz arama | — |
| tohum `feedback_playwright-ui5-firepress-model-api` (MessageBox ters istisnası) | UYARLA | `runtime-verification.md` §4.2 · `known-errors-ui5.md` | `memory/feedback_ui5-runtime-sayiyla-dogrula.md` D kulvarında | — |
| tohum `feedback_kapi-zinciri-derlemeyi-gormez` (Vaka 2/3 NUMC) | VAR | `skills-sap/sap-code-review/references/checklist-abap.md:33` BE-80 | ABAP konusu, UI hedefine yazılacak bir şey yok | — |
| tohum `feedback_cdn-surum-varligi-surum-dosyasiyla-kanitlanmaz` | UYARLA | `known-errors-ui5.md` (lokal/deploy tablosu) | Maket/yerel çalıştırmada kütüphane dosyasını ölç; teslim edilen uygulama CDN kullanmaz | — |
| tohum `feedback_deploy-ui-yarida-kesilince-bsp-yine-yaratilmis-olabilir` | UYARLA | `deploy-and-local-run.md` §4 · `known-errors-ui5.md` | Salt okuyarak ölç, baştan deploy + `verify`; silme kararı kullanıcının | — |
| tohum `feedback_onay-diyalogu-afterclose-…` | UYARLA | `known-errors-ui5.md` (Render) | Önce sözü sonuçlandır, sonra destroy; üç kapanış yolu testi | — |
| tohum `feedback_ui-testi-dom-varligi-…` | UYARLA | `runtime-verification.md` §4.3 · `known-errors-ui5.md` | rect + `elementFromPoint`, olay parametresi `-dbg.js`'ten, kopya test düzeneği | — |
| tohum `feedback_ui-testinin-son-kontrolu-…` | UYARLA | `runtime-verification.md` §4.3 | Son kontrol sunucu durumu + mutasyon | — |
| tohum `feedback_ui5-analyticaltable-v2-toplam-tuzaklari` | UYARLA | `list-grid-alv.md` §4.1 (yeni) · `known-errors-ui5.md` | Beş tuzak | — |
| tohum `feedback_ui5-mockserver-batch-etag-iki-nokta-keser` | UYARLA | `known-errors-ui5.md` | ETag `:` → sahte 412. Git Bash `kill` / `rg` yan notları ALMA (UI değil) | — |
| tohum `feedback_ui5-yapici-ayarinda-suslu-parantez-baglamadir` | UYARLA | `known-errors-ui5.md` (Render) | Setter ile ver | — |
| (B2 notu) "kopyalar birebir aynı olmayabilir" (ADR 0008 şerhi, 278–844 satır) | UYARLA | `list-grid-alv.md` başlık + §3 | Kopya kaynağı şablon; eski kopyayı kendiliğinden ezme | — |
| (B2 notu) `fallbackLocale` 1.71.85 | UYARLA | `app-skeleton.md` §7.1/§8 · `freestyle-odata-v2.md` §9 | 1.71.85 nesne biçimini desteklemez, `supportedLocales`/`fallbackLocale` hiçbir yerde okunmaz; ortak gövde dizgi kullanır (şablon V7 testi) | `-k ui5_sablon` V7 → OK |
| `pbe_ui` (test sözleşmesi) | ALMA | — | Kaynak ortama özgü oturum/worktree tazelik damgası | — |
| `ui_dogrulama_satir_sonu_kacis` (test sözleşmesi) | VAR | `scripts/_bspnet.py` `deploy_ayari` | `deploy-to-abap` görev biçimini okur; satır sonu kaçışı `verify` `OK~` sınıfında | `-k deploy_ui` → 66/66 |
| `bsp_adi_namespace` (test sözleşmesi) | UYARLA | `tests/test_bsp_adi_namespace.py` | Yukarıdaki deploy_ui satırı | `-k bsp_adi` → 15/15 |

## Mutasyon sonuçları (kopya + md5 → boz → test → kopyadan geri yükle → md5 EŞİT; hepsi ÖLDÜ)
- **bsp:** M1 eski Z kuralı · M2 bildirilmemiş ns kabul · M3 ICF ns dalı yok · M4 bozuk ad → sap düğümü · M5 yinelenen
  anahtar görülmez · M6 politika fail-open · M7 küçük harf çevrilmez.
- **odata:** O1 harita ns dalı yok · O2 müşteri koşulu kaldırıldı · O3 ana servis ns seçimi yok.
- **xml:** X1 maske kaldırıldı (tam olarak N2/N3/N4a/N4b/N4c düştü — kaynağın beyan ettiği küme) · X2 satır sonu korunmuyor (K4b/K4c).
- **i18n:** I1 önek dalı yok · I2 önek dil denetimi yok.
- **şablon:** S1 yasak API ortakta · S2 1.71 index kebab · S3 i18n nesne · S4 gevşek tarih · S5 kutu joker reddi kaldırıldı ·
  S6 `bilesenArayuzleri` adı · S7 TR'de `msg.saved` yok · S8 sızıntı `std/03` · S9 `getSortOrder` None · S10 `_addFilterMenuItem`
  ortakta. (S1–S10 `test_static` düzeltmesinden SONRA yeniden koşuldu: 10/10 ÖLDÜ, md5 EŞİT.)

## OTONOM KARARLAR
1. Şablon hedefi `templates/ui5-freestyle/` (lider onayı AR-1 ①); şablon README aXet için yeniden yazıldı, kaynak README birebir alınmadı.
2. Manifest `sap.app.i18n` referansta dizgi biçimine çevrildi (iki hatta çalışan tek biçim); nesne biçim yalnız 1.120 notu olarak kaldı.
3. `list-grid-alv.md` §6.4 yeni bölüm olarak §6.3'ten sonra konuldu (şablon README zaten §6.4'e atıfta bulunuyordu).
4. FE-53..57 satırlarında kaynak "Ref" sütunu (dış bildirim numarası) yerine aXet referansı / "tüketici ölçümü" yazıldı.
5. `check_i18n_keys.py`'ye dinamik önek desteği eklendi — şablon kopyasında yanlış ERROR veriyordu (tur içi bulgu, kendi işimizin yan etkisi).
6. `test_ui5_sablon.py`'deki sızıntı regex'i parçalanarak yazıldı (A2'nin `test_static` bulgusu, lider iletti).
7. AnalyticalTable tuzakları `list-grid-alv.md` §4.1'e (liste ekranı tek ev), test kör noktaları `runtime-verification.md` §4.3'e kondu.
8. Kesilen deploy dersinde kaynak tablo adları yerine "nesne katalogu + transport görevi kaydını salt okuyarak ölç" yazıldı (aXet okuma araçları).

## AÇIK KALAN
1. **Kimlik kaydı bayat (lider dosyası):** `python maintenance/sync_check.py --kimlik-denetle` → `[FAIL] 8 kimlik ihlali`:
   FE-53..FE-57 (B1) + BE-89, C-TBL-CRE-01/02 (B2) `KAYITTA-YOK`. Hepsi kaynakta var → `--kimlik-kaydi` ile yenile.
2. Namespace'li BSP'de 15 karakter sınırının namespace'i kapsayıp kapsamadığı ve ICF yolu canlıda ÖLÇÜLMEDİ (kaynakta da tek sistemde ölçülmüş).
3. `_bspkaynak.ODATA_REPO` `Repositories('{bsp}')` BSP adını URL-kodlamadan kullanıyor; namespace'li adla `fetch_ui_source.py indir` ÖLÇÜLMEDİ.
4. Şablonun 1.71 sütunu (boş durum `VBox`, `visibleRowCountMode`) 1.71 çalışma zamanında ÖLÇÜLMEDİ (kaynakta da yalnız API metadata'sı); şablon README §0'da yazılı.
5. `sync-rules.json`'a önerilen yeni desenler (`playbook/templates/ui5-freestyle/*`, `tests/fixtures/ui5_*`, yeni tohum dersleri) `B1-sync.json`'da — mevcut `playbook/templates/*` deseni classic şablona gidiyor, ui5 alt deseni ondan önce gelmeli.
