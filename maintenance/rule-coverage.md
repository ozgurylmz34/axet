# Kural kapsama tablosu — IX çalışma kuralları → aXet

> Bakımcılar için. `sync-rules.json` DOSYA düzeyinde eşler; bu tablo kural dosyalarının **madde** düzeyindeki
> karşılığıdır. Kaynakta bu dosyalardan biri değişince (`sync_check` → DEĞİŞEN) buradaki ilgili satırlar da
> güncellenir. İlk yazım: 2026-09-13.

Zorlama türü: **metin** (her oturum yüklenen çekirdek/SAP kuralı) · **skill** (ilgili iş türünde okunur) ·
**izin** (`permissions.rules` / denylist) · **kod** (script/yazma kapısı reddeder) · **ölçüldü** (aXet'te davranış
canlı denendi). Durum: tamam · kısmi · eksik · alınmaz.

## 1. Kesin yasaklar (`claude/kesin-yasaklar.canonical.md`, proje `CLAUDE.md` damgası)

| # | Kural | aXet'teki yeri | Zorlama | Durum | Not |
|---|---|---|---|---|---|
| 1 | A — standart objeyi yaratma/değiştirme/silme yok | `core/sap/00-sap.md` tablo · `sapadt/gate.py check_names` (Z/Y, standart silme) · **Z104:** `sapadt/std_ext_scan.py` + `gate.check_std_extension` (Z adlı objenin kaynağında standart hedefli `extend type` / `extend view [entity]` / `extend custom\|abstract entity` / `annotate view\|entity` / BDEF `extension` → `ADR_0005_A`) + `adt_push_source` ikinci katman + abapGit `check`/`pack` (aynı tarayıcı; TABL XML `APPEND`→`SQLTAB`) | metin + kod + ölçüldü | tamam | 10 yazma aracının hepsinde Z/Y reddi test edildi; baskılı istemde model reddetti. **Z104 (2026-09-24):** kırmızı ölçüm — sentetik `check_write` 6/6 `allowed=True` (Z adlı append/extend/annotate/BDEF ext.) → kapıdan sonra 6/6 `ADR_0005_A`; anahtar açık + DEV'de de red; fail-closed: hedef çözülemezse `ADR_0005_A`, kaynak yok/tarayıcı koşamazsa `std_ext_scan_unavailable`; `tests/test_std_ext_gate.py` + CLI `6j-ext` + abapGit 3 test; mutasyon (kapı çağrısı / Z-Y kontrolü / 2. katman) testleri adıyla kırdı. Bilinen sınır: BDEF extension'da genişletilen BDEF kaynakta yazmaz → `using interface <Z>` yoksa Z→Z genişletme de red (fail-closed). **Bug gate BULGU 1 (2026-09-24) kapandı:** `--` yorum sayılmadığı için `-- /*` … `-- */` arasındaki gerçek kod siliniyordu (ddls/ddlx/bdef/None + `adt_struct_create` iki alan → `[]`, kapı `allowed=True`) → `--` tüketilir, silinmez; `test_std_ext_*_tire_yorum_bypass` (t1-t8 + kontrol u1-u3). **Bug gate BLOCKER (2026-09-24, taban efbd48f) kapandı:** o tek görünümde BDEF başlığı `--` içindeki `;`'da bitip `--` içindeki yem Z arayüzünü topluyordu (B1-B4, B14 → `[]`, kapı `allowed=True`); baştaki BOM BDEF başlığını gizliyordu; tip None'da Z arayüzlü başlık arkadaki `extend view entity <std>`'yi gizliyordu → kaynak artık **üç görünümde** taranır ((a) `--` tüketilir-silinmez · (b) `--` yorum · (c) `--` kod) ve bulgular birleşir, BOM atılır; `test_std_ext_*_tire_yem_arayuz*` + `*_bom` (y1-y8, bom1-3, kontrol v1-v3) + push_source 2 vaka; mutasyon (c'yi kaldır / yalnız b / b'yi kaldır / BOM atma / None birleşimi) testleri adıyla kırdı. Güvenlik iddiası iki SAP `--` davranışının (b)/(c) ile doğru modellenmesine dayanır — SAP davranışı DOĞRULANMADI. Bilinen yanlış pozitif: `--` yorumunda standart hedefli genişletme metni; alan/alias adı `extend`/`annotate` → `?` red. Canlı yazma yapılmadı |
| 2 | A — standart objeler yalnız okunur; append alanı/DTEL adını AI önermez, append'i ve append alanının Z DTEL'ini AI yaratmaz (kullanıcı yaratır, sonucu bildirir) | `core/sap/00-sap.md` · **kod (Z104):** append'i/extend'i yaratan kaynak yazma kapısında `ADR_0005_A` (satır 1) | metin + kod + ölçüldü | kısmi | Baskılı istemde ad önermedi. **Canlı T4 (2026-09-24, Z103):** ad önermedi ama kullanıcı "adları ben veririm" deyince yaratmayı ÜSTLENDİ → metne "yaratmazsın" + DEVAM tanımı eklendi (`AXET-SAP-0.5.1`); yeniden ölçüm bekliyor. **Kapsam ayrımı (kullanıcı, 2026-09-21; Z36):** yasak yalnız standart objeye append alanı (ve onun DTEL'i); yeni Z DDIC adı öner + canlı kontrol + açık onay (`skills-sap/sap-dev/SKILL.md` §6, `sap-intake-triage` şablonu `ONAY` kutusu) — metin + test `tests/test_sap_skill_bilgi.py`, davranış ölçülmedi (Z37) |
| 3 | B — standart tabloya doğrudan INSERT/UPDATE/DELETE/MODIFY yok | `core/sap/00-sap.md` · `sapadt/std_dml_scan.py` + `gate.check_std_dml` (`ADR_0005_B`, doğrudan BLOCKER — kullanıcı kararı) + `adt_push_source` ikinci katman | metin + kod | tamam | 153/153 senaryo + 30 unittest (lider yeniden koştu); lider ek 12 bağımsız vaka 12/12; mutasyon: tarayıcı kapıdan çıkarılınca test FAIL. Bilinen sınır: ADBC string SQL, INDX `EXPORT/DELETE FROM DATABASE`, `/Z/`-`/Y/` dışı müşteri namespace'i yasaklı sayılır (IMPLEMENTATION §12.5). Canlı yazma yapılmadı. **2026-09-25:** sıra released API (RAP BO/EML · released BAPI · released OData) ile başlar (`AXET-SAP-0.5.2`); karar ağacı `skills-sap/sap-dev/references/write-api-selection.md` (metin). Kod: `std_dml_scan` yalnız doğrudan DML'i reddeder, API seçimini ZORLAMAZ (BE-79 inceleme yargısı); model davranışı ölçülmedi |
| 4 | C — transport yaratma/release yok | `core/sap/00-sap.md` · CLI'de transport yaratan/release eden araç yok · `require_transport` | metin + kod + ölçüldü | tamam | Baskılı istemde reddetti |
| 5 | C — paket yaratma yok | `core/sap/00-sap.md` · `gate.check_names` `PACKAGE_TYPES` | metin + kod | tamam | Ölçüldü: önce kapıdan geçiyordu; düzeltildi, test 5b (package/devc/DEVC/K yaratma + silme → `ADR_0005_C`) |
| 6 | C — enqueue kilidi silme yok | `core/sap/00-sap.md` · CLI'de kilit silme aracı yok | metin + kod | tamam | `adt_lock_check` yalnız okur |
| 7 | D — master_language, 4 etiket, açıklama boş değil | `core/sap/00-sap.md` · `language_mismatch` · `require_tr_text` · `require_all_labels` · reviewer validator'ları | metin + kod | tamam | Canlı yazma yapılmadı |
| 8 | DUR → AÇIKLA → ÖNERİ → İSTE → BEKLE | `core/sap/00-sap.md` | metin + ölçüldü | tamam | |
| 9 | Yasak metni fiziksel damgalı (kurulumdan bağımsız yüklenir) | Global `context_paths` + proje `AGENTS.md` damgası (`scripts/sap_stamp.py`, `new_project.py --sap`, `doctor.py`) | metin + kod + ölçüldü | tamam | Global SAP kapalıyken `--live`: `SAP-CORE-ID: YOK`, `SAP-STAMP-ID: AXET-SAP-0.2.0` → yasak yalnız damgadan yüklendi. Bozuk/eski damga `doctor` FAIL, `new_project --sap` yeniler. 2026-09-14: `sap_stamp.denetle` güncel/farklı/yok/bozuk + ikinci kopya + yetim işaret, `kanonik_denetle` A-D tamlığı (`tests/test_sap_stamp`, `test_doctor`) |

## 2. Her oturum davranış değişmezleri (`CLAUDE.core.md` §1.1)

| # | Kural | aXet'teki yeri | Zorlama | Durum | Not |
|---|---|---|---|---|---|
| 10 | TAHMİN YASAK / kanıtlı hareket | `core/00-temel.md` §1 | metin | tamam | |
| 11 | "Yüklendi/aktive edildi/başarılı" mesajına güvenme | `core/00-temel.md` §1 · `adt_activate` sahte-OK düzeltmesi | metin + kod | tamam | |
| 12 | Kontrol grubu | `core/00-temel.md` §1 | metin | tamam | |
| 13 | ÖNCE-ARA (ara → ölç → daralt → yaz, prior-art satırı) | `core/00-temel.md` §2 · `%recall` | metin + skill | tamam | Otomatik tetik yok |
| 14 | Git: main'e commit yok, dal açık başlangıçla | `core/00-temel.md` §6 · `%commit-pr` · deny kuralları | metin + skill + izin | tamam | |
| 15 | Hedef açıklığı (`--repo`, `git -C`, commit ve PR ayrı) | `%commit-pr` Rules (üç biçim + `gh api` yer tutucu yasağı + `git -C`) · `core/00-temel.md` §6 | skill | tamam | 2026-09-13 |
| 16 | Merge: CI durumu kontrol, `--admin` CI atlatmaz | `%commit-pr` Rules (`gh pr checks` + `--admin` notu) | skill | tamam | 2026-09-13; CI barındırma kararı henüz yok |
| 17 | Worktree yaşam döngüsü | — | — | alınmaz | aXet'te çok ajanlı worktree modeli yok |
| 18 | Gün sonu: checkpoint, SESSION_NOTES, WIP commit, push | `%gun-sonu` (checkpoint → SESSION_NOTES → iş listesi → devir notu → WIP commit → push; "gün sonu" sözü push talebi) · `core/00-temel.md` §0 · paket `SESSION_NOTES.md` şablonu | metin + skill | tamam | Kullanıcı kararı 2026-09-13 "Evet, hepsi". Otomatik tetik yok (hook yok); worktree denetimi alınmaz |
| 19 | Kapanış disiplini (madde artefaktta kapanır, açık madde tek yerde, kapanan çapa arşive) | `core/00-temel.md` §4 · proje `.axet-code/memory/project_is-listesi.md` (Aktif · Ertelenmiş tetikler · Arşiv) · `%gun-sonu` §4 | metin + skill | tamam | IX RESUME çapası + deferred-triggers + archive tek dosyada · 2026-09-25: `%gun-sonu` §4'e ertelenmiş tetik süpürmesi (kapanan/iptal/katılan kalem kaynağıyla arşive; kaynak çekirdek gün-sonu maddesi) |
| 20 | Gate moratoryumu (yeni gate için 5 şart + açık onay) | Template `AGENTS.md` bakım kuralları | metin | tamam | |
| 21 | Alt ajan kararı (önemsiz → kendin, ağır → devret) | `core/00-temel.md` §7 | metin | tamam | |
| 22 | Alt ajan kuralları görmez → brifinge yaz | `core/00-temel.md` §7 | metin + ölçüldü | tamam | Ölçüldü: çekirdek/SAP/proje dosyalarını görmez; §7 buna göre güncellendi |
| 23 | BUG GATE: önemli değişiklikten sonra taze bağımsız inceleme | `core/00-temel.md` §4 + `%code-review` | metin + skill | tamam | Otomatik tetik yok; SAP checklist modu parti 6 |
| 24 | SAP yazma öncesi reviewer pre-flight (BLOCKER → yazma yok) | `sapadt/gate.py` + `run_review` · UI5 deploy: `sap-ui5-fiori/scripts/deploy_ui.py deploy` aynı `gate.check_write`'tan geçer (Z106) | kod | tamam | `skip_reviewer`/`ack_drop` reddi test edildi. **Z106 (2026-09-24):** deploy (BSP yazar) önceden kapısızdı — yalnız `--user-ok` beyanı + `*deploy_ui*` `ask` (oturum izniyle sormadan geçer); artık `sap-write.local` + `--sap-write` + tier DEV + kapsam beyanı + Z/Y + dil kapısı build'den önce, red çıkış 3. BSP için reviewer zinciri YOK (kaynak ABAP değil). `sap-ui5-fiori/tests/test_deploy_ui.py` 13 kapı testi (alt süreç + süreç içi, istek/run sayısı 0; kontrol grubu açık+DEV); canlı deploy ile ÖLÇÜLMEDİ |
| 25 | PULL-BEFORE-EDIT (düzenlemeden önce canlı kaynak) | `sap-adt-foundation` SKILL §2 · `core/sap/00-sap.md` · `sapadt/pull_state.py` (`adt_get` canlı hash kaydeder; `adt_push_source` kayıt yoksa `pull_before_edit_missing`, canlı kaynak değiştiyse `source_changed_since_pull`) | metin + skill + kod | tamam | Karşılaştırma çekildiği andaki canlı ↔ yazma anındaki canlı. Test PBE 1-6 + mutasyon. Canlı ölçüldü: okuma kaydı yazıldı (hash, host/client yok). Canlı push karşılaştırması ölçülmedi (yazma yok). Sınır: okuma ile push arası yarış, durum dosyası elle değiştirilebilir |
| 26 | İnfra sorunu: DONDUR → SINIFLA | Template `AGENTS.md` bakım kuralları | metin | tamam | |
| 27 | Altyapı (script/kural/izin) değişikliğinde önce uyar + açık onay | `core/00-temel.md` §3 "Altyapı değişikliği de onay ister" | metin | tamam | 2026-09-13 |
| 28 | Bağlantı tutarsızlığında SAP işlemi yok | `conn_env_mismatch` · `write_target_mismatch` (`gate.check_target_system`; UI5 deploy `ui5-deploy.yaml` hedefi ≠ `.conn_adt`) | kod | tamam | Z106 (2026-09-24): deploy hedefi `.conn_adt`'den değil `ui5-deploy.yaml`'dan gelir; eşlik denetimi olmadan tier kapısı başka sistemi doğrulardı. Test: url/client farkı → red |
| 29 | Always-allow yasağı | `core/00-temel.md` §3 (kalıcı "allow" ekleme yasağı + `run`/`-y` uyarısı) · `doctor.py` projede şablon desenini ezen kural FAIL | metin + kod | tamam | 2026-09-13 |
| 30 | Kapsam dışı bulgu karar ağacı | `core/00-temel.md` §5 | metin | tamam | |
| 31 | Onay isterken 5 unsur | `core/00-temel.md` §3 | metin | tamam | |
| 32 | Belirsizlikte DUR ve sor | `core/00-temel.md` §3 | metin | tamam | |

## 3. `CLAUDE.core.md` diğer bölümler

| # | Kural | aXet'teki yeri | Zorlama | Durum | Not |
|---|---|---|---|---|---|
| 33 | §2 SAP profil modeli (profil dışı kural uygulanmaz) | `sap-project.json` · `_profile` araç kısıtı · `sap-dev` §2 (profil yeteneğini varsayma, canlı doğrula) · `coding-patterns.md` profil notu | kod + skill | tamam | Her SAP skill'inde profil notu ya da profil bölümü (2026-09-14); foundation araç kısıtı `references/profiles.md` |
| 34 | §3 oturum protokolü + ekran teyidi | `core/00-temel.md` §0 (önce `session_brief.py`: git durum çapası, template güncelliği, doctor FAIL/WARN, aktif paket son kaydı, iş listesi, devir notları; sonra kanarya) · `doctor.py` proje kontrolleri | metin + kod | kısmi | Kanarya run modunda 2 yanıtın 1'inde basıldı; özetin modelce çalıştırıldığı canlı ölçülüyor; hook olmadığı için zorlanamaz |
| 35 | §4 T1–T11 bilgi yazma tetikleri + SORU 0 | `%remember` "When to use" (T1 çalışan + başarısız yollar, T2 ilk obje tipi, T10 inceleme yakalar mıydı, T11 tekrar eden tuzak → skill/checklist/doğrulayıcı önerisi) + kapsam seçimi | skill | tamam | 2026-09-13; otomatik tetik yok |
| 36 | §5 hafıza = hatırlatıcı, kanonik = çekirdek; ders hijyeni | `%remember` (Son-doğrulama + Applies-to + "kanonik yer skill/çekirdek" notu) | skill | tamam | 2026-09-13 |
| 37 | §6 STOP kuralı (validator fail → önce düzelt …) | `core/00-temel.md` §4 "DUR kuralı" | metin | tamam | 2026-09-13 |
| 38 | §7 kapsam beyanı (araç neye bakmadığını söyler) | `core/00-temel.md` §1 · tüm template script'leri KAPSAM satırı basar | metin + kod | tamam | |
| 39 | §8 davranış güvenlik duvarı / yabancı içerik | `%skill-audit` · `doctor.py` ezme kontrolü | skill + kod | tamam | |
| 40a | §7 kod gate'leri → commit anı (Claude hook'larının telafisi) | Proje pre-commit (`templates/project/.githooks/pre-commit` + `scripts/project_precommit.py`): kimlik dosyası, sır deseni, paket adlandırma (`check_package_naming.py`), `validators-local/`, SAP projesinde çevrimdışı reviewer (BLOCKER engeller) · `--no-verify` ve `*core.hooksPath*` bash deny | kod + izin | tamam | `tests/test_precommit` 16 test (gerçek `git commit` uçtan uca, fail-closed). Ağ isteyen reviewer gate'leri commit anında koşmaz → WARN. İzin desenlerinin aXet'te eşleştiği DOĞRULANMADI |
| 40b | §8 davranış yüzeyi manifest'i (F2) | `scripts/behavior_manifest.py` + `doctor.py` (proje: AGENTS.md, .axet-code.json, denylist, .githooks, validators-local hash; template: git tabanlı onaysız değişiklik) · onay `generate` yalnız kullanıcı terminalinde (`*behavior_manifest.py*generate*` bash deny) | kod + izin | tamam | `tests/test_behavior_manifest` 14 test; denylist'in manifest dosyasını aXet'te engellediği DOĞRULANMADI |
| 40 | §10 iş sonu 5 saniye öz-kontrol | `core/00-temel.md` §4 (çalışan yöntemi `%remember`) · `core/sap/00-sap.md` (pakete özgü karar `.rules.md`'ye) | metin | tamam | |

## 4. Proje `CLAUDE.md` (PROVA)

| # | Kural | aXet'teki yeri | Durum | Not |
|---|---|---|---|---|
| 41 | Kesin yasaklar damgası | bkz. #9 | tamam | |
| 42 | Proje kimliği (profil, release, master_language, source_root) | `AGENTS.md` + `sap-project.json` (`source_root`) | tamam | |
| 43 | Proje dosya indeksi (paket registry, kararlar, ertelenmiş işler, overlay'ler) | `<source_root>/PAKETLER.md` (`new_package.py --index`, `doctor` bayatlık WARN) · `AGENTS.md` aktif paket satırı · proje hafızası (kararlar) · `project_is-listesi.md` "Ertelenmiş tetikler" · `validators-local/` overlay (pre-commit çalıştırır) | tamam | 2026-09-14; ayrı `playbook-local/`/`standards-local/` klasörü yok — proje kuralları `AGENTS.md` ve paket `.rules.md`'de |
| 44 | Compact talimatları (neyin korunacağı) | `%handoff` + `core/00-temel.md` §10 | alınmaz | Kullanıcı 2026-09-13: aXet için compact talimatı istenmedi; aXet özetlemesine talimat verilip verilemediği ölçülmedi |

## 5. Hafıza tohumu (`claude/memory-seed`, 86 kayıt)

| Grup | Adet (yaklaşık) | aXet'teki yeri | Durum |
|---|---|---|---|
| Genel çalışma dersleri | 10 (bazıları birleştirildi) | `memory/` ekip hafızası, her oturum yüklenir | tamam |
| Çekirdeğe özet olarak girenler | ~8 | `core/00-temel.md`, `core/sap/00-sap.md` (kanıt disiplini, önce-ara, onay, kapsam dışı bulgu, ALV paritesi, KVKK, Z metin tahmin yasağı, eski sistem alan adı teyidi, clean core, DDIC tablo onayı) | tamam |
| SAP/UI5 teknik dersler (çoğu bir validator'a bağlı) | ~27 | Obje tipi skill referansları: `sap-cds-ddic`, `sap-rap`, `sap-classic-abap`, `sap-odata-backend`, `sap-dev/references/coding-patterns.md` | tamam — SAP backend dersleri (26 dosya, `sync-rules.json` memory-seed satırları) skill referanslarında; UI5 dersleri parti 4'te `memory/feedback_ui5-*` (4 ekip dersi) + `sap-ui5-fiori` referansları (42b37b8). Validator'a bağlı olanların bir kısmı yazma öncesi incelemede kodla çalışıyor (TYPE c parametre, decimal WRITE, window function, para birimi referansı, DTEL etiketleri, master language, alan düşürme, released objeler, RAP etag, audit alanları) |
| Claude'a özgü (hook, ajan takımı, MCP, statusline …) | ~21 | — | alınmaz |
| Proje/tarihsel | ~5 | — | alınmaz |

## Açık düzeltmeler (bu tablodan)
> **Açık maddelerin tek yeri `maintenance/IS-LISTESI.md`'dir** (2026-09-14). Bu bölüm yalnız tarihçedir; burada
> açık madde tutulmaz.

1. **Kapandı (2026-09-14 denetimi):** Hafıza tohumundaki UI5 dersleri — parti 4, `memory/feedback_ui5-*`.
1b. SAP CLI yazma araçları (kullanıcı onayı 2026-09-13 "Evet, hepsi"): kabuk ddls/srvd/bdef/fugr/func/msag/enqu/ttyp, push bdef/ccimp/ccau/func, `adt_screen_generate`, RAP CDS → `rap_cds_creation`, 3 eksik validator kodlandı — çevrimdışı 242/242 + 55 unittest (lider yeniden koştu); **canlı yazma davranışı DOĞRULANMADI**. Mesaj yazma `adt_msgclass_write` ile eklendi (2026-09-13, kullanıcı isteği; kilit silme adımı alınmadı). Kalan: ddlx/dcl/srvb kabuğu, ttyp satır tipi, text pool, RFC-enable (`sync-rules.json` → `scripts/create_*.py`, `push_*.py`).
1c. **Kapandı (2026-09-13, kullanıcı "tabiki"):** `adt_domain_create` ağdan önce `steps.pre_flight` (tip/uzunluk/ondalık/sabit değer metni, `preflight_blocker`) + `artifact_path` ile `domain_creation_csv` zinciri; çıktı uzunluğu hatası düzeltildi (`IMPLEMENTATION.md` §15). Çevrimdışı 323/323 + 70 unittest (lider yeniden koştu); canlı DOĞRULANMADI. Artefaktsız DTEL etiket uzunluğu 2026-09-14 denetiminde kapalı bulundu (`sapadt/tools/composite.py:477` `require_label_lengths`). struct→DTEL varlık kontrolü → `IS-LISTESI.md` D1.
2. #34 kanarya zorlanamaz → `IS-LISTESI.md` D7.
Kapanan (2026-09-13): #9/#41 yasak damgası (kod + canlı ölçüm) · #5 paket yasağı (kod + test) · #19/#23 çekirdek §4 · #20/#26 template `AGENTS.md` · #22 alt ajan (ölçüm + §7) · #3 Yasak B tarayıcısı · #25 PULL-BEFORE-EDIT · #40/#42 paket katmanı.
