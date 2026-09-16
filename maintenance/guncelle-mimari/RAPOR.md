# GUNCELLE-MIMARI · Aşama 1 — aXet.code template repo mimari envanteri

Kaynak: `C:\axet` (dal `feat/2026-09-14-kurulum`, HEAD `c1a0d6f`, `git -C C:/axet log -1 --oneline`). Salt-okunur
inceleme; hiçbir repo dosyası değiştirilmedi (yalnız `git ls-files/log/show/diff` ve `Read`). Sınıflandırma betiği ve
ham çıktısı: `C:\IX\PROVA\.tmp\guncelle-mimari\classify.py`, `axet_files.txt`, `classify_output.json`.

Prior-art okundu (tekrar icat edilmedi): `maintenance/UPDATE-PROCEDURE.md`, `maintenance/rule-coverage.md`,
`maintenance/sync-rules.json`/`sync-lock.json`/`sync_check.py`, `README.md`, `docs/onboarding.md`,
`maintenance/IS-LISTESI.md` (KARAR bloğu satır 32-98 + kullanıcı cevapları satır 88-93, ikinci tur).

---

## 0. Ek kapsam (koordinatör talebi, iş sırasında İKİ KEZ eklendi) — nereye işlendi
- **(A) Silinen template dosyası artık SORULMAZ, GERİ GETİRİLİR** → §6 "kullanıcının sildiği skill" vakası ve döngü
  riski değerlendirmesi.
- **(B) Güncelleme-sonrası bütünlük turu** → yeni §8.
- **(C) İkinci tur kullanıcı kararları (Q1-Q4, 2026-09-15 AskUserQuestion)** → yeni §9 (proje katmanı güncellemesi,
  yayın modeli revizyonu, kritik kalem hatırlatması, günlük fetch bağlanma noktası).

---

## 1. Dosya sınıfları (412/412 sınıflandırıldı, 0 eşleşmeyen)

`classify.py` sıralı-regex ile **ilk eşleşen kural kazanır** tasarımıyla her dosyayı **tam bir** alt sınıfa atar
(kesin bölüntü/partition). Çıktı (`classify_output.json`): **412 dosyanın 412'si sınıflandı, 0 UNMATCHED**. Betikte
ayrıca her dosya için TÜM kuralları (yalnız birincisini değil) test eden bir "overlap" denetimi de var; 129 dosya
birden fazla *desenle* eşleşiyor ama bunlar kasıtlı özel→genel örtüşmeler (ör. bir validator hem `validator` hem
`skill-script` genel deseniyle eşleşir; ilk/daha özel kural kazanır) — **gerçek çoklu-sınıflandırma değil**, betiğin
sıra-mantığını doğrulayan bir iz. Aşağıdaki tablo nihai (birincil) atamayı gösterir.

| Kullanıcının istediği üst sınıf | Alt sınıf (script adı) | Sayı | Örnek yol |
|---|---|---:|---|
| **çekirdek kural** | `cekirdek-kural` | 2 | `core/00-temel.md`, `core/sap/00-sap.md` |
| **skill gövdesi** | `skill-govde` | 28 | `skills/*/SKILL.md`, `skills-sap/*/SKILL.md` |
| **skill referansı** | `skill-referans` (+`skill-referans-modul` alt-kümesi 2) | 74 | `skills-sap/sap-rap/references/eml.md` |
| **bilinen hata** (referansın alt-türü) | `bilinen-hata-referans` | 3 | `known-errors-adt.md`, `known-errors-classic.md`, `known-errors-ui5.md` |
| **validator** | `validator`(22, sap-adt-foundation) + `validator-ui5`(5) + `validator-diger-skill`(4) | 31 | `skills-sap/sap-adt-foundation/scripts/sapadt/lib/validators/check_*.py`, `sap-ui5-fiori/scripts/check_*.py` |
| **validator zinciri/eşleme** | `validator-zincir-map`(1) + `validator-gate-motor`(2: `gate.py`,`_reviewer.py`) + `validator-runner`(1: `run_review.py`) | 4 | `skills-sap/sap-code-review/references/validator-map.md` |
| **script (genel/kurulum)** | `kurulum-araci-script`(4) + `bakim-script-kok`(6) | 10 | `scripts/install.py`, `scripts/doctor.py`, `scripts/behavior_manifest.py` |
| **skill script'i** | `skill-script` | 79 | `skills-sap/sap-fs-ts-docs/scripts/build_doc_pdf.py` |
| **test** | `test-kok`(13, kök `tests/`) + `skill-test`(48) | 61 | `tests/test_doctor.py`, `skills-sap/sap-adt-foundation/tests/test_static.py` |
| **fixture** | `skill-fixture-sample` | 32 | `skills-sap/sap-ui5-fiori/tests/fixtures/app_good/...` |
| **ders/memory** | `ders-memory`(22: ekip) + `ders-memory-proje-sablon`(2: proje şablonunun kendi memory index'i) | 24 | `memory/feedback_*.md`, `templates/project/.axet-code/memory/MEMORY.md` |
| **config/izin** | `config-izin-kok`(4) + `proje-sablon-config`(6, proje şablonunun kendi config/izin dosyaları) | 10 | `config/permissions.json`, `.axetcode-denylist`, `templates/project/.githooks/pre-commit` |
| **proje şablonu** | `proje-sablon-diger`(2) + `proje-sablon-sap-json`(1) + `paket-sablon`(6) | 9 | `templates/project/AGENTS.md`, `templates/project-sap/sap-project.json`, `templates/package/*.tmpl` |
| **kurulum aracı** | `kurulum-araci-kok` | 3 | `kur.cmd`, `kur.ps1`, `yeni-proje.cmd` |
| **belge** | `belge-kok`(1) + `belge-docs`(3) + `bakim-repo-agents`(1, kök `AGENTS.md` — bakımcı-talimatı) + `skill-index-belge`(1) + `skill-implementation-belge`(1) | 7 | `README.md`, `docs/onboarding.md`, `AGENTS.md` (kök), `skills-sap/README.md`, `skills-sap/sap-adt-foundation/IMPLEMENTATION.md` |
| **bakım/iç** | `bakim-ic` | 9 | `maintenance/IS-LISTESI.md`, `maintenance/sync_check.py`, `maintenance/yayin_hazirla.py` |
| **lisans** | `lisans` | 4 | `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, `LICENSES/Apache-2.0.txt` |
| **skill asset/template içeriği** (istenen listede yoktu, ayrı tutuldu) | `skill-asset-template` | 22 | `skills-sap/sap-classic-abap/templates/*.abap`, `sap-adt-foundation/assets/.conn_adt.example` |

Toplam: 2+28+74+3+31+4+10+79+61+32+24+10+9+3+7+9+4+22 = **412**. ✔ (elle toplam kontrolü betiğin
`SINIFLANDIRILAN TOPLAM: 412` satırıyla eşleşiyor.)

**Not — sınıf sınırındaki özel dosyalar (dosya:satır ile):**
- `skills-sap/sap-adt-foundation/scripts/sapadt/lib/validators/_gate_status.py` betikte "validator" değil genel
  `skill-script`'e düştü çünkü adı `check_` ile başlamıyor; içerik itibarıyla bu **validator sözleşme/durum
  şeması**dır (`AXET-GATE-STATUS` biçimi), gate motoruna en yakın dosyalardan biridir — güncelleme sırasında
  validator ailesiyle BİRLİKTE ele alınmalı, `skill-script` genel kovasına gömülüp unutulmamalı.
- `scripts/check_package_naming.py` (kök) hem "bakım script'i" hem fiilen bir **validator**'dır (proje pre-commit
  zincirinde `project_precommit.py` tarafından çağrılır — `scripts/project_precommit.py`); "script" sınıfına
  düştü ama davranışı validator ailesine yakındır.

---

## 2. Yükleme yolu (sınıf → aXet'e nasıl ulaşır, ne zaman etkin olur)

| Sınıf | Mekanizma | Kanıt (dosya:satır) | Ne zaman etkin |
|---|---|---|---|
| çekirdek kural | global `options.context_paths` — `install.py` her oturumda tam metni gönderir | `scripts/install.py:172` (`ctx.extend([CORE_FILE...`) | `install.py` çalıştırılınca (bir kere); içerik değişikliği **anında** etkilidir (dosya her oturumda yeniden okunur, ayrı "derleme" yok) — YENİ bir aXet oturumu gerekir (README.md:48) |
| skill gövdesi/referansı/script'i/asset | global `options.skills_paths` (klasör), `%<skill-adı>` çağrısıyla okunur | `scripts/install.py:173-174`; keşif `scripts/doctor.py:261-303` `skill_envanteri` | Klasör zaten `skills_paths` altındaysa dosya değişikliği **bir sonraki `%skill` çağrısında** görünür (yeni oturum şart değil — skill dosyası her çağrıda okunur); klasör YENİ eklendiyse `install.py` yeniden koşmalı |
| ders/memory (ekip) | `context_paths` içindeki `memory/MEMORY.md` (yalnız indeks; kayıt dosyaları indeksten link'lenir) | `scripts/install.py:172` `TEAM_MEMORY`; `memory/MEMORY.md:1-7` | Oturum başı; `%recall`/`%remember` skill'i ile de okunur |
| ders/memory (proje) | proje `.axet-code.json` → `.axet-code/memory/MEMORY.md` proje-config `context_paths`'i | `scripts/doctor.py:937` (`.axet-code/memory/MEMORY.md` in ctx kontrolü) | Proje config'i varsa oturum başı |
| validator / validator zinciri | çalışma-zamanı Python import'u (`run_review.py` → `TASK_VALIDATORS`); aXet'e "yüklenmez", SAP yazma aracı (`adt_push_source` vb.) çağırdığında **süreç içinde** çalışır | `skills-sap/sap-code-review/references/validator-map.md:3,7-8` | Her SAP yazma çağrısında (kod değişikliği anında etkili — ayrı yükleme yok) |
| config/izin | global config `permissions.rules` (install.py birleştirir) | `scripts/install.py:175-183` | `install.py` yeniden koşulmalı (README.md:152: "Yeni kurallar ve skill'ler bir sonraki aXet oturumunda yüklenir" — ama izin kuralları `install.py` çalışmadan config'e yazılmaz) |
| proje şablonu | `new_project.py`/`new_package.py` proje köküne **kopyalar** (statik, sonradan senkronize OLMAZ) | `README.md:81-116`; `scripts/new_project.py:83-115` (kopyala-veya-atla, taban kaydı YOK — bkz. §9a) | Yalnız proje kurulum anında; sonraki template güncellemeleri var olan projeye OTOMATİK yansımaz — bu, tüketici-güncelleme mimarisinin `%guncelle-proje`'nin var olma SEBEBİDİR |
| kesin yasak damgası (proje şablonunun özel bir alt-akışı) | `core/sap/00-sap.md` kanonik blok → `sap_stamp.kanonik_blok()` → proje `AGENTS.md`'ye BASLA/BITIR damga | `scripts/sap_stamp.py:16-27`; yazan: `scripts/new_project.py:118-135` | `new_project.py --sap` basar/yeniler; `doctor.py:955-968` `check_stamp` her `doctor.py` koşusunda kanonikle karşılaştırır — **damga güncelliği mekanik olarak doğrulanabilir**, otomatik güncellenmez |
| kurulum aracı | `kur.cmd`/`kur.ps1` doğrudan indirilip çalıştırılır (README.md:37-39) | `kur.ps1:8` (`git pull --ff-only`), `:540` | Kullanıcı elle çalıştırdığında |
| bakım/iç, lisans, belge | hiçbiri aXet'e yüklenmez (maintainer-only ya da statik metin) | `AGENTS.md:4-5` (kök) — "Bu dosya yalnız bu template reposunun KENDİSİ üzerinde çalışırken yüklenir"; `yayin_hazirla.py:27` `maintenance/` public sürüme hiç GİRMEZ | — |
| test | hiçbiri aXet çalışma zamanına yüklenmez; yalnız `python tests/run_tests.py` / `skills*/tests/run_tests.py` ile elle/CI'de koşulur | `tests/run_tests.py:36` (`unittest discover`) | Bakımcı komut satırında |

---

## 3. Bağımlılıklar (kırılgan eşler — birini güncellemek diğerini de zorunlu kılar)

| Kaynak değişirse | Eş dosya güncellenmeli | Zorlayan mekanizma | DOĞRULANMADI/kısıt |
|---|---|---|---|
| `run_review.py` `TASK_VALIDATORS` / `_reviewer.py` eşlemeleri | `skills-sap/sap-code-review/references/validator-map.md` §1-2 | `skills-sap/sap-code-review/tests/test_checklists.py:8-9` (kod↔tablo eşitliğini test eder — koddan türetme, elle liste yok) | test yalnız **run_review/_reviewer ile validator-map.md** eşitliğini zorlar; `check_package_naming.py` gibi validator ailesi dışı kalan dosyaları KAPSAMAZ |
| yeni `check_*.py` validator eklenir | `TASK_VALIDATORS`'a kayıt (`run_review.py`) + `validator-map.md` satırı + ilgili `checklist-*.md` kimliği | `test_checklists.py` "adı geçen her .py ... gerçekten var mı" (satır 6) — **var mı** kontrol eder ama **YENİ dosyanın zincire KAYITLI olduğunu** zorlamaz (dosya diskte olup zincire hiç girmemişse test bunu YAKALAMAZ; bkz. §8 boşluk B3) | |
| `core/sap/00-sap.md` KESİN YASAKLAR bölümü / `SAP-CORE-ID` | tüm proje `AGENTS.md` damgaları (`sap_stamp.kanonik_blok`) | `doctor.py:955-968` `check_stamp` (proje bazında, `doctor.py` KOŞULURSA) | Otomatik push YOK — her proje kendi `doctor.py`sini koşup FAIL görmeli; koşulmazsa sessizce bayatlar |
| `memory/MEMORY.md` indeksi ↔ `memory/feedback_*.md` dosyaları | ikisi birbirini yansıtmalı | **YOK** — `install.py`/`doctor.py`/testlerin hiçbiri bu çifti çapraz kontrol etmiyor (bkz. §8) | Bugün (2026-09-15) 21 disk dosyası = 21 referans (`grep -o 'feedback_[a-z0-9-]*\.md' memory/MEMORY.md \| sort -u` = 21; `ls memory/feedback_*.md` = 21) — **şu an tutarlı ama mekanik olarak zorlanmıyor** |
| `config/permissions.json` | `install.py` `RETIRED_RULES` (eski desen temizliği) + `tests/test_install.py` `IzinDesenUzunlukTest` (ask < deny uzunluk kısıtı) | `scripts/install.py:53-71`; `README.md:181-189` | Uzunluk testi VAR ama "yeni kural eski bir deny'ı gerçekten ezdi mi" canlı `axet-code run` ile ölçülmüyor (yalnız simülasyon, README.md:189: "ölçülmedi") |
| davranış yüzeyi dosyaları (proje: `AGENTS.md`, `.axet-code.json`, `.axetcode-denylist`, `.githooks/**`, `validators-local/**`; template: `AGENTS.md`, `.axetcode-denylist`, `config/permissions.json`, `core/**`, `skills/**`, `skills-sap/**`) | manifest hash'i (proje) / git commit+upstream durumu (template) | `scripts/behavior_manifest.py:6-19,38-41` | Proje tarafında onay KULLANICI TERMİNALİNDE `generate` gerektirir (aXet oturumu çalıştıramaz — bash deny `*behavior_manifest.py*generate*`, `config/permissions.json:20`) |
| `sync-rules.json` (IX→aXet aktarım kuralı) | `sync-lock.json` hash'i | `maintenance/sync_check.py:230-234` (`--update-lock`, yalnız KURALSIZ=0 iken) | Bu zincir **aXet'in kendi güncelleme mimarisine değil, IX(DEV_CORE)→aXet bakımcı aktarımına** aittir — GUNCELLE-MIMARI'nin hedefidir farklı: `%guncelle` **aXet→tüketici** yönünü, bu zincir **IX→aXet(bakımcı)** yönünü kapsar. İkisi karıştırılmamalı |
| skill `SKILL.md` frontmatter (`name`, `description`) | klasör adı = `name`; `description` ≤1024 karakter | `scripts/doctor.py:94-121,624-638` `frontmatter_problems`/`check_template` | Mekanik, `doctor.py` her koşuda kontrol eder |
| `AGENTS.md` `- SAP` satırı ↔ proje `sap-project.json` | `sap_profile`/`master_language` tutarlı olmalı | `scripts/doctor.py:780-841` `sap_satiri_denetle`/`check_sap_satiri` | Mekanik, ÇELİŞKİ → FAIL |

**Genel gözlem:** aXet'te **hiçbir hook/pre-commit engeli** validator-zincir/dosya bütünlüğünü commit ANINDA
zorlamıyor (README.md:177 "Hook yok"); bütünlük yalnız (a) `doctor.py` elle koşulursa, (b) ilgili skill'in kendi
`tests/run_tests.py`'si elle koşulursa görünür. Bu, tüketici güncellemesinin **sonunda** neden bir "bütünlük turu"
gerektirdiğinin temel sebebidir (§8).

---

## 4. Test haritası

| Takım | Komut | Kapsadığı sınıf(lar) | Ön koşul | Süre (ölçülen kanıt) |
|---|---|---|---|---|
| Kök template testleri | `python tests/run_tests.py` | script (kurulum/bakım), config/izin (`test_install.py`), proje şablonu (`test_new_project.py`, `test_new_package.py`), davranış yüzeyi (`test_behavior_manifest.py`), damga (`test_sap_stamp.py`), pre-commit (`test_precommit.py`), `doctor.py` (`test_doctor.py`), `session_brief.py`, `kur.ps1` (`test_kur.py`), paket adlandırma (`test_package_naming.py`) | Repo dışı izole çalışma dizini önerilir — **PROVA-içi TMP'de 28 yanlış FAIL ölçüldü** (bkz. aşağı) | **217 test / 758,2 sn** (`C:\IX\PROVA\.tmp\adim4-lider\kok2.txt:232`, repo-dışı TMP; bu ölçüm `feat/2026-09-15-adim4` dalına ait, HEAD `c1a0d6f`'ten farklı bir commit — büyüklük mertebesi için gösterge, güncel HEAD üzerinde YENİDEN KOŞULMADI) |
| `sap-adt-foundation` testleri | `python skills-sap/sap-adt-foundation/tests/run_tests.py` | validator (22 adet), validator zinciri (`run_review.py`, `gate.py`, `_reviewer.py`), skill script'i (`sapadt/*`), fixture yok (senaryo verisi kod içinde) | `.conn_adt` İÇERİĞİ okunmaz, bağlantı gerektirmez (sahte istemci); izole TMP önerilir | Yakın-dal ölçümü: **279 test / 234,7 sn** (`C:\IX\PROVA\.tmp\kilit-lider\tam.txt:289`, `feat/2026-09-14-kilit-kalici` dalı — DOĞRULANMADI: bu sayı güncel HEAD ile birebir aynı mı ölçülmedi, yalnız mertebe) |
| `sap-code-review` testleri | `python skills-sap/sap-code-review/tests/run_tests.py` | validator zinciri↔dosya bütünlüğü (`test_checklists.py`), abaplint sarmalayıcı, `released_successors.py` | — | Süre DOĞRULANMADI (bu koşuda ayrı ölçülmedi) |
| `sap-fs-ts-docs`, `sap-ui5-fiori`, `sap-gui-scripting`, `sap-abapgit-delivery` testleri | `python skills-sap/<ad>/tests/run_tests.py` | ilgili skill script'i + fixture (özellikle `sap-ui5-fiori/tests/fixtures/app_good|app_bad`) | `sap-ui5-fiori` Node/Playwright bağımlılığı ister (README.md:32); yoksa test SKIP olabilir — DOĞRULANMADI (bu turda koşulmadı) | DOĞRULANMADI |
| `office-docs`/`office-excel`/`office-slides` testleri | `python skills/<ad>/tests/run_tests.py` | skill script'i + fixture (`office-docs/tests/samples/ornek.md`) | isteğe bağlı pip paketleri (README.md:30) yoksa SKIP olabilir — DOĞRULANMADI | DOĞRULANMADI |
| **Test HİÇ OLMAYAN sınıflar** | — | **belge** (docs/*.md, README.md — hiçbir otomatik test yok, yalnız `doctor.py --live` dolaylı doğrular); **ders/memory** (MEMORY.md/feedback_*.md — §3'te işaretlendiği gibi index↔dosya eşleşmesi test edilmiyor); **bakım/iç** (`maintenance/*.py` script'lerinin KENDİ testi yok — `sync_check.py`/`yayin_hazirla.py` unittest'siz, yalnız elle/manuel akış); **lisans**; skill `sap-dev`, `sap-cds-ddic`, `sap-classic-abap`, `sap-odata-backend`, `sap-rap`, `sap-intake-triage` (yalnız `references/`+`templates/`, `tests/` klasörü YOK — `git ls-files` çıktısında bu skiller için `tests/` yolu hiç geçmiyor) | | | |

**Genel doğrulama:** `git ls-files` üzerinde altı skil için (`sap-rap`, `sap-cds-ddic`, `sap-dev`, `sap-classic-abap`,
`sap-odata-backend`, `sap-intake-triage`) `tests/` yolu **HİÇ geçmiyor** (bu turda doğrudan kontrol edildi). Bu,
"içerik yalnız metin/şablon (referans+template)" skillerin test kapsamı dışında kaldığını gösterir; güncellemede
bunların doğrulaması **yalnız `doctor.py` frontmatter + elle okuma** ile yapılabilir.

---

## 5. Mevcut yayın akışı ve KRİTİK bulgu (`yayin_hazirla.py`)

Akış: `maintenance/UPDATE-PROCEDURE.md` §1-6 (IX→aXet aktarımı) → `maintenance/yayin_hazirla.py` (public kopya
hazırlar) → kullanıcı elle `git remote add` + `git push` (script PUSH ETMEZ, yalnız komutu yazdırır:
`yayin_hazirla.py:143-145`).

**`yayin_hazirla.py` bugün her çalıştırmada TAMAMEN YENİ, ATASIZ bir git geçmişi kurar:**
- `main()` hedefin **BOŞ** olmasını zorunlu kılar: `hedef.exists() and any(hedef.iterdir())` → HATA (`yayin_hazirla.py:110-112`).
- İçerik kopyalanır (`kopyala()`, satır 56-71), sonra: `git("init", "-q", "-b", "main", cwd=hedef)` (**satır 139**)
  + `git("add", "-A", ...)` (**140**) + **tek** `git commit` (**141**).
- Önceki yayının commit geçmişiyle **hiçbir bağlantı kurulmaz** — script önceki `origin`'i fetch/pull etmiyor,
  var olan public klonu güncellemiyor; her seferinde sıfırdan `git init`.

**Sonuç — kullanıcının sorduğu soruya doğrudan cevap:** EVET, ikinci bir yayın bu haliyle koşulursa:
1. Yeni yayının commit'i, ilk yayının commit'iyle **ortak atası olmayan (unrelated history)** bir ağaçtır (içerik
   byte-eşit olsa bile blob/tree hash'leri aynı çıkabilir ama COMMIT nesnesi ve dolayısıyla `git log`/`git
   merge-base` zinciri farklıdır — farklı `git commit` çağrısı = farklı SHA, farklı ata zinciri).
2. `kur.ps1:540` `git pull --ff-only` bunu **kesin olarak reddeder** ("DURDU: git pull --ff-only başarısız") çünkü
   fast-forward mümkün değildir (ortak ata yok). **Bu, `kur.cmd`'nin BUGÜNKÜ tek güncelleme yolunu tamamen kırar.**
3. `%guncelle`'nin planlanan 3-yollu (taban/yerel/yeni) birleştirmesi de aynı nedenle çöker: `git merge-base
   <taban> <yeni>` **bulunamaz** (ortak ata yok) → "taban" kavramı tanımsız kalır, diff/3-way karşılaştırma
   yapılamaz.
4. Maintainer `git push --force` ile üstüne yazarsa (script bunu ÖNERMİYOR, yalnız düz `push -u origin main`
   yazdırıyor — satır 145): mevcut tüketicilerin klonundaki `main` ile uzak `main` **tamamen kopar**; sonraki
   `git fetch`/`pull` tüketici tarafında "diverged"/"refusing to merge unrelated histories" hatası üretir
   (git'in standart davranışı; bu repo-özel bir kod yolu değil, genel git semantiğidir — DOĞRULANMADI: bizzat bu
   iki-defa-yayın senaryosu canlı denenmedi, ama git'in unrelated-history reddi köklü ve iyi belgeli bir
   davranıştır).

**Kullanıcı kararı (Q2, 2026-09-15, ikinci tur — bkz. §9b için TAM revizyon):** seçim birimi **kalem değil,
YAYIN**dır: her yayın public geçmişe TEK commit olarak eklenir (kalem başına commit DEĞİL). Bu, aşağıdaki eski
"Model B/C" değerlendirmesini YER DEĞİŞTİRMEZ, YALNIZCA netleştirir — teknik çözüm AYNI kalır (public klonun
ÜSTÜNE commit, `git init` KALDIRILIR), granülarite netleşti. Ayrıntılı 5 adımlık dönüşüm planı: **§9b**.

| Model (tarihsel değerlendirme, artık Q2 ile netleşen: B) | Açıklama | ff-only/3-way etkisi | Sızıntı taraması etkisi |
|---|---|---|---|
| A — bugünkü (her yayında `git init`) | `yayin_hazirla.py` şu an bunu yapıyor | 2. yayından itibaren KIRAR (yukarıda kanıtlandı) | Her yayın "temiz sayfa"dır — sızıntı taraması `tara()` (satır 74-94) her seferinde SIFIRDAN, birikmiş geçmiş riski yok — **en güvenli tarama modeli** |
| **B — KARARLAŞTIRILAN: yayın başına TEK commit, public klonun ÜZERİNE** | Maintainer public repoyu da klonlar (`git clone <public>`), içeriği filtrelenmiş kaynakla eşitler (silme dahil), `git add -A && git commit` (yeni ata zinciri KORUNUR) | ff-only/3-way ÇALIŞIR (ortak ata var) | Her commit'in İÇERİĞİ (bugünkü gibi TÜM ağaç) taranır — script zaten tüm ağacı tarıyor, maliyeti düşük |

`GUNCELLE.md` bugün **repoda yok** (`find . -iname "GUNCELLE*"` → boş; `git log --all -- GUNCELLE.md` → boş) — bu
BEKLENEN bir durumdur (KARAR §7: "Yayından önce: ... GUNCELLE.md v1" henüz yazılmadı, aşama 2 girdisidir), gap
olarak değil, aşama-2-girdisi olarak not edildi.

---

## 6. Güncelleme yöntemi önerisi (sınıf başına) + 9 örnek vaka

Genel model (her sınıf için ortak iskelet): **taban** (son senkron edilen template sürümü) · **yerel** (tüketicinin
şu anki dosyası) · **yeni** (template'in güncel sürümü). `%guncelle` üçünü karşılaştırır.

| Sınıf | taban=yerel, yeni≠taban | taban≠yerel, yeni=taban | taban≠yerel VE yeni≠taban (ikisi de değişmiş) | Otomatik mi onaylı mı | Eş dosyalar | Test | Oturum yeniden başlamalı mı | Risk |
|---|---|---|---|---|---|---|---|---|
| çekirdek kural | yeniyi al | yereli koru | ÇAKIŞMA → listele, kullanıcı seçsin (satır bazlı büyük olasılıkla) | Onaylı (§11 istisnası kapsamında OKUMA, YAZMA kullanıcı onayıyla) | — | `tests/test_doctor.py` (frontmatter/boyut) yok ama `doctor.py check_template()` satır sayısı ≤150 kontrolü | EVET (yeni oturum) | Yüksek — her oturum yüklenir, hatalı içerik hemen etkiler |
| validator (yeni eklendi) | yeniyi al (yeni dosya) | — | — | Otomatik dosya kopyası + **onaylı** kayıt (validator-map.md/TASK_VALIDATORS'a bağlanma kullanıcı fark etmeden olabilir → onay şart) | `run_review.py` `TASK_VALIDATORS`, `validator-map.md` satırı, ilgili `checklist-*.md` kimliği | `skills-sap/sap-code-review/tests/test_checklists.py` + ilgili `sap-adt-foundation/tests/run_tests.py` | Hayır (skill dosyası, sonraki çağrıda etkin) | Orta — zincire bağlanmazsa "sessiz no-op" (dosya var ama hiç çağrılmaz) |
| **kullanıcının gevşettiği validator + bizim bug düzeltmemiz** | ÇAKIŞMA: yerel "gevşetilmiş" (ör. bir kontrolü WARNING'e düşürmüş), yeni "bug düzeltmesi" (farklı bir mantık hatası) | — | — | **ASLA otomatik EZME** — üç-yollu diff'te ikisi de değişmiş sayılır → kullanıcıya iki değişikliği YAN YANA göster ("sizin değişikliğiniz: X · bizim değişikliğimiz: Y · ikisi de mi, biri mi?") | validator-map.md önem sütunu | önce/sonra `run_review.py --task <görev> --artifact <örnek>` ile aynı örnek dosya üzerinde iki sürümün ÇIKTISI karşılaştırılır | Hayır | Yüksek — sessiz otomatik-al kullanıcının bilinçli gevşetmesini sessizce geri sıkılaştırır (ADR 0005 B tarzı "kullanıcı kararı" ihlali riski) |
| **yeni skill** | yeni klasör → kopyala | — | — | Otomatik (yeni dosya, çakışma yok) | Global/proje `skills_paths`'e otomatik eklenmez — zaten `skills/` ve `skills-sap/` kökleri baştan `skills_paths`'te (`install.py:173-174`), klasör içine yeni SKILL.md düşmesi yeter | `doctor.py --skills` (frontmatter, ad çakışması) | Hayır (yeni oturumda `%<ad>` çağrılabilir; `doctor.py` skill envanteri ise `--skills` ile ANINDA) | Düşük |
| **kullanıcının sildiği skill (GÜNCELLENMİŞ VAKA — kullanıcı kararı 2026-09-15)** | yerel silinmiş, yeni değişmemiş → **silinmiş kalır** (yeni=taban, restore GEREKMEZ) | — | **yerel silinmiş VE template bu dosyayı güncellemiş (yeni≠taban)** → **ARTIK SORULMAZ, GERİ GETİRİLİR**; değişiklik listesinde AÇIKÇA bildirilir: `GERİ GETİRİLDİ: <dosya> (yerelde silinmişti, template'te güncellenmiş)` | Otomatik geri getirme + ZORUNLU log satırı (sessiz restore YASAK — kullanıcı şaşırmasın) | değişiklik listesi (KARAR §7: "her değişiklik tek commit + liste kalemi"; §9b'de yayın-başı commit olarak revize edildi, DOSYA-düzeyi liste kalemi kavramı YİNE geçerli) | `doctor.py --skills` ad çakışması + frontmatter | Hayır | **Döngü riski (kullanıcının istediği ek değerlendirme):** kullanıcı skill'i BİLİNÇLİ olarak istemiyorsa (ör. kurumsal politika, disk/bağlam tasarrufu) ve bakımcı o skill'i düzenli güncelliyorsa → HER `%guncelle` çalıştırmasında yeniden geri gelir → sil→çalıştır→geri gel→sil döngüsü. **En sade çözüm (KARAR'la çelişmeyen):** ayrı bir "yoksay listesi"/opt-out DOSYASI EKLEMEMEK (KARAR madde 5: ayrı kullanıcı katmanı YOK) — bunun yerine HER geri getirmede GÖRÜNÜR bir log satırı basmak yeterli: kullanıcı sorunu (istemediği skill) her seferinde AÇIKÇA görür ve isterse (a) manuel silmeye devam eder (döngü kabul edilebilir maliyettir — %guncelle nadiren, ör. ayda bir çalışır, ayrıca §9d'deki günlük-fetch bildirimi zaten "N yeni kalem" der, %guncelle'nin KENDİSİ günde bir çağrılmayabilir), ya da (b) `%template-oneri`/GitHub issue ile bakımcıdan o skill'i template'ten TAMAMEN kaldırmasını ister (KARAR §6 öneri kanalı, yayından sonra). **Döngüyü otomatik kapatan bir mekanizma İSTENMEDİ ve önerilmiyor** — kalıcı silme isteği kalıcı bir template kararı olmalı, tüketici-yerel bir bypass değil (aksi, "kesin yasak damgası ve SAP kapısı farkı engellenmeden raporlanır" ilkesiyle aynı felsefede: engellenmez ama HER ZAMAN görünür kılınır). |
| **MEMORY.md indeksi iki tarafta değişmiş** | — | — | taban≠yerel (kullanıcı kendi `%remember` kaydını eklemiş) VE taban≠yeni (bakımcı yeni ekip dersi eklemiş) → **SATIR-BAZLI BİRLEŞTİRME** (index bir madde-listesidir, çakışma NADİRDİR — ikisi de EKLEME ise git'in kendi 3-way merge'i genelde otomatik çözer; gerçek çakışma yalnız AYNI satır ikisi de değiştirdiyse) | Genelde otomatik (satır-ekleme birleşir); gerçek çakışmada onaylı | `memory/feedback_*.md` yeni dosyalar da birlikte gelmeli (index bir dosyaya işaret ediyorsa dosya da kopyalanmalı — bugün mekanik ZORLAMA YOK, bkz. §3/§8) | YENİ: index↔dosya çapraz kontrolü (bkz. §8 boşluk B1) | Hayır | Orta — index'e satır eklenip dosya unutulursa "kırık link" (bkz. §8) |
| **kesin yasak kanoniği değişmiş** | template `core/sap/00-sap.md` KESİN YASAKLAR bölümü değişti (yeni `SAP-CORE-ID`) | — | — | **Otomatik AMA hemen etkisiz** — proje `AGENTS.md` damgası `new_project.py --sap` KOŞULMADAN güncellenmez; `doctor.py check_stamp` bunu FAIL olarak gösterir (`scripts/doctor.py:955-968`) | proje `AGENTS.md` damgası (her SAP projesinde AYRI çalıştırılmalı; §9a'daki `%guncelle-proje` bunu OTOMATİKLEŞTİRİR) | `tests/test_sap_stamp.py` (kanonik bütünlük) + proje bazında `doctor.py` | template tarafı: yeni oturum yeter; PROJE tarafı: `new_project.py --sap` çalıştırılıp yeni oturum açılmalı | **Yüksek** — proje AGENTS.md damgası yenilenmeden yasaklar YİNE eski sürümde kalır (sessiz bayatlık; yalnız `doctor.py` FAIL'i ile görünür — koşulmazsa görünmez) |
| **izin/config değişmiş** (`config/permissions.json`) | yeniyi al | yereli koru (kullanıcı kendi kuralını eklemiş olabilir — proje `.axet-code.json`'da) | Şablon kuralı EZİLMEMELİ (`doctor.py:938-949` proje config'in şablon kuralını ezip ezmediğini kontrol eder) | Otomatik dosya + **`install.py` YENİDEN KOŞULMALI** (global config'e yazma işlemi ayrı adımdır) | — | `tests/test_install.py` (uzunluk/öncelik) | EVET — `install.py` sonrası yeni oturum | Yüksek — `install.py` koşulmazsa dosya değişse de global config bayat kalır (README.md:152 vurgusu) |
| **install.py değişmiş** | — | — | dosya doğrudan değiştirilir (kullanıcı elle DEĞİŞTİRMEZ varsayımı — template dosyası) | Otomatik al + **ÇALIŞTIR** (`python scripts/install.py`) ZORUNLU adım | `config/permissions.json`, `templates/project-sap/*` referansları (`AXET_HOME` sabitleri) | `tests/test_install.py` tam takım | EVET | Yüksek — install.py'nin KENDİSİ bozulursa (syntax hatası) sonraki `install.py` çağrısı çöker; `%guncelle` önce/sonra test ölçümü BUNU YAKALAR (dosya al → `python scripts/install.py --dry-run` dene → hata varsa GERİ AL) |
| **test dosyası değişmiş** | yeniyi al | yereli koru (tüketici kendi testini eklemiş olamaz normalde — testler template'e ait) | — | Otomatik | ilgili `check_*.py`/skill script'i (test tek başına anlamsız) | testin KENDİSİ koşulur (önce/sonra karşılaştırma tam da budur) | Hayır | Düşük |
| **kullanıcının kendi eklediği script** (template'te KARŞILIĞI OLMAYAN, tüketicinin `skills/<ad>/scripts/` veya proje `.axet-code/skills/` altına kendi eklediği) | — | — | template bu dosyayı HİÇ TANIMIYOR (ne tabanda ne yenide var) → **DOKUNULMAZ** (3-yollu karşılaştırmanın kapsamı DIŞINDA — yalnız `sync-rules.json`/`GUNCELLE.md` listesindeki dosyalar taranır) | Otomatik: hiçbir işlem (yoksay) | — | — | Hayır | Düşük — ama YALNIZ template'in tanıdığı dosya kümesiyle sınırlı bir tarama yapılırsa güvenli; template TÜM proje ağacını "silinen/yeni" diye taramaya kalkarsa (yanlış tasarım) kullanıcının kendi dosyasını "silinmiş template dosyası" sanıp SİLMEYE ÇALIŞABİLİR — **GUNCELLE.md'nin kapsam listesi KESİN OLMALI, dizin taraması OLMAMALI** (tasarım notu, kod yazılmadı) |

---

## 7. Ajanın atlamasını mekanik olarak önleme (script'e bağlanabilecek adımlar)

Mevcut kodda **yeniden kullanılabilecek** parçalar (envanterlendi, hepsi bugün BAŞKA bir amaç için yazılmış ama
`%guncelle` motoru bunları BİRE BİR reuse edebilir):
1. **Sınıflandırma:** `maintenance/sync_check.py`'nin `first_rule()`/`fnmatch` mantığı (satır 78-82) — GUNCELLE.md'nin
   dosya→karar eşlemesi AYNI desende (`sync-rules.json` biçiminde) tutulabilir; sıfırdan yazmaya gerek yok.
2. **Hash karşılaştırma:** `behavior_manifest.py`'nin `_hash()` (satır turları normalize CRLF→LF, satır 45-47) ve
   `sapmalar()` (satır 81-89) fonksiyonları taban/yerel/yeni 3-yollu karşılaştırmanın ÇEKİRDEĞİ olarak
   REUSE edilebilir (bugün 2-yollu: canlı↔manifest; 3-yollu'ya genelleştirilebilir; bkz. §9a — proje tarafında bu
   manifest zaten TABAN adayıdır).
3. **Doğrulama sonrası rapor biçimi:** `doctor.py`'nin `add(status, msg)` + `KAPSAM —` satırı deseni (ör.
   `doctor.py:1066-1074`) her yeni script için ZATEN kurumsallaşmış bir "PASS/WARN/FAIL + ne bakılmadı" formatı —
   `%guncelle`'nin son raporu AYNI formatta üretilirse ajan atlayamaz: her kalem PASS/WARN/FAIL olarak listede
   durur, "eksik kalem" doğrudan FAIL sayılır (çıkış kodu 1).
4. **Manifest tazeleme reddi (sessiz atlamayı yapısal olarak imkansız kılan desen):** `install.py:297-299`
   "yazılan config geri okunduğunda farklı çıktı" doğrulaması — yaz+geri-oku-doğrula deseni `%guncelle`'nin her
   dosya güncellemesinde tekrarlanmalı (kopyaladım dedi ama diskte yok/farklı → FAIL, "yaptım" beyanına güvenme).
5. **Skill envanteri / ad çakışması taraması:** `doctor.py:223-350` `skill_envanteri` — yeni skill eklerken ad
   çakışmasını ZATEN mekanik tespit ediyor; `%guncelle` yeni skill kopyaladıktan SONRA bunu çağırmalı (ek kod değil,
   var olan `doctor.py --skills` çağrısı).
6. **Plan dosyası + FAIL-if-incomplete:** Bugün BÖYLE bir dosya YOK (`GUNCELLE.md` henüz yazılmadı) — bu, aşama
   2'nin somut çıktısı olmalı: `%guncelle` çalışırken bir geçici plan (`~/.axet-guncelleme-plani.json` gibi) yazıp
   her kalemi `bekliyor→uygulandi→dogrulandi` olarak işaretlemeli; script sonunda `bekliyor`/`uygulandi` (henüz
   `dogrulandi` değil) kalan kalem varsa **çıkış kodu ≠ 0** (doctor.py'nin `fails` sayacı deseniyle birebir aynı,
   `doctor.py:1075-1077`). Bu, "ajan bazı kalemleri atladı ama 'bitti' dedi" sınıfını YAPISAL olarak imkânsız kılar.

---

## 8. Güncelleme-sonrası bütünlük turu (koordinatör ek talebi B)

### 8a. Bugün REPODA VAR OLAN denetim araçları (envanter)

| Araç / komut | Kapsadığı | Çıkış kodu anlamı | Kanıt (dosya:satır) |
|---|---|---|---|
| `python scripts/doctor.py` | global config (context_paths/skills_paths/izin) · çekirdek boyutu · SAP kanonik/damga bütünlüğü · davranış yüzeyi sapması (proje+template) · skill envanteri+frontmatter+ad çakışması · proje iskeleti (AGENTS.md, yer tutucu, `.axetcode-denylist`, pre-commit kablolama, `.rules.md`/PAKETLER.md) · bağlam boyutu (200KiB WARN/1MiB FAIL) | `1` = en az bir FAIL var; WARN çıkış koduna YANSIMAZ (yalnız metinde görünür — `doctor.py:1075-1077`) | `scripts/doctor.py:1023-1077` |
| `python scripts/doctor.py --live` | + aXet'in bağlamı FİİLEN yüklediğini bir model çağrısıyla ölçer (CORE-ID/SAP-CORE-ID/MEMORY-ID/PROJECT-ID/PROJECT-MEMORY-ID/SAP-STAMP-ID satırları) | Aynı (`1` FAIL varsa) | `scripts/doctor.py:992-1020` |
| `python scripts/behavior_manifest.py check [--project-dir]` | proje davranış yüzeyi (AGENTS.md, .axet-code.json, .axetcode-denylist, sap-project.json, .githooks/**, validators-local/**, .axet-code/skills/**, .axet-code/commands/**) manifest'le eş mi | `0` eş · `1` sapma · `2` manifest yok/okunamaz | `scripts/behavior_manifest.py:194-254` |
| `python scripts/behavior_manifest.py check --template` | TEMPLATE'in KENDİ davranış yüzeyi (AGENTS.md, .axetcode-denylist, config/permissions.json, core/**, skills/**, skills-sap/**) commit'siz/upstream'e gitmemiş değişiklik taşıyor mu | `0` es · `1` sapma · git yoksa `ÖLÇÜLEMEDİ` (yine de `0` döner — DOĞRULANMADI: bu satırda dönüş kodu kontrol edilmedi, kodda `return 0` sabit görülüyor `behavior_manifest.py:214`) | `scripts/behavior_manifest.py:156-214` |
| `python maintenance/sync_check.py --source ...` | **YALNIZ IX→aXet bakımcı aktarımı** (KURALSIZ/YENİ/DEĞİŞEN/SİLİNEN dosya + kural hijyeni) — **tüketici güncellemesiyle İLGİSİZ**, yalnız bakımcının kaynağı aXet'e taşırken kullandığı araç | `0` temiz · `1` KURALSIZ/eksik hedef · `2` kural hatası · `3` kullanım/git hatası | `maintenance/sync_check.py:18` |
| `python tests/run_tests.py` | script/config/proje-şablonu/davranış-yüzeyi/damga birim testleri (repo-dışı izole dizin ŞART — bkz. §4 not) | `0`/`1` (`unittest` `wasSuccessful()`) | `tests/run_tests.py:44,48` |
| `python skills-sap/sap-adt-foundation/tests/run_tests.py` (özellikle `test_static.py`) | **(a)** tüm `.py` derlenebiliyor mu (`test_derleme`) **(b)** yasak dizgeler: `C:\IX`, `DEV_CORE`, `mcp`/`fastmcp`/`mcp_servers` import'u, `CLAUDE_PROJECT_DIR`, `.conn*`/`*.env` gerçek dosyası, `.conn*.example` içinde yer-tutucu-dışı değer **(c)** `gate_atlatma_taramasi`: AST ile "yazma metodunu ÇAĞIRAN dosya `check_write` de çağırıyor mu" — validator ZİNCİRİNİN AŞILMADIĞINI kanıtlar; tarama `KOK = H.SKILLS_SAP` yani `skills-sap/` KÖKÜNÜN TAMAMI (yalnız sap-adt-foundation değil), ama yazma-metodu deseni yalnız `sap_adt_lib.py`/`sap_client.py` biçimindeki isimlere göre kurulu | `0`/`1` | `skills-sap/sap-adt-foundation/tests/test_static.py:14,17-24,67-70,124-140` |
| `python skills-sap/sap-code-review/tests/test_checklists.py` (`run_tests.py` içinde) | checklist satır biçimi + kimlik tekliği + **"görev→check_x.py(ÖNEM) zincirde mi"** + **adı geçen HER .py/.md/%skill/adt_*/skill-kimliğinin GERÇEKTEN VAR OLDUĞU** + `validator-map.md` ↔ `run_review.py`/`_reviewer.py` eşitliği + SKILL.md frontmatter + iz/kimlik sızıntısı yasağı | `0`/`1` | `skills-sap/sap-code-review/tests/test_checklists.py:4-11` |
| `python maintenance/yayin_hazirla.py --hedef <boş> --yalniz-tara` | public yayın öncesi sızıntı taraması (şirket adı, iç kullanıcı/dizin, iç repo adı `DEV_CORE`/`PROVA`, müşteri izi, oturum linki, dışlanan dosyaya atıf, örnek alan adı) + zorunlu dosya/NOTICE yol varlığı | `0` temiz · `1` bulgu var (yalnız TARA modunda, git kurulmaz) | `maintenance/yayin_hazirla.py:74-94,129-135` |

### 8b. BUGÜN HİÇBİR ARACIN YAKALAMADIĞI boşluklar (envanter + kapanış önerisi)

| # | Boşluk | Kanıt (bugün neyin BAKILMADIĞI) | Kapanış: var olan aracın kapsamını genişletme mi, YENİ kontrol mü |
|---|---|---|---|
| B1 | **`memory/MEMORY.md` indeksi ↔ `memory/feedback_*.md` dosya varlığı** çapraz kontrolü yok (index'te link olup dosya silinmiş / dosya var olup index'te unutulmuş) | `grep -rln "MEMORY.md\|memory/feedback"` yalnız `test_behavior_manifest.py`/`test_doctor.py`/`test_install.py`'de YOL SABİTİ olarak geçiyor, İÇERİK çapraz kontrolü YOK (bu turda doğrulandı: `C:\axet` üzerinde çalıştırılan grep) | **Var olan aracın genişletmesi**: `doctor.py`'ye küçük bir `check_memory_index()` eklenebilir (regex `\[.*\]\(feedback_[^)]+\.md\)` çıkar, `memory/` dizin listesiyle iki yönlü fark al) — `test_checklists.py`'nin "adı geçen her .py/.md var mı" desenine BİREBİR benzer, aynı desen memory'ye UYARLANIR. **YENİ KONTROL sayılır → gate moratoryumu (5 şart + açık onay) gerektirir** çünkü yeni bir doğrulayıcı eklemektir. |
| B2 | **Skill `SKILL.md`'nin metninde andığı `scripts/`/`references/` dosyasının GERÇEKTEN VAR OLDUĞU** — bu kontrol YALNIZ `sap-code-review` skill'inin KENDİ referansları için var (`test_checklists.py`), diğer 27 skill için YOK | `test_checklists.py` `REFS = SKILL / 'references'` sabiti YALNIZ `sap-code-review` klasörüne bakıyor (satır 15) | **Var olanı GENELLEŞTİRME** — aynı "adı geçen dosya var mı" AST/regex taraması TÜM `skills(-sap)/*/SKILL.md` + `references/*.md` için genel bir script'e çıkarılabilir (`check_package_naming.py` tarzı genel-amaçlı bir `scripts/check_skill_refs.py`). Yeni script = **gate moratoryumu** (5 şart) kapsamında, kullanıcı onayı gerekir. |
| B3 | **Yeni bir `check_*.py` validator dosyası diske düşer ama `TASK_VALIDATORS`/`validator-map.md`'ye HİÇ bağlanmazsa** bunu YAKALAYAN bir test yok (`test_checklists.py` yalnız TABLODA ADI GEÇEN dosyaların var olduğunu doğrular — TERSİNİ, yani "diskte olup tabloda adı GEÇMEYEN validator dosyası" taramaz) | `skills-sap/sap-code-review/tests/test_checklists.py` kaynak kodu okundu (satır 6 "adı geçen her .py ... gerçekten var mı" — tek yönlü) | **Var olan test dosyasının genişletmesi** (aynı dosyada, TERS yönlü bir kontrol eklemek) — küçük, düşük riskli bir EKLEME; yine de yeni bir ASSERTION eklemek "yeni kontrol" sayılabilir → kullanıcıya bildirilmesi önerilir (küçük ölçekli olduğu için "5 şart" tam gerekmeyebilir, ADR 0019 sınırında — karar kullanıcının). |
| B4 | **Genel repo-çapında markdown içi göreli link kontrolü YOK** (`[metin](dosya.md)` biçimindeki bağlantıların hedefi var mı) — `grep -rln "markdown link\|link_check\|broken link" --include=*.py .` boş sonuç verdi (bu turda ölçüldü) | Bu turda ölçülen negatif sonuç: repo genelinde link-checker script'i BULUNAMADI | **YENİ KONTROL** — repo hiçbir yerde bunu yapmıyor; `README.md`, `docs/onboarding.md`, `AGENTS.md` (kök), skill referansları birbirine çokça link veriyor (`[...](...)`  biçiminde onlarca örnek — ör. `README.md` "Yapı" tablosu, `maintenance/UPDATE-PROCEDURE.md` başlığı). Kapanış: genel-amaçlı `scripts/check_markdown_links.py` (tüm `.md` dosyalarını tara, `](...)` içindeki göreli `.md`/dosya yollarını `Path.exists()` ile doğrula, harici `http(s)://` atlanır) — **gate moratoryumu** kapsamında, kullanıcı onayı ZORUNLU. |
| B5 | **Skill → script/referans atıflarının TERSİ** (bir `scripts/*.py` dosyası hiçbir `SKILL.md`'den referans edilmiyorsa "yetim script" — orphan) | Doğrudan ölçülmedi; `check_reuse_gate.py` (validator ailesinde) benzer bir "yeniden kullanım" denetimi yapıyor ama SAP obje kodu için, template'in KENDİ script dosyaları için değil | **YENİ KONTROL** (düşük öncelik — yetim script zararsızdır, yalnız bakım borcu) |
| B6 | **`.gitignore`/`.axetcode-denylist` ile GERÇEKTEN neyin engellendiği canlı ölçülmedi** — `README.md:214-217` bunu zaten "Bilinen sınırlar" olarak İTİRAF EDİYOR ("Denylist davranışı" `doctor.py` KAPSAM satırında "bakılmayanlar" listesinde: `doctor.py:1066`) | `README.md:214-217`; `doctor.py:1066` KAPSAM satırı | Bu bilinçli bir kapsam-dışı beyanı — YENİ kontrol istenirse `_lab/` tarzı canlı ölçüm gerekir (kod değil, deney) |

### 8c. "Kontrol FAIL → düzeltme döngüsü → yeniden ölç" akışı için öneri

Bugün repoda BÖYLE bir döngü YOK (her araç tek-seferlik komut; ajan kaç kez tekrar deneyeceğine kendi karar verir —
mekanik sınır yok). Öneri (tasarım notu, kod YAZILMADI):
1. **Deneme sınırı:** `%guncelle` FAIL → düzelt → yeniden koştur döngüsü **en fazla 2 tur** otomatik olsun (ilk FAIL
   → düzelt → 2. ölç; 2. ölç de FAIL → DUR, kullanıcıya sor). Gerekçe: `core/00-temel.md` §1.1 STOP kuralının
   ruhu ile birebir aynı ("belirsizlikte forward progress yok") — bu proje `CLAUDE.md`'sinde zaten var olan bir
   ilke, aXet tarafına YİNE UYGULANMALI.
2. **Geri dönüş seçeneği:** her `%guncelle` çalıştırması ÖNCE bir `git stash`/yedek dal (`yedek/<tarih>` — KARAR
   §7'de `kur.cmd -Sifirla` için zaten öngörülen desenin AYNISI, `IS-LISTESI.md:37`) açsın; 2. turda da FAIL ise
   otomatik `git checkout <yedek dal>` ile GERİ AL, kullanıcıya "2 denemede kapanmadı, değişiklikler geri alındı,
   ayrıntı: <rapor yolu>" mesajı bassın. Bu, `doctor.py`'nin "FAIL varsa ilerleme"yi kesin engelleyen deseniyle
   (çıkış kodu 1 → gate) tutarlıdır.
3. Yeni bir gate/kontrol EKLEMEK (B1-B5) `core/00-temel.md`'nin (bu envanterin kendisinin de tabi olduğu) **gate
   moratoryumu** kuralına tabi: gerçek hata yaşanmış olmalı, geri alınamaz/sessiz olmalı, başka katman yakalamıyor
   olmalı, önce doküman denenmiş olmalı, kullanıcı onayı AÇIK olmalı. Bu envanterin B1-B5 satırları bu 5 şartın
   İLK ÜÇÜNÜ (yaşanmışlık, sessizlik, katman-eksikliği) KANITLA doldurur ama **4. ve 5. şart (önce-doküman-denendi,
   açık-onay) bu görev kapsamında SAĞLANMADI** — aşama 2'de kullanıcıya AYRI VE TEK TEK sunulmalı.

---

## 9. İkinci tur kullanıcı kararları (2026-09-15, AskUserQuestion) — mimariye etkisi

### 9a. (Q1) Proje katmanı güncellemesi — `%guncelle-proje`

Karar: proje açılınca doctor/oturum özeti "proje şablonu eski" der; `%guncelle-proje` AYNI 3-yollu yöntemle proje
kökünü günceller, proje başına AYRI onay. Genişletilmiş envanter — proje köküne DÜŞEN her şablon dosyası + yazan
araç + BUGÜN taban (sürüm) kaydı var mı:

| Dosya/dizin (proje kökünde) | Kaynağı | Yazan araç | Bugün taban (sürüm) kaydı VAR MI? |
|---|---|---|---|
| `AGENTS.md` (gövde) | `templates/project/AGENTS.md` | `new_project.py:83-115` (kopyala; varsa VE aynıysa atla; varsa VE FARKLIYSA `"[VAR, dokunulmadı]"` — EZMEZ) | **HAYIR** — yalnız `current == text` eşitlik kontrolü (satır 93), sürüm/hash AYRICA saklanmaz |
| `AGENTS.md` içindeki KESİN YASAK damga bloğu | `core/sap/00-sap.md` kanonik blok | `new_project.py:118-135` → `sap_stamp.damgala()` | **EVET** — `SAP-STAMP-ID` satırı (`sap_stamp.py:16-27`) canlı karşılaştırılabilir taban; `doctor.py:955-968` her koşuda kontrol eder |
| `.axet-code.json` | `templates/project/.axet-code.json` | `new_project.py` (aynı kopyala-veya-atla) | HAYIR |
| `.axet-code/.gitignore` | `templates/project/.axet-code/.gitignore` | `new_project.py:97-99` (TEK istisna: içerik tam `*` ise güncellenir) | KISMİ — yalnız "varsayılan mı" testi, gerçek hash değil |
| `.axet-code/memory/MEMORY.md`, `project_is-listesi.md` | `templates/project/.axet-code/memory/*` | `new_project.py` (kopyala-veya-atla) | HAYIR |
| `.axetcode-denylist`, `.gitattributes`, `.gitignore` | `templates/project/*` | `new_project.py` (kopyala-veya-atla) | HAYIR |
| `.githooks/pre-commit` | `templates/project/.githooks/pre-commit` | `new_project.py` (kopyala-veya-atla; LF zorunlu, satır 109-113) | HAYIR (dosya kendisi) — proje `behavior_manifest.py generate` çalıştırılmışsa `.axet-code/behavior-manifest.json`'da bu dosyanın hash'i KAYITLI (`behavior_manifest.py:38-39` `PROJE_DIZINLER` içinde `.githooks`) |
| `validators-local/README.md` | `templates/project/validators-local/README.md` | `new_project.py` | HAYIR (dosya) — proje kendi `validators-local/*.py` eklerse o dosyalar `behavior_manifest.py` `PROJE_DIZINLER`'da (satır 39) kapsanır |
| `templates/package/*` (`.rules.md.tmpl`, `SPEC.md.tmpl`, `SESSION_NOTES.md.tmpl`, `README.md.tmpl`, `ref_docs/README.md.tmpl`, `folders.txt`) | `new_package.py` | DOĞRULANMADI (bu turda `new_package.py` kaynağı DETAYLI okunmadı, yalnız `README.md:109-116` üzerinden davranışı çıkarıldı) | DOĞRULANMADI |
| `sap-project.json` | `templates/project-sap/sap-project.json` | `new_project.py --sap` (aynı kopyala-veya-atla) | HAYIR |

**Sonuç:** Bugün template→proje kopyalama TEK KATMANLI bir "yoksa yarat, varsa VE aynıysa atla, varsa VE FARKLIYSA
DOKUNMA" korumasıdır (`new_project.py:91-102`) — 3-yollu (taban/yerel/yeni) karşılaştırma için gereken "taban"
(kurulum anındaki template hash'i) **hiçbir dosya için AYRICA saklanmıyor**, TEK istisna kesin yasak damgasıdır
(`SAP-STAMP-ID`, kanonik metnin kendisi taban görevi görür). **En yakın mevcut aday:** proje
`behavior_manifest.py generate` çalıştırılmışsa `.axet-code/behavior-manifest.json` o ANKİ proje dosyalarının
hash'ini tutar (`behavior_manifest.py:62-63,103-137`) — kurulum SONRASI İLK `generate` çağrısı YAPILDIYSA bu hash
fiilen "kurulum anındaki template sürümü" ile aynıdır (proje henüz değiştirilmemişse) ve `%guncelle-proje`'nin
TABAN'ı olarak REUSE edilebilir; ama (a) kapsamı `PROJE_DOSYALAR`/`PROJE_DİZİNLER` ile SINIRLI (AGENTS.md,
.axet-code.json, .axetcode-denylist, sap-project.json, .githooks/**, validators-local/**, .axet-code/skills/**,
.axet-code/commands/** — `behavior_manifest.py:38-41`) — `.axet-code/memory/*.md` VE `templates/package/*`'ten
türeyen dosyalar bu kapsamın DIŞINDA, taban hash'i YOK; (b) `generate` ÇALIŞTIRILMAMIŞSA (README.md:93 "Sonraki
adım" listesinde ADIM 2 — atlanabilir bir adım) taban HİÇ yoktur.

**Tasarım önerisi (aşama 2 girdisi, kod YAZILMADI):** `%guncelle-proje`'nin taban ihtiyacı `behavior_manifest.py`nin
kapsamını `templates/project/**`'in TAMAMINA (memory şablonları + `templates/package/**` dahil) genişletmesi VE
`new_project.py`'nin proje kurulumunun SON adımı olarak `behavior_manifest.py generate`'i OTOMATİK/hatırlatmalı
hale getirmesiyle (bugün "Sonraki adımlar" listesinde 2. madde, elle — `new_project.py:148-149`) çözülebilir.

### 9b. (Q2) Yayın modeli — yayın başı TEK commit (revize `yayin_hazirla.py` planı)

Karar netleşti: **kalem başına DEĞİL, YAYIN (release) başına tek commit.** Seçim birimi COMMIT DEĞİL, `%guncelle`'nin
CHANGELOG-türetilmiş kalem→dosya eşlemesidir (public commit'in İÇİNDEKİ hangi DOSYALARIN alınacağı `%guncelle`'nin
dosya-kopyalama seviyesinde seçilir, git seviyesinde değil).

`yayin_hazirla.py`'nin bu modele geçişi için gereken değişiklik (envanterlendi, YAZILMADI):
1. `--hedef` artık BOŞ bir klasör değil, **var olan public klonun ÇALIŞMA AĞACI** olmalı (bugünkü
   `if hedef.exists() and any(hedef.iterdir()): HATA` — `yayin_hazirla.py:110-112` — bu şart TERS ÇEVRİLMELİ: hedef
   `git remote get-url origin` ile doğrulanmış bir public klon OLMALI).
2. `kopyala()` (satır 56-71) mantığı KORUNUR (filtreli ağaç çıkarma — `DISLANANLAR`), ama hedefe yazmadan önce
   ESKİ ağaç TEMİZLENMELİ (ör. `.git` HARİÇ tüm dosyaları silip yeniden kopyalama) ki SİLİNEN dosyalar public
   tarafta da silinsin.
3. `tara()` (satır 74-94) AYNEN kalır — YİNE TÜM AĞACI tarar (yalnız diff değil); bu, ZATEN "her yayında sıfırdan
   tam tarama" ilkesini korur, DEĞİŞMEZ.
4. `git init` (satır 139) YERİNE: `git add -A` + `git commit -F -` (satır 140-141 AYNEN kalır, YALNIZ `init`
   çağrısı KALDIRILIR — public klon zaten kendi geçmişine sahip, yeni commit onun ÜSTÜNE gelir).
5. Push artık `push -u origin main` (satır 145, YALNIZ ilk yayında geçerli) DEĞİL, sıradan `git push origin main`
   (fast-forward, ikinci ve sonraki yayınlar) — `kur.ps1:540`'daki `pull --ff-only` ile BİREBİR UYUMLU hale gelir.
6. CHANGELOG kalem→dosya eşlemesi: bugün `README.md` "Değişiklik notu" bölümü (`README.md:241-271`) SERBEST METİN;
   `%guncelle`'nin dosya-düzeyinde seçim yapabilmesi için bu bölümün (ya da ayrı bir `GUNCELLE.md`/`CHANGELOG.md`
   yapısal alanının) her kalem için **etkilenen dosya listesini** MAKİNECE OKUNUR biçimde taşıması gerekir (aşama 2
   tasarım girdisi — bugün YOK: `README.md`'de böyle bir yapısal alan BULUNAMADI, DOĞRULANMADI değil, açıkça YOK).

Bu revize model, ORİJİNAL bulguyu (ikinci yayının `ff-only`'yi kırdığı) AYNEN geçerli kılar — kullanıcının Q2
cevabı FARKLI bir seçim-granülaritesi seçmiştir (kalem yerine yayın), ama git-geçmişi SÜREKLİLİĞİ sorunu ÇÖZÜLMESİ
GEREKEN AYNI teknik boşluktur; yalnız çözüm netleşti (yukarıdaki 5 adım). §5'teki "Model B" satırı bu revizyonla
BİREBİR aynıdır.

### 9c. (Q3) Kritik kalemler — seçili gelir, hatırlatma mekaniği

Karar: kritik kalemler seçili gelir, kullanıcı çıkarabilir, alınana kadar `doctor`/oturum özeti HER OTURUM
hatırlatır. Bugün BUNA EN YAKIN mevcut desen `doctor.py`'nin proje kontrolündeki FAIL/WARN KALICILIĞIDIR: ör.
`check_stamp` (damga farklıysa HER koşuda FAIL basar, `doctor.py:961-962`) ya da `bm.proje_denetle` sapma satırları
(HER koşuda listelenir, `doctor.py:906-916`). Aynı desen: kritik bir GUNCELLE kalemi alınmadığı sürece `doctor.py`
VE `session_brief.py` HER koşuda (WARN olarak, FAIL DEĞİL — kullanıcı henüz reddetmemiş, yalnız ertelemiş) bunu
basmalı. Bugün BÖYLE bir "bekleyen kritik kalem" DURUMU (proje bazında kalıcı bir liste) TUTULMUYOR — en yakın
emsal `.axet-code/memory/project_is-listesi.md`'nin "Ertelenmiş tetikler" bölümü (`rule-coverage.md:38` satırında
anılan yapı) — AYNI DOSYA "GUNCELLE bekleyen kritik kalemler" alt-başlığı ile REUSE edilebilir (yeni dosya
AÇMADAN).

### 9d. (Q4) Günde bir kontrol — bağlanma noktası

Bugünkü `session_brief.py`'de ZATEN bir "saatte en fazla bir `git fetch`" önbelleği VAR:
`FETCH_CACHE = Path.home() / ".axet-template-cache" / "last_fetch"` (`scripts/session_brief.py:32`),
`template_durumu()` fonksiyonu (satır 77-101) bunu kullanarak "template N commit geride" der. Kullanıcının istediği
**günde bir** (saatte bir DEĞİL) ve **kalem sayısı** (ham commit sayısı DEĞİL) bildirimi bu mekanizmanın İKİ
noktada FARKLILAŞMIŞ bir kopyası/uzantısı olmalı:
1. **Aralık:** `FETCH_CACHE` dosyasının zaman damgası saat yerine GÜN bazında karşılaştırılmalı (aynı dosya, farklı
   eşik — `session_brief.py:82-90` civarındaki karşılaştırma bloğu) YA DA ayrı bir
   `~/.axet-template-cache/last_guncelle_check` dosyası (GUNCELLE'ye özel, session_brief'in genel "template geride"
   uyarısından BAĞIMSIZ bir bildirim istenirse).
2. **Birim:** "N commit geride" (bugünkü, satır 100: `f"template {geri} commit geride..."`) yerine "N kalem" — bu,
   `README.md` "Değişiklik notu" bölümündeki (ya da aşama-2'de yapısallaşacak `GUNCELLE.md`/`CHANGELOG.md`'deki)
   sürüm-başlıklarının SAYISI anlamına gelir; ham `git rev-list --count` (commit sayısı) DEĞİL.
3. **Ağ yoksa sessiz:** bugün ZATEN bu davranış var — `session_brief.py:88-90`
   (`rc, _ = _git(AXET_HOME, "fetch", ...)` başarısızsa `not_ = " (fetch başarısız — son bilinen duruma göre)"` ile
   SESSİZCE devam eder, HATA FIRLATMAZ) — kullanıcının istediğiyle ZATEN TUTARLI, yeniden yazmaya gerek yok.
4. **Otomatik uygulama yok:** bugün de `session_brief.py` YALNIZ RAPOR üretir, hiçbir dosyaya yazmaz
   (docstring satır 7: "Proje dosyalarına yazmaz; model çağrısı yapmaz") — kullanıcının 4. şartıyla zaten UYUMLU,
   ek kısıtlama gerekmez.

**Bağlanma noktası özeti:** `session_brief.py` (`scripts/session_brief.py:32,77-101`) — `doctor.py` DEĞİL, çünkü
`doctor.py` bugün template için HİÇBİR git-fetch YAPMIYOR (yalnız `template_denetle()` ile commit'siz/upstream'e
gitmemiş YEREL değişiklikleri okur, `behavior_manifest.py:156-187` — ağ çağrısı YOK). Kullanıcının "doctor ya da
oturum özeti" ifadesindeki "doctor" muhtemelen `doctor.py check_template()`'in `bm.template_denetle()`'yi çağırma
biçimini (`doctor.py:642`) kastediyor olabilir — ama o fonksiyon FETCH YAPMAZ, yalnız YEREL git durumunu okur;
GÜNLÜK FETCH ihtiyacı olan kısım MUTLAKA `session_brief.py`'ye bağlanmalı (zaten TEK fetch-yapan script budur).

---

## Açık kalemler / DOĞRULANMADI listesi

- `yayin_hazirla.py` ikinci-yayın senaryosu (unrelated-history reddi) **canlı denenmedi**; git'in genel semantiğine
  dayanan bir çıkarımdır (kod okumasıyla doğrulandı: `git init` her seferde, ortak ata YOK — ama gerçek bir 2.
  `git push` denemesi bu turda YAPILMADI, YAPILAMAZ da: kod yazma/repo değiştirme yasak kapsamında).
  `behavior_manifest.py:214`'teki `--template` dalının git-yoksa-da `return 0` verdiği DOĞRULANMADI (kod okumasıyla
  şüphe edildi, çalıştırılarak teyit edilmedi — sandbox'ta gerçek git kurulu, bu dal tetiklenmedi).
- Skill test takımlarının (`sap-ui5-fiori`, `office-*`) isteğe bağlı bağımlılık eksikliğinde SKIP/FAIL davranışı
  DOĞRULANMADI (bu turda hiçbir test KOŞULMADI — görev talimatı "test koşman gerekmez" dedi, mevcut `.tmp` çıktıları
  kullanıldı; onlar da farklı feature dallarına ait, güncel HEAD ile birebir DOĞRULANMADI).
- `check_package_naming.py`in validator ailesiyle tam ilişkisi (`project_precommit.py` üzerinden çağrıldığı)
  `templates/project/.githooks/pre-commit` içeriği DERİNLEMESİNE okunmadı (yalnız `validators-local/README.md`
  okundu) — pre-commit'in `check_package_naming.py`'yi DOĞRUDAN çağırıp çağırmadığı DOĞRULANMADI.
- `new_project.py` çoğunlukla DETAYLI okundu (bu tur, §9a için); `new_package.py`, `yeni_proje.py` kaynak kodu
  DETAYLI okunmadı (yalnız README/rule-coverage üzerinden davranışları çıkarıldı).
- `sap-project.json` (kök, `C:\axet\sap-project.json`) `.gitignore`'da (`/sap-project.json` satırı) — İÇERİĞİ
  görev talimatı gereği OKUNMADI (yalnız varlığı `ls -la` ile görüldü).

## KAPSAM BEYANI (bu raporun BAKMADIĞI)

- SAP CANLI davranış (ADT push/activate) hiç test edilmedi/koşulmadı — bu envanter yalnız STATİK kod/doküman
  incelemesidir.
- `axet-code` runtime'ının (kapalı kaynak host uygulama) izin motorunun FİİLEN nasıl davrandığı bu görevde YENİDEN
  ölçülmedi; yalnız `README.md`/`config/permissions.json` içindeki ÖNCEDEN ölçülmüş notlar aktarıldı (kaynağı
  belirtilerek).
- `_lab/` ve `temp_docs/` klasörleri **gitignore'lu** (`.gitignore:2-8`), `git ls-files` kapsamı DIŞINDA — bu
  envanter yalnız GİT'E İZLENEN 412 dosyayı kapsar; `_lab/`'daki geçmiş ölçüm klasörleri (t1-t15 vb.) içerik
  olarak okunmadı (yalnız isim listesi görüldü).
- Worktree'ler (`C:\.wt\axet\*`) görev talimatı gereği kapsam DIŞI bırakıldı, hiç okunmadı.
- `maintenance/sync-rules.json` (130 KB) ve `sync-lock.json` (163 KB) İÇERİK olarak TAM okunmadı (yalnız başlık/
  yapı ve `sync_check.py`'nin onları nasıl kullandığı okundu) — dosya içindeki tekil kural satırları TEK TEK
  doğrulanmadı.
- Diğer 5-6 SAP skill'inin (`sap-cds-ddic`, `sap-classic-abap`, `sap-odata-backend`, `sap-rap`, `sap-dev`,
  `sap-intake-triage`) `references/*.md` içerikleri TEK TEK okunmadı; yalnız dosya varlığı/sayısı ve isimleri
  sınıflandırıldı.
- `maintenance/IS-LISTESI.md` bu görev SIRASINDA iki kez büyüdü (bakımcı/lider paralel çalışıyor) — bu rapor
  görevin BAŞINDA okunan sürüm + koordinatörün ALINTILADIĞI ikinci-tur satırları (satır 88-93) temel alınarak
  yazıldı; dosyanın en güncel hali TEKRAR okunmadı (olası ek büyüme DOĞRULANMADI).
