# Uyum turu 8 — D kulvarı karar tablosu

Kaynak: DEV_CORE `dd9ba0f..c457161` · PROVA `43bd60c..HEAD` · tarih 2026-11-17 (`date +%F`).
Kulvar: çekirdek kurallar, kesin yasaklar damgası, rol brifleri, inceleme brifi, hafıza dersleri, kurulum/doctor.
Testler worktree `C:/AI_WORKS/.wt/axet/t8` içinde, her biri ayrı komut (`python tests/run_tests.py -k <ad>`).

## Karar tablosu

| Kaynak dosya | Karar | aXet hedef | Ne aktarıldı / gerekçe | Test → sonuç |
|---|---|---|---|---|
| `claude/kesin-yasaklar.canonical.md` (A-EK özeti) | UYARLA | `core/sap/00-sap.md` (A satırı + "Müşteri ad alanı" paragrafı, damga bölümü içinde) · `skills-sap/sap-dev/references/role-briefs.md` S1 birebir | A = müşteri ad alanında olmayan (Z/Y ya da bildirilmiş `/<NS>/`); bildirim `sap-project.json` → `customer_namespaces` (A1 ile aynı anahtar); SAP namespace'i ve bildirilmemiş namespace standart; liste yok/boş/bozuk → yalnız Z/Y; SE03/lisans anahtarı C, anahtar dosyaya yazılmaz; listeye ekleme kullanıcı beyanı; D namespace'liye de uygulanır. SAP-CORE-ID dokunulmadı | `-k test_sap_stamp` 8/8 · `-k test_sap_skill_bilgi` 24/24 (S1 eşitliği) |
| `governance/decisions/0005-*` (A-EK) | UYARLA | yukarıdakiyle aynı + `templates/project-sap/sap-project.json` (`customer_namespaces: []` + açıklama) · `templates/project/AGENTS.md` SAP satırı | ADR metni aXet'e ADR olarak alınmaz (çekirdek damgası kanonik); kilit nesnesi EZ/EY ve FUGR include biçimi A1'in `ad_politikasi`'nde | `-k test_new_project` 12/12 (anahtar + damga paragrafı yeni assertion) |
| proje `CLAUDE.md` (PROVA; yasak damgası A-EK) | VAR | `core/sap/00-sap.md` damgası → `scripts/sap_stamp.py` proje `AGENTS.md`'ye basar | `sap_stamp.py` kodu DEĞİŞMEDİ: bölüm deseni `## ⛔ KESİN YASAKLAR … ## ` ve A-D tamlık denetimi yeni metni kapsıyor (ölçüldü: test_sap_stamp yeşil) | `-k test_sap_stamp` 8/8 |
| `CLAUDE.core.md` — onay penceresi açan komut yazma | UYARLA | `core/00-temel.md` §3 (1 satır) · `skills/explore/references/brief-template.md` §3 "Komut biçimi" | Silme yerine üzerine yaz, değişkenli silme yolu yok, çalışma dizini dışına `cd` yok, reddedileni tekrarlama. İzin listesi/`TaskStop` kısmı alınmadı | `-k test_skill` 19/19 · doctor (izole config) 0 FAIL |
| `CLAUDE.core.md` — gün sonu "iş dalı PR ile main'e GİRER" | UYARLA | `skills/gun-sonu/SKILL.md` adım 8 | Push ≠ main'e girdi; dal iş listesinde `(main'e girmedi — PR yok / PR #n açık)`; bitmiş iş için `%commit-pr` önerisi; inceleme koşmamış/BLOCKER'lı iş PR'a/main'e alınmaz. Birleştirme aXet gün sonunun parçası değil (lider kararı ④) | `-k test_skill` 19/19 |
| `CLAUDE.core.md` — A özeti (namespace) | VAR | `core/sap/00-sap.md` | Çekirdek özetindeki A satırı aXet'te SAP çekirdeğinde (yukarıda) | — |
| `CLAUDE.core.md` — worktree `--wt-taban`, ⓒ provizyon hariç, entegrasyon dalı hükmü | ALMA | — | aXet'te çok ajanlı worktree modeli yok (rule-coverage #17) | — |
| `CLAUDE.core.md` — tohum terfi gözlem→karar, onay bekleme gözlemi, ONAY BEKLEYEN AJANA MÜDAHALE, gelen bildirim gözlemi | ALMA | rule-coverage #18c | Claude'a özgü (ajan bekçisi, TaskStop, PushNotification, `seed_memory`, `izin_bekleme_taramasi`); aXet alt görevi tek yanıtla döner | — |
| `claude/agents/backend-expert.md`, `frontend-expert.md`, `sap-feature.md`, `sap-research.md` (BAĞLAM DİSİPLİNİ, teslim öncesi öz-kapı) | UYARLA | `role-briefs.md` yeni S5 + (b)/(c) TESLİM ÖNCESİ ÖZ-KAPI (KAHİN/SINIF/METİN/KARDEŞ) + (b) ÇIKTI 8 + (c) mock-canlı maddesi; "S1-S4" → "S1-S5" (`role-briefs.md` 3 yer, `skills/research/SKILL.md` 1 yer) | Öz-kapı araçları aXet adlarıyla (`adt_sql_query`, `adt_grep_source`, `adt_where_used`, `rg`); FE-54/55/56 kimlikleri aXet kontrol listesinde yok → kimliksiz madde. Transkript okuma yasağı ve onay penceresi bölümü alınmadı (alınmayanlar tablosuna 2 satır) | `-k test_sap_skill_bilgi` 24/24 |
| `claude/agents/bug-expert.md` (büyük kaynak istisnası, madde başına tek satır) | UYARLA | `skills-sap/sap-code-review/references/reviewer-brief.md` (S5 bloğu, ≳1000 satır kaynakta bölge okuma, KAPSAMA tablosunda tek kimlik/tek satır, ana oturum denetimine "birleşik satır") · `skills/code-review/SKILL.md` (OKUMA satırı + tek satır) | — | `-k test_sap_skill_bilgi` 24/24 · `-k test_skill` 19/19 |
| `claude/agents/adt-gateway.md` (ADR 0005 namespace + BE-13 tablo/yapı onay kaydı) | UYARLA | `skills-sap/sap-dev/SKILL.md` §6 "Yeni DDIC tablo ya da yapı" satırı (DTEL'siz alan listesi + onay kaydında adıyla; `%sap-cds-ddic` C-TBL-CRE-01/02, C-STR-FIELD-01) | Gateway kodu (`sap_adt_cli.py`, `std_dml_scan.py`) A1/A2 kulvarında; namespace kapısı A1'in | `-k test_sap_skill_bilgi` 24/24 |
| `claude/templates/spawn-brief.md` | UYARLA | `skills/explore/references/brief-template.md` §3 (komut biçimi + DOĞRULAMA KADANSI) + alınmayanlar tablosu 2 satır | "KOD DONDU sonrası kapsam eklenmez" lider notu: aXet'te ara kanal yok → dönüşten sonra gelen kalem yeni devirdir (yapısal karşılık); onay penceresinde durdurma alınmadı | `-k test_skill` 19/19 |
| `claude/rules/sap-source-protokolu.md` (`table_creation`/`struct_creation` DTEL'siz alan listesi; §9 namespace) | UYARLA | `skills-sap/sap-dev/SKILL.md` §6 · `skills-sap/sap-dev/references/naming.md` §3 namespace notu | aXet'te DTEL'siz alan validator'ı yok (B kulvarı checklists notu); kural elle yürünen C-TBL-CRE satırlarına bağlandı. `sap-adt-foundation/SKILL.md` A2 ile ortak → dokunulmadı (aşağıda AÇIK KALAN) | `-k test_sap_skill_bilgi` 24/24 |
| `claude/skills/sap-abap-dev/SKILL.md` (guardrail metni namespace) | UYARLA | `naming.md` §3 · S1 damgası | aXet guardrail metni `sap-adt-foundation/SKILL.md:115` (A2/A1) — dokunulmadı | — |
| `claude/skills/sap-abap-dev/references/operational-lessons.md` (409/kilit: bizimse bırak, başkasınınsa kullanıcı) | VAR | `skills-sap/sap-adt-foundation/references/foundation-ops.md` §5 (araç yalnız kendi handle'ını bırakır, kilit temizlemez, SM12 kullanıcıda, 409'da retry yok) | aXet'te bağımsız unlock aracı yok; davranış zaten kaynağın yeni metniyle aynı yönde | — |
| `MAINTENANCE.md` (`sql_view_prefix` satırı namespace) | ALMA | — | aXet'te `populate_cds_views` / `_derive_prefixes` / `sql_view_prefix` yok (`rg` 0 eşleşme, maintenance hariç) | — |
| `ONBOARDING.md` (ix_doctor `.tmp` altına yazar) | VAR | `skills/onboard/SKILL.md` | aXet `doctor.py` hiçbir dosya yazmaz (`write_text/write_bytes/open(w)` 0 eşleşme; kaynaktaki 4i/4j kanca smoke'u aXet'te yok). `docs/onboarding.md` için değişiklik GEREKMEZ | — |
| `.github/workflows/core-ci.yml` (`pyyaml`) | ALMA | — | aXet UI5 deploy YAML'ı kendi ayrıştırıcısıyla okur (`sap-ui5-fiori/scripts/_bspnet.py`, PyYAML'sız); B1 testi gerektirmedi (lider kararı ⑥). CI'a dokunulmadı | — |
| `scripts/team_setup.py` | ALMA | — | settings tazeleme, `--wt-ac`/`--wt-taban`, worktree provizyonu Claude/worktree'ye özgü; `install.py` lider işi (değiştirilmedi) | — |
| `scripts/ix_doctor.py` (4h/4i/4j kanca kablolaması) | ALMA | — | aXet'te kanca yok | `-k test_doctor` (aşağıda) |
| `scripts/init_project.py` (`customer_namespaces` yorumu) | UYARLA | `templates/project-sap/sap-project.json` (`new_project.py --sap` kopyalar) | JSON yorum taşımaz → anahtar boş liste + `_aciklama` cümlesi | `-k test_new_project` 12/12 |
| `scripts/bootstrap_package.py` (ce8a124, namespace paket adı) | UYARLA | `scripts/new_package.py` · `templates/package/.rules.md.tmpl` (kilit satırı `{LOCK}{LOCK_NOTE}`; Z/Y çıktısı bayt-aynı) · `scripts/check_package_naming.py` (`--package /NS/…` klasörü bulur) | A1 modülü `importlib` ile dosyadan yüklenir; yoksa/yüklenemezse namespace RED, Z/Y aynen (lider kararı ②). Klasör `#ns#…`; sınıf öneki `/<NS>/CL_<gövde>_*`; namespace'li kilit nesnesi satırı DOĞRULANMADI etiketli | `-k test_new_package` 21/21 (5 yeni) · `-k test_package_naming` 13/13 |
| `scripts/hooks/session_start.py` + `scripts/git-hooks/core_precommit.py` (Q349 tam ref) | UYARLA (kısmi) | `scripts/session_brief.py` `YAYINLAR_REF` → `refs/remotes/origin/main:…` | `project_precommit.py`'de `origin/main`/changelog mantığı yok → ALMA. `guncelle.py`/`guncelle_proje.py` aynı sınıf → AÇIK KALAN (lider kararı ⑤) | `-k test_session_brief` 23/23 (1 yeni) |
| `scripts/seed_memory.py` (#430 indeks, a-taze) | ALMA | — | aXet'te tohum dağıtıcısı yok; ekip hafızası git ile gider | — |
| `claude/memory-seed/feedback_bash-heredoc-kacis-ve-utf8-bozulmasi.md` | UYARLA | `memory/feedback_bash-heredoc-turkce-kacis.md` | 4. vaka (`\b` → 0x08, bayt sayımı) + 5. vaka (kabuk test vektörü, `chr(92)`) | `-k test_recall` 23/23 |
| `claude/memory-seed/feedback_deploy-lokal-test-onayi-sart.md` | UYARLA | `memory/feedback_deploy-kullanici-testi-sonrasi.md` | Deploy kapsamı = çalışma ağacı; yazma brifine deploy adımı koyma | `-k test_recall` 23/23 |
| `claude/memory-seed/feedback_kararlari-once-topla-sonra-dispatch.md` | UYARLA | `memory/feedback_kararlari-once-topla.md` | Teknik şartlar da önce; iki parçalı çözüm birlikte; şart brifin içinde | `-k test_recall` 23/23 |
| `claude/memory-seed/feedback_kendi-isini-yeniden-siniflandirip-kural-disina-cikma.md` | UYARLA | aynı adlı aXet dersi | Vaka 3 (karar kaydından gelen onay kalemi) + vaka 4 ("küçük" değişikliği kendin yazmak) | `-k test_recall` 23/23 |
| `claude/memory-seed/feedback_takim-sureklilik-gun-sonu-resume.md` | UYARLA | `skills/gun-sonu/SKILL.md` adım 8 | Dal ≠ main; ajan checkpoint kısmı Claude'a özgü | `-k test_skill` 19/19 |
| `feedback_engellenen-silmeyi-kullaniciya-komut-olarak-verme.md` | AL | `memory/feedback_engellenen-silmeyi-komut-olarak-verme.md` | Genel; iç adlar çıkarıldı | `-k test_recall` 23/23 |
| `feedback_is-parametresini-koda-gomme-onerme.md` | AL | `memory/feedback_is-parametresini-koda-gomme.md` | — | aynı |
| `feedback_kayit-tarihi-saatten-alinir.md` | AL | `memory/feedback_kayit-tarihini-olc.md` | — | aynı |
| `feedback_kullanici-testi-sirasinda-yeni-parti-baslatma.md` | AL | `memory/feedback_kurulumdan-sonra-yeni-parti-sorulur.md` | Ajan açma ifadesi "alt görev" olarak genelleştirildi | aynı |
| `feedback_python-ile-dosya-duzenlerken-bayt-kipi-kullan-eol-korunur.md` | AL | `memory/feedback_python-yerinde-duzenleme-bayt-kipi.md` | Önce `edit` aracı, gerekirse bayt kipi | aynı |
| `feedback_test-yazmadan-once-acik-onay.md` | AL | `memory/feedback_uygulama-testi-onayla-yazilir.md` | Kapsam: uygulama testleri; aXet araç testleri dışarıda | aynı |
| `feedback_re-gate-dar-kapsam-yalniz-high-durdurur.md` | UYARLA | `memory/feedback_yeniden-inceleme-dar-kapsam.md` | bug-expert → `%code-review` / `%sap-code-review` | aynı |
| `feedback_aralikli-hata-avina-butce-koy-ilerlemeyi-izle.md` | UYARLA | `memory/feedback_aralikli-hata-avina-butce.md` | Bütçe + "kararı değiştirdi mi?"; bekçi kısmı alınmadı | aynı |
| `feedback_isaret-sozdizimi-onermeden-once-prior-art-ara.md` | UYARLA | `memory/feedback_isaret-onermeden-once-prior-art.md` | Arama yeri aXet skill referansları | aynı |
| `feedback_belge-incelemesinde-fable-kayit-duzeni-opus-tasarim.md` | UYARLA | `memory/feedback_belge-incelemesi-iki-tur.md` | Model adı yerine tur türü (kontrol listesi ↔ senaryo) | aynı |
| `feedback_gun-sonu-dal-pr-ile-maine-girer.md` | UYARLA | `skills/gun-sonu/SKILL.md` adım 8 (ayrı ders açılmadı) | Merge/dal silme `%commit-pr`'de; gün sonu birleştirmez | `-k test_skill` 19/19 |
| `feedback_kullaniciya-her-mesaj-turkce.md` | VAR | `core/00-temel.md` §12 "Türkçe, kısa, net" | — | — |
| `feedback_yeni-gelistirmede-ts-builddan-once-yazilir.md` | ALMA (B kulvarı) | `%sap-fs-ts-docs` / `%sap-dev` | SAP doküman/build sırası dersi | — |
| `feedback_bekci-yeniden-kurulunca-tabani-kayar…`, `feedback_ekran-teyidi-gorev-mesajinda…`, `feedback_infra-brifinde-kardes-kipleri…`, `feedback_seed-alanina-satir-ici-yorum…`, `feedback_wt-denetim-entegrasyon-dali…` | ALMA | — | Claude'a özgü (bekçi, SessionStart hook teyidi, `run_battery`, `seed_memory`, worktree denetimi) | — |
| `feedback_kapi-raporu-kaydi-verify-report-tuzaklari.md` | UYARLA (kısmi) | `reviewer-brief.md` §8 + `skills/code-review/SKILL.md` (madde başına tek satır) | `checklist_check --verify-report` ve transkript okuma Claude'a özgü → ALMA | `-k test_sap_skill_bilgi` 24/24 |
| `claude/memory-seed/_indeks-*` | ALMA | — | Brif gereği (`_indeks-*` alınmaz) | — |
| `tests/fixtures/izin_bekleme_taramasi`, `kanca_kablolama`, `tohum_yayilim_m4`, `seed_memory_hub_indeks` | ALMA | — | Ölçtükleri araçlar (izin bekleme tarayıcısı, kanca kablolaması, tohum dağıtımı) aXet'te yok | — |
| `tests/fixtures/parity_probe_diff`, `changelog_amend`, `olcum_yoklugu_sozlesmesi` | ALMA | — | `parity_probe.py`, İNFRA-CHANGELOG kapısı ve o validator'lar aXet'te yok; ölçüm-yokluğu ilkesi aXet'te her aracın KAPSAM satırıyla karşılanır (rule-coverage #38) | — |
| `maintenance/rule-coverage.md` | — | #2b yeni · #17, #18, #23, #41 notları · #18b, #18c, #22b yeni · §5 "Tur 8" satırı | — | — |

## Mutasyon sonuçları

| Mutasyon | Beklenen | Sonuç | Geri yükleme |
|---|---|---|---|
| `new_package.namespace_coz`: `musteri_govdesi` yerine bildirimsiz kabul | namespace RED testleri kırılır | 2 failure (21 test) | md5 `9495eada…` eşit |
| `new_package`: klasör `root/module/name.lstrip('/')` | `#ns#` klasör testi kırılır | 1 failure | md5 eşit |
| `new_package.ad_politikasi`: modül hep `None` | namespace kabul testi kırılır | 3 failure | md5 eşit |
| `session_brief.YAYINLAR_REF` kısa `origin/main:` | etiket gölgeleme testi kırılır | 1 failure (`test_ayni_adli_etiket_uzak_dali_golgelemez`) | md5 `85c0cd9f…` eşit |

## Son test koşuları (her biri ayrı komut)

`-k test_sap_stamp` 8/8 · `-k test_sap_skill_bilgi` 24/24 · `-k test_skill` 19/19 · `-k test_new_package` 21/21 · `-k test_package_naming` 13/13 · `-k test_new_project` 12/12 · `-k test_session_brief` 23/23 · `-k test_recall` 23/23 · `-k test_doctor` 144/144 (AGENTS şablonu düzeltmesinden sonra) · `python scripts/doctor.py` (izole XDG config) → `SONUÇ: 0 FAIL · 2 WARN` (commit'siz yüzey + lider kulvarının özel ajanları izole config'te kurulu değil).

## OTONOM KARARLAR

- Namespace bildirim anahtarı A1 ile aynı: `sap-project.json` → `customer_namespaces` (lider teyidi ①).
- Damga paragrafı A tablosunun altına, damga bölümünün İÇİNE kondu → proje `AGENTS.md`'ye de basılır; S1 aynı metinle eşitlendi.
- `sap_stamp.py` değiştirilmedi: mevcut desen ve A-D tamlık denetimi yeni metni kapsıyor (test yeşil).
- `new_package.py` A1 modülünü `sys.path` yerine `importlib.util.spec_from_file_location` ile yükler: kökteki `scripts/` ile `lib/utils` paket adı çakışmasın; `os.environ.setdefault("AXET_SAP_PROJECT_DIR", proje)` ile modülün proje kökü kuralı `--project-dir`'e eşitlenir (ortam önceden başka dizine ayarlıysa modül kendi fail-closed kuralıyla kapatır).
- Namespace'li kilit nesnesi adı `/<NS>/E<gövde>` yazıldı ama DOĞRULANMADI etiketiyle (ad politikası `E/<NS>/…` biçimini tanımaz; canlı ölçüm yok).
- `check_package_naming.py --package` namespace'li adı klasör biçimiyle de eşler (küçük, kendi sahipliğimde).
- `templates/project-sap/sap-project.json`'a `customer_namespaces: []` eklendi (JSON'da yorum yok; boş liste = Z/Y, `load_sap_project` bilinmeyen anahtarı reddetmiyor — ölçüldü).
- Rol brifinde FE-54/55/56 kimlikleri kullanılmadı (aXet `checklists.md`'de yok); madde kimliksiz.
- "KOD DONDU sonrası kapsam eklenmez" kuralı brif şablonuna yazılmadı; aXet alt görevi tek yanıtla döndüğü için yapısal karşılık alınmayanlar tablosunda.
- `core/00-temel.md`'ye yalnız 1 satır (133/150); CORE-ID'ye dokunulmadı.
- `doctor.py` 0 FAIL ölçümü izole config ile yapıldı (aşağıda): makinenin global config'i başka klonu (tüketici klonu) gösterdiği için doğrudan koşu 40 FAIL veriyor (37 skill ad çakışması + 3 `context_paths/skills_paths` bu worktree'yi göstermiyor) — çevresel, değişikliklerden bağımsız.
- `templates/project/AGENTS.md` namespace satırı yer tutucusu `<yok ya da /NS/>` biçiminde (içinde ters tırnak yok): ilk biçim (`<yok | `/<NS>/` …>`) doctor'ın yer tutucu doldurma testini kırdı (`test_agents_yer_tutucu`), düzeltildi.
- `role-briefs.md` S2 araç listesine başka bir kulvar (BAdI aracı) eşzamanlı `adt_badi_spot_read/_write` ekledi; `test_rol_brifingi_s2_…` arada 3 koşuda kırmızı, ekleme sonrası yeşil — benim S1/S5 bölümlerim etkilenmedi.
- Hafızada yeni dosyalar aXet ad biçimiyle (kısa ad, `name:` öneksiz); iç adlar (çekirdek repo adı, proje, kişi) yazılmadı.

## AÇIK KALAN

1. **Q349 sınıfı `guncelle.py` / `guncelle_proje.py`'de açık** (lider kararı ⑤: dokunulmadı). Öneri: `scripts/guncelle.py` (586-627, 789, 1913, 2917 civarı `origin/main` kısa adları) ve `scripts/guncelle_proje.py:154` → `refs/remotes/origin/main`; `core/00-temel.md` §11 istisna metnindeki `git show origin/main:` ifadesi de aynı tura. Test deseni: `tests/test_session_brief.py::YayinlarRefTest` (aynı adlı etiketle gölgeleme + kontrol grubu).
2. **`skills-sap/sap-adt-foundation/SKILL.md` (A2/A1 dosyası):** satır ~115 "Guard'lar (Z/Y öneki, …" ve ~124 `ADR_0005_B` satırındaki "Bilinen sınır: `/Z…/`, `/Y…/` dışındaki müşteri namespace'i de yasaklı sayılır — … bugün desteklenmiyor" cümlesi A1'in `ad_politikasi` değişikliğinden sonra güncel mi, sahibi doğrulamalı. Ayrıca rule-coverage #3 notundaki aynı cümle.
3. **Namespace'li kilit nesnesi biçimi** (`/<NS>/E…` mi `E/<NS>/…` mi) canlıda ölçülmedi — `new_package` şablon satırı DOĞRULANMADI etiketli.
4. **`doctor.py` doğrudan koşu** bu makinede global config tüketici klonunu gösterdiği için FAIL verir; worktree birleşip tüketici klonu güncellenince yeniden ölçülmeli (izole config: 0 FAIL).
5. Rol brifi öz-kapı ve S5 maddelerinin model davranışına etkisi ölçülmedi (metin).
