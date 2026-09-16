# ARŞİV — devam noktası DEĞİLDİR

> `maintenance/IS-LISTESI.md` "DEVAM NOKTASI" bölümünün 2026-09-15 gün sonundaki hâli (dal tablosu, gate turları, güncelleme mimarisi tartışması).
> Güncel durum: `maintenance/IS-LISTESI.md`. Buradaki 🔴/⬜/"çalışıyor" ifadeleri bayattır.

| Konu | Güncel durum (2026-09-15 gün sonu) |
|---|---|
| K1/D1, kilit, D3, adım 4 dalları | hepsi `feat/2026-09-14-kurulum`'a merge edildi; worktree'ler kapatıldı |
| Güncelleme mimarisi | kararlar IS-LISTESI §2 "G" bölümünde; tasarım `maintenance/guncelle-mimari/TASARIM.md` |
| "ESKİ yerel katman" tartışması | reddedildi (kullanıcı "7 madde ok"); yalnız burada tarihçe |

## ▶ DEVAM NOKTASI — 2026-09-15 sabahı buradan başla (gün sonu 2026-09-14)

> Bu bölüm yarın ilk iş okunur; iş bitince silinir, kalıcı bilgi ilgili satırlarda (K1, D1, D3, D11) durur.
> Bu makinede SAP bağlantılı iş yapılmadı; transport yok, açık kilit yok.

**Dallar ve worktree'ler** (hepsinin tabanı `0087228`, `feat/2026-09-14-kurulum`; remote/push YOK):

| Dal | Worktree | Son commit | Durum | Yarınki iş |
|---|---|---|---|---|
| `feat/2026-09-14-kurulum` | `C:\axet` (ana) | bu gün sonu commit'i | merge hedefi; kök 209 · foundation 255 test / 598 satır yeşil (`0087228`) | 3 dalı buraya al |
| `feat/2026-09-14-k1-d1-reviewer` | `C:\.wt\axet\k1-d1-reviewer` | `0f18b30` WIP | uygulama bitti · **bug gate BLOCKER** (B1–B5, ayrıntı K1/D1 satırı) · 2026-09-15 düzeltme ajanı ÇALIŞIYOR (B1 = a+b; a yalnız struct→DTEL zincirinde, genelleştirme kullanıcı kararı).<br>Durum (ajan, doğrulama bekliyor): B1–B5 kodu ve belgeleri tamam, K1/D1 modülü 59/59 senaryo · 26 test yeşil, code-review 45 OK.<br>Ek bulgu: ortak oturumun `Retry(total=3)` adaptörü (`sap_adt_lib.py:1170-1191`) bütçeli GET'i 4 kez deniyordu (asılı SAP'de 42,7 sn). Çözüm: yalnız gate alt sürecine retry'sız adaptör.<br>Ölçüm: asılı SAP'de `struct_creation` zinciri 75,7 sn → (a) ile BLOCKER. Süreyi bütçesiz WARNING validator'ı `check_standard_table_fields` (>120 sn) dolduruyor → açık kalem, "(a) genelleşirse" listesine.<br>**Düzeltme BİTTİ (2026-09-15):** ajan raporu `C:\IX\PROVA\.tmp\k1d1-fix\RAPOR.md` — B1 15 sn toplam bütçe (env yalnız düşürür) + gate sürecinde retry'sız adaptör + 30 sn sarmalayıcı zaman aşımı yalnız 4 DTEL zincirinde BLOCKER · B2 `adt_struct_create` fields[] her zaman, olmayan artifact BLOCKER · B3/B5 belge · B4 aday çıkarımı kenar vakaları; fail-first 9F+1E → yeşil; mutasyon 12/12.<br>**Commit `c9b5538`.** **Lider yeniden koşusu: 658/658 senaryo · 281 test · 0 failure** (scratchpad TMP, sahte kök). **Dar re-gate: WARNING** (rapor `C:\IX\PROVA\.tmp\gate-k1d1-re\RAPOR.md`):<br>**TUR 2 BİTTİ (2026-09-14 ~23:50, commit YOK):** rapor `C:\IX\PROVA\.tmp\k1d1-fix2\RAPOR.md`.<ul><li>Belge "her çağrıda" (4 yer, B3b).</li><li>Bütçe gerçek toplam süre sınırı oldu: `_sureli` iplik; damla 40 → 3,3-3,9 sn, asılı kurulum 30,6 → 3,3-3,8 sn; B1h d ile 503'e tek istek.</li><li>`_birlestir` normalize (B6).</li><li>D1f `_Taban` ADT_* temizliği (modül ve sınıf sırası 3/3).</li><li>Tek render `ddic_dtel.yapi_ddl_kaynagi`: create_structure ile gate aynı DDL (B7a/b).</li><li>Fail-first 6 kırmızı; mutasyon 12/12 (ajan önce yanlışlıkla 13/13 dedi).</li><li>Ajanın tam takım koşusu: foundation 676/676 · 290 test · sap-code-review 45 OK.</li></ul>**Lider doğrulaması:** sap-code-review **45 OK (skip 1) rc=0** (repo dışı TMP, `scratchpad/k1d1-lider2/scr.txt`) · foundation **676/676 senaryo · 290 test · 0 failure · rc=0** (cwd worktree, repo dışı TMP, `scratchpad/k1d1-lider2/tam.txt`).<br>**3. dar gate BAŞLATILDI:** tur 2 SAP yazma yolunu (`create_structure` DDL render) ve iplik davranışını değiştirdiği için "dar düzeltme" sayılmadı. Odak: eski ↔ yeni DDL bayt eşitliği ve iplik terkinde yanlış PASS yolu.<br>**3. gate: WARNING** (rapor `C:\IX\PROVA\.tmp\gate-k1d1-tur2\RAPOR.md`).<ul><li>MEDIUM gerileme: açıklamadaki satır sonu, gate'in aday çıkarıcısına ham `--`/`/*` satırı gösterip gerçek alanları gizliyor (probe: HEAD BLOCKER → yeni OK).</li><li>Render 11/11 bayt aynı; iplik bütçesinde yanlış PASS yok.</li><li>**Lider kararı:** açıklama ve etikette `\r \n U+2028 U+0085` → `validation_error` (ağa gitmeden), render fonksiyonu da reddeder; B7'ye `--` vakası; dar fail-first düzeltme, 4. gate yok. Aynı ajana verildi.</li></ul>**TUR 3 BİTTİ** (rapor `C:\IX\PROVA\.tmp\k1d1-fix3\RAPOR.md`):<ul><li>`ddic_dtel.SATIR_SONU_KARAKTERLERI` (CR LF U+2028 U+2029 U+0085) + `satir_sonu_ihlali`. Bakılan yerler: yapı açıklaması + alan description/name/type (ad ve tipte de gizleme ölçüldü).</li><li>Render ValueError → gate BLOCKER.</li><li>composite `validation_error` ağdan önce.</li><li>Fail-first: B7 5 FAIL → B7 48/48 · modül 122/122 · B7g HEAD bayt pini.</li><li>Mutasyon 8/8.</li><li>Ajan tam takım: foundation 720/720 · 295 test · sap-code-review 45 OK.</li><li>§18.8 + tool-catalog:362.</li><li>Lider diff okudu: `sap_client.py:2413` sarmalayıcısı `adt_client.create_structure`'ı `try` içinde çağırıyor → ValueError fail-closed.</li><li>Yeni açık: VT/FF/U+001C-1E kümede yok (satır sonu sayılıp sayılmadığı DOĞRULANMADI).</li></ul>**Lider tam takım (tur 3):** foundation **720/720 senaryo · 295 test · 0 failure · rc=0** · sap-code-review **45 OK (skip 1) rc=0** (repo dışı TMP, `scratchpad/k1d1-lider3/`).<br>**Commit `2796a52`** (tur 2+3) → kurulum dalına merge BAŞLADI (commit'siz).<ul><li>Çakışma yalnız `IMPLEMENTATION.md`. K1/D1 bölümü **§20** olarak dosya sonuna eklendi (§18 kilit, §19 D3 korundu).</li><li>§18→§20 atıfları: `IMPLEMENTATION.md:107`, `:454`, `check_struct_field_dtel_active.py:46`, `test_verdict_reviewer_k1_d1.py:560`.</li><li>Kalan §18'ler kilide ait: `test_kilit_politikasi.py:10`, `sap_adt_lib.py:3793`.</li><li>Birleşik sap-code-review **45 OK (skip 1) rc=0**. Foundation koşuyor (`scratchpad/birlesik-k1d1/`).</li><li>Kök takım DA koşulacak (foundation bitince; zamanlama testleri paralel yükte bozulmasın diye sırayla). Değişen dosyaların hepsi `skills-sap/` altında, ama kök `behavior_manifest`/`doctor`/`install` testleri `skills-sap`'e dokunuyor.</li></ul>**Açık kalemler:**<ul><li>Süreç içi ADT_* env mirası + env-önce guard (ölçüldü; aXet CLI'de yüzey düşük; `tools/diag.py` çoklu çağrı yolu).</li><li>IX MCP tarafı ayrı kalem.</li><li>Sarmalayıcı SKIP yazmayı durdurmuyor.</li><li>Tam takım D1f sıra bağımlılığını yapısal olarak gizliyor.</li></ul>
- MEDIUM: validator-map, run_review ve _reviewer belgeleri bayat.
- LOW: bütçe gerçek toplam süre değil. Damla sunucuda gate 90 sn+ sürüyor; sarmalayıcı 30 sn'de BLOCKER, yanlış PASS yok.
- Öneri: `_birlestir` normalize.
- Önceden var: D1f sıra bağımlı (env sızıntısı); `description` alanı gate'in görmediği DDL satırı üretebiliyor; sarmalayıcı SKIP'i.
- B1/B2/B4 doğrulandı (B4 fuzz: FN=0).

**Düzeltme turu 2 ÇALIŞIYOR** (aynı ajan). Lider kararları:
- gerçek toplam süre sınırı
- D1f izolasyonu
- description render'ı gate ile tek kaynak
- SKIP kalemine dokunulmaz

Rapor hedefi `C:\IX\PROVA\.tmp\k1d1-fix2\RAPOR.md`.

**⚠ Ölçülen açık kalem (ajan, 2026-09-15; DÜZELTİLMEDİ):** süreç içinde `.conn_adt` başka sisteme çevrilince bağlantı eski sistemde kalıyor.
- İlk `_get_client` çağrısı `.conn_adt`'yi `os.environ`'a yüklüyor (`sap_adt_lib.py:437-438`, override=False).
- Süreç yeniden başlamadan `.conn_adt` → B yapılınca reviewer ve `adt_struct_create` istekleri A'ya gitti, B'ye 0 istek. Sahte sunucu A/B ile ölçüldü.
- ADR 0010 süreç içi guard'ı (`_guard_binding_current`) reddetmedi: `project.effective_conn_value` env'i önce okuyor (`project.py:106-107`), yani env'i env ile karşılaştırıyor.
- Kanıt: `C:\IX\PROVA\.tmp\k1d1-fix2\kanit\urun_etkisi_env_sizinti.txt`.
- aXet yüzeyi (lider ölçümü): uzun yaşayan MCP sunucusu yok (ls-files ve kod araması 0). `sap_adt_cli.py` her çağrıda yeni süreç açıyor. Pratik risk yalnız tek süreçte çok çağrı yapan yollarda (populate toplu koşumu) ve koşum sürerken `.conn_adt` değişirse.
- DEV_CORE'daki uzun yaşayan MCP sunucusunda aynı sınıf olabilir; ayrı kalem, ölçülmedi.<br>⚠ Ölçülen yan etki (kullanıcıya bildirildi): 1 sn/GET yanıt veren sistemde 26 geçerli Z DTEL'li yapı → yanlış BLOCKER (bütçe ~14 denetime yetiyor; 0,3 sn'de geçiyor). `struct_creation` 1 sn'de ~25-26 sn (30'a yakın; ~9 sn `check_standard_table_fields`, bütçesiz).<br>Açık: validator-map §1'de 6 eşanlamlı eksik · programlarda yanlış `.clas/.intf.abap` tarama etiketi (taban) · struct yolunda sarmalayıcı SKIP yazmayı bloklamıyor | re-gate → merge (§18/§19 sonrası §20) |
| `feat/2026-09-14-kilit-kalici` | `C:\.wt\axet\kilit-kalici` | `4bc95a5` WIP | Uygulama bitti · **tam foundation 613/613 senaryo · 270 test, 0 failure** (2026-09-15, sahte kök + izole TMP, `C:\IX\PROVA\.tmp\kilit-tam\tam_takim.txt`).<br>**Bug gate: WARNING** (rapor `C:\IX\PROVA\.tmp\gate-kilit\RAPOR.md`):<br>• M1: aynı ya da başka kullanıcı 403'ünde Bug-11, bayat transport ile ikinci kilit deniyor; tüm-404 dalında PUT da bayat corrNr ile gidiyor.<br>• M2: test eksik.<br>• L1–L4.<br>**Düzeltme BİTTİ** (ajan; rapor `C:\IX\PROVA\.tmp\kilit-fix\RAPOR.md`, dalda §18.7–18.8):<br>• M1: Bug-11 yalnız sahipsiz 409'da koşuyor; `lock_object` başında `_last_lock_*` sıfırlanıyor. Tüm-404 dalında PUT'un bayat transportla gitmesi de kapandı.<br>• M2, L1–L4 kapandı.<br>• Yan etki düzeltildi: `hints.py:135` K-09 ipucu.<br>• Tam takım 622/622 senaryo · 279 test · 0 failure; mutasyon 17/17.<br>**Lider yeniden koşusu: 622/622 · 279 test · 0 failure** (`C:\IX\PROVA\.tmp\kilit-lider\tam.txt`). ADR 0006 gereği WARNING düzeltmesi dar ve fail-first testli olduğu için üçüncü gate açılmadı.<br>**Commit `80f7b9e` → MERGE `56db2f3`** (`feat/2026-09-14-kurulum`, 2026-09-15). Kurulum dalında 0087228'den beri foundation değişmemişti, birleşik foundation dalla aynı (`git diff 80f7b9e HEAD -- skills-sap` boş). Worktree kapatıldı, dal silindi.<br>**Açık:** push yanıtında kilit alanlarının üst seviyeye taşınması (sözleşme değişikliği) · aktivasyon öncesi unlock False iken aktivasyonun koşmaması · L3 yolları | 2. lider koşusu yeşilse commit → **D3'ten ÖNCE merge** |
| `feat/2026-09-14-d3-populate` | `C:\.wt\axet\d3-populate` | `4ceed2f` WIP | Uygulama bitti · tam foundation 677/677 satır, 304 test yeşil.<br>**Bug gate: WARNING** (rapor `C:\IX\PROVA\.tmp\gate-d3\RAPOR.md`):<br>• 1: araç istisnası koşumu durdurmuyor.<br>• 2: yinelenen CSV başlığı kabul ediliyor.<br>• 3: force yolunda silme mesajda yok.<br>• 4: cp1254 CSV traceback veriyor.<br>Düzeltme ajanı çalışıyor. Lider kararları: sonucu bilinmeyen hata → DURDUR · `auth_failed` → DURDUR (hesap kilidi riski) · 502/503/504 → DURDUR · msgclass `readback_failed` mesajı "PUT kabul, doğrulanamadı".<br>**Düzeltme BİTTİ** (rapor `C:\IX\PROVA\.tmp\d3-fix\RAPOR.md`, §19.10): sonucu bilinmeyen yazma (unexpected/connection_failed/502-504/step_exception) ve kimlik reddi (auth_failed/401) → `run_stopped` + `result.stop`; durum yalnız `^\[(\d{3})\] ` önekinden; yinelenen başlık → rc3 `csv_invalid`; UTF-8 dışı → rc3 `csv_unreadable`; force'ta SİLİNDİ öneki. Ajan: 749/749 · 319 test · 0 failure; mutasyon N01-N17+N06b öldü, M01-M15 + L3-L7 öldü, L1/L2 eşdeğer.<br>**Commit `e51f4d9` → MERGE `c1a0d6f`** (kilitten sonra). Çakışma yalnız IMPLEMENTATION §18 → D3 §19'a numaralandı, atıflar güncellendi; birleşik kodda `clear_enqueue_lock` çağrısı yok. **Birleşik tam foundation (kilit + D3, `c1a0d6f`): 773/773 senaryo · 343 test · 0 failure** (lider, sahte kök + scratchpad TMP; toplam kontrolü 598+24+151 · 255+24+64). D3 L1 mutasyonunun birleşik kodda tek başına yakalandığı YENİDEN KOŞULMADI.<br>Açık: `_err_from_exc` status_code yapısal alan değil (~50 çağrı) · durum taşımayan 13 `SAPADTError` · öneri 5 (ön geçiş yalnız kapı) · `C:\IX\PROVA\.tmp\d3-fix\tmp\node-compile-cache` elle silinecek (ajanın silmesi izin katmanında reddedildi) | birleşik takım yeşilse worktree kapat |
| ~~`feat/2026-09-15-adim4`~~ ✅ KAPANDI | ~~`C:\.wt\axet\adim4-kalanlar`~~ | taban `4b8f05b` | **✅ 2026-09-14 23:05 KAPANDI:** kurulum dalında birleşik kök takım **218/218 OK · 602 sn** (repo dışı TMP, `scratchpad/birlesik-adim4/kok.txt`). `git cherry` boş, junction yok. Worktree kaldırıldı, dal silindi (46c3b97 → merge 95d1357).<br>2026-09-15 açıldı; ajan: http `@` yolu + `new_project --no-next-steps` + doctor emekli izin deseni WARN (D5 merge sonrasına).<br>**3 iş bitti (ajan raporu, lider doğrulaması bekliyor):** kök takım 216/216 · 7 yeni test tabanda kırmızıydı · mutasyon 9/9 yakalandı · PYTHONUTF8'siz 119 OK (rapor `C:\IX\PROVA\.tmp\adim4\RAPOR.md`).<br>**Lider kararı:** yetki sınırı (`/?#`) kalıyor. Yol, sorgu ya da fragment içindeki `@` için ret değil UYARI verilecek; doctor'a "yalnız global config" kapsam satırı eklenecek. Bu ek sürüyor.<br>**Açık:** `*core.hooksPath*` deny ↔ new_project alt süreci · http dışı şemada sorgudaki `@`.<br>**Lider kök takım kontrolü: 217/217 OK** (repo dışı TMP, `C:\IX\PROVA\.tmp\adim4-lider\kok2.txt`; PROVA içi TMP ile 28 yanlış FAIL).<br>**Bug gate: WARNING** (rapor `C:\IX\PROVA\.tmp\gate-adim4\RAPOR.md`): F1 MEDIUM scp `a:b/c@d:e` origin sessizce bozulup AGENTS.md'ye yazılıyor (gerileme) · F2 MEDIUM N1/N7 mutantları kaçtı · F3-F5 LOW. **Düzeltme BİTTİ** (rapor `C:\IX\PROVA\.tmp\adim4-fix\RAPOR.md`):
- F1-F5 kapandı.
- Fail-first 7F+9E → yeşil.
- Mutasyon 11/11 (gate'in kaçırdığı N1/N5/N6/N7 dahil).
- Kök takım: "218 test · 0 failure · 0 error · 0 skip · 519 sn" (repo dışı TMP).
- Değişen beklenti: `https://kul:Pa#password=x@host/...` artık `yerel` önerir.

**Ek lider kararı BİTTİ:** git'te scp biçiminin parola sözdizimi yok, bu yüzden scp adresini değiştiren her temizleme → `yerel` + uyarı (`kul:gizli@host:yol` ve `host:u@x:y.git` dahil). Değişmeyen scp aynen önerilir. Açık `--repo` reddi aynen kalır.
- `yeni_proje.py:278-280`
- Kırmızı 3F → yeşil; mutasyon 12/12
- Ajan kök takım: "218 test · 0 failure · 0 error · 0 skip · 550 sn"

**Commit `46c3b97` → MERGE** (kurulum dalı, çakışmasız). **Lider birleşik kök takım koşusu ÇALIŞIYOR** (scratchpad TMP). | kök yeşilse worktree kapat |
| ~~`feat/2026-09-14-core-port`~~ | — | `8c0dc8d` | **KAPATILDI 2026-09-15:** junction yoktu (`dir /AL` boş), ağaç temiz, `git worktree remove` + `branch -d` | — |

**Yarın sırası:**
1. **K1/D1 düzeltmesi:** B1 (önerim a+b: ağ BLOCKER gate'i içeren zincirde zaman aşımı = BLOCKER + 404 sondası toplam süre bütçesiyle tek geçiş) · B2 (`struct_fields_dtel` fields[] üzerinde her zaman koşsun; `artifact_not_found` bu araçta BLOCKER) · B3 belge metinleri koda eşit · B4/B5. Sonra dar kapsamlı taze bug gate (sahte sunucu probları `C:\IX\PROVA\.tmp\devam-2026-09-14\gate-k1d1\`).
2. **D3 ve kilit dalları için taze bug gate** (ayrı ayrı, taze bug-expert). Kilit dalında önce tam foundation takımı.
3. **Merge:** 3 dal → `feat/2026-09-14-kurulum`. Beklenen çakışmalar (diff hunk'larıyla ölçüldü): `IMPLEMENTATION.md` §18 **üç dalda** (K1D1, kilit, D3) → §18/§19/§20 olarak ayrılır · `sap_adt_lib.py` `SAPLockError` sonrası: kilit `@@ -105 +106,11` (`KILIT_CAKISMA_TARIFI`) ile D3 `@@ -118 +119,36` (Domain istisna sınıfları) bitişik → metin çakışması olası · `sap_client.py`: D3 yalnız `:2303-2307` (`create_dataelement`); `push_object` `:941-947` bölgesine D3 dokunmadı (önceki çakışma notu düzeltildi) · `foundation-ops.md`, `tool-catalog.md`, `SKILL.md`, `atom.py` birden çok dalda. Merge sonrası: `KilitSirasi` T1–T3 birleşik kodda · D3 L1 mutasyonu tek başına artık yakalanmalı (kilit dalı handle'ı None'a çekiyor) · tam foundation (sahte kök `C:\IX\PROVA\.tmp\devam-2026-09-14\port\e3_sahte_kok`, izole TMP/TEMP/TMPDIR) · kök takım `python tests/run_tests.py` · skill takımları.
4. **Adım 4 kalanları:** D5 fixture'ları · `new_project --no-next-steps` · http `@` yolu · doctor emekli anahtar WARN.
5. **Adım 6 yayın:** `yayin_hazirla` → push onayı (şirket yazılı izni push anında yeniden teyit; tek temiz commit) → GitHub'dan Q4 reinstall → E4 → W21 (yalnız DEV sandbox, E7–E8 sonrası, adım adım onay).

**✅ KARAR (kullanıcı onayı 2026-09-15, "7 madde ok") — tüketici güncelleme mimarisi.** Bu blok aşağıdaki eski "yerel katman" tartışmasının YERİNE geçer; eski metin tarihçe olarak altta.
- Felsefe: kurulumdan sonra kopya tüketicinin. Template başlangıç noktası, sonrasında isteğe bağlı yeni yetenek ve düzeltme.
- Üç komut:
  - (1) tek satır ilk kurulum.
  - (2) `%guncelle`: seçmeli güncelleme. İnce başlatıcı `git show origin/main:GUNCELLE.md` okur; 3-yollu vaka tablosu; önce/sonra test; hükmü script verir; geri dönüş etiketi.
  - (3) `kur.cmd -Sifirla`: yerel = repo. Değişiklik listesi, yazılı onay, `yedek/<tarih>` dalı, `reset --hard` + `clean -fd` (`-x` yok), install + doctor. Projelere dokunmaz. Tek satır komut GitHub'daki `kur.ps1`'yi indirdiği için (`README.md:39`) bozuk yerel `kur.ps1`'den bağımsız.
- Bayraksız `kur.cmd`: temizse çeker, değilse durur ve iki yolu söyler (bugün yalnız "DURDU", `kur.ps1:540`).
- 7 karar:
  1. `CLONE_PROTECTED` kaldırılır; doctor değişen template dosyalarını bilgi olarak listeler.
  2. Seçmeli güncelleme: her şey listelenir + "hepsini al".
  3. Kesin yasak damgası ve SAP kapısı farkı engellenmeden raporlanır.
  4. Sıfırlama yukarıdaki gibi.
  5. Ayrı kullanıcı katmanı (`axet-yerel`) YOK; 2026-09-13 kararı korunur. Aşağıdaki 6 açık soru bununla düşer.
  6. Öneri kanalı (GitHub issue/PR, tek bakımcı) yayından sonra.
  7. Yayından önce: 1, 4, `kur.cmd` mesajı, `GUNCELLE.md` v1 + `%guncelle`, çekirdek §11 dar istisnası, değişiklik listesi biçimi (her değişiklik tek commit + liste kalemi). Yayından sonra: `_lab` ölçümleri (uzaktan prosedürü izleme, kabuk/zaman aşımı, config'in oturum ortasında okunması) + öneri kanalı.
- Asgari güvenceler: §11 istisnası yalnız doğrulanmış klonun kendi uzağından, yalnız bu dosya, yalnız `%guncelle` sırasında. GitHub `main` koruması. Prosedür deny ve yasakları gevşetemez. Ayrışma eşiğinde birleştirme denenmez.
- **Kullanıcı ek şartı (2026-09-15):** güncelleme talimatı repo mimarisinin tamamını kapsamalı: dosyalama, kural, validator, skill, script, ders, config, template, test. Her tür için güncelleme yöntemi ve testi, ajanın anlayacağı ve ATLAYAMAYACAĞI biçimde tarif edilmeli. "Burası çok önemli." → iş maddesi **GUNCELLE-MIMARI** (aşama 1: mimari envanteri + tasarım, 2026-09-15 başladı; araştırma raporu hedefi `C:\IX\PROVA\.tmp\guncelle-mimari\RAPOR.md`).
- **Kullanıcı kararları (2026-09-15, ek):**
  - Kullanıcının sildiği template dosyası güncellemede **GERİ GETİRİLİR** (sorulmaz, raporda bildirilir).
  - Güncellemeden sonra ajan **bütünlük turu** koşar: doctor + genel kontrol araçları + atıf ve kırık link kontrolleri. Sonuca göre düzeltir ve yeniden ölçer.
  - Açık tasarım noktaları:
    - Aynı dosyanın her güncellemede geri gelme döngüsü.
    - Bugün hiçbir aracın yakalamadığı atıf sınıfları. Yeni kontrol çıkarsa gate moratoryumu onayı gerekir.
    - Düzeltme döngüsünün deneme sınırı.
- **Yayın modeli — kullanıcıyla netleşti (2026-09-15):**
  - Yeni kurulum tam `git clone` ile yapılır (`kur.ps1:553`, `--depth` yok). Yeni kuran her zaman en son sürümü ve bütün public geçmişi alır; tabanı kurulduğu andaki HEAD olur.
  - İlk yayın tek commit. Sonraki değişiklikler public geçmişin üstüne eklenir.
  - Public'e force push YOK. Tek istisna sır sızıntısı: geçmiş temizlenir, kullanıcılara `-Sifirla` önerilir.
  - Sığ klon YASAK; test ile sabitlenecek.
- **GUNCELLE-MIMARI — lider varsayılanları (itiraz yoksa böyle; tasarım belgesinde gerekçeli):**
  - Değişiklik listesi `CHANGELOG`: kalem no, tür, neden, dosyalar, test, `gerektirir:` (kalem bağımlılığı script'le zorlanır). Commit trailer `Guncelleme-Kalemi:`. Yayınlar etiketlenir.
  - Test kapsamı: yalnız plandaki kalemlerin eşlendiği takımlar önce ve sonra koşar; tam tur isteğe bağlı. Tam foundation ≈7 dk, kök ≈12 dk ölçüldü.
  - İstemediklerim listesi: silinen template dosyası geri gelir. Kullanıcı kalıcı istemiyorsa yerel bir hariç listesine yazar; ajan o listedekileri geri getirmez ve raporda sayar.
  - `-Sifirla` yedek dalları birikir. doctor 5'ten fazlasını bilgi olarak bildirir, silmez.
  - aXet.code uygulama sürümü: kalem en az sürüm isterse `%guncelle` bildirir. aXet'in kendisini güncellemek kapsam dışı.
  - Platform varsayımı Windows (`kur.ps1`, winget). Script'ler Python ile taşınabilir yazılır, Linux/macOS DOĞRULANMADI.
- **✅ Kullanıcı cevapları (2026-09-15, AskUserQuestion):**
  - (Q1) **Proje açılınca öner.** `%guncelle` yalnız klonu günceller. Proje aXet'te açılınca doctor ya da oturum özeti "proje şablonu eski" der; `%guncelle-proje` aynı 3-yollu yöntemle günceller. Her proje ayrı onaylanır. Ölçülen zemin: `new_project.py:125-132` damgayı yeniliyor.
  - (Q2) **Yayın başı tek commit** (kalem başı commit DEĞİL). Sonuç: public geçmişte seçim birimi yayındır. Yayın içinde kalem seçimi yalnız CHANGELOG'daki kalem→dosya eşlemesiyle, dosya düzeyinde yapılabilir. Aynı dosyaya dokunan kalemler birlikte alınır. Karar 2 ("her şey listelenir + hepsini al") buna uyarlanır.
  - (Q3) **Kritik kalemler seçili gelir.** Kullanıcı çıkarabilir; alınana kadar doctor ve oturum özeti her oturum hatırlatır.
  - (Q4) **Günde bir kontrol.** Oturum özeti ya da doctor günde en fazla bir kez `git fetch` yapar ve "N yeni kalem" der. Ağ yoksa sessiz geçer; hiçbir şeyi otomatik uygulamaz.
- **Aşama 1 BİTTİ (2026-09-15):** rapor `C:\IX\PROVA\.tmp\guncelle-mimari\RAPOR.md`, betik `classify.py`.
  - 412/412 izlenen dosya sınıflandı, eşleşmeyen 0.
  - Yükleme yolları, eş dosyalar ve test haritası dosya:satır kanıtlı.
  - Yayın kopukluğu kodla doğrulandı: `yayin_hazirla.py:110-112,139` her yayında `git init`. Canlı ikinci yayın denenmedi.
  - Proje katmanında taban kaydı YOK (`new_project.py:91-102` yalnız eşitlik kontrolü). Tek istisna `SAP-STAMP-ID` damgası.
  - Testi olmayan sınıflar:
    - skill'ler: `sap-rap`, `sap-cds-ddic`, `sap-dev`, `sap-classic-abap`, `sap-odata-backend`, `sap-intake-triage`
    - belgeler
    - memory
    - `maintenance/*.py`
  - Bütünlük boşlukları (yeni kontrol çıkarsa gate moratoryumu, kullanıcıya TEK TEK sunulacak):
    - B1 MEMORY indeksi ↔ dosya
    - B2 skill atıfları (yalnız sap-code-review için var)
    - B3 diskte olup zincire bağlı olmayan validator
    - B4 genel markdown link kontrolü
    - B5 yetim script
    - B6 denylist canlı ölçümü
  - Günlük kontrolün bağlanma yeri `session_brief.py:32,77-101` (doctor fetch yapmıyor).
- **Aşama 2 taslağı HAZIR (2026-09-15):** `C:\IX\PROVA\.tmp\guncelle-mimari\TASARIM.md` (14 bölüm; lider okudu, K4 motor bağımsızlığı notu eklendi).
  - Ana kararlar:
    - dosya başına taban (`uygulanan.json`)
    - proje tabanı şablon SHA kaydı (behavior-manifest reddedildi: hash'ten içerik çıkmaz)
    - vaka kodları V0-V7 + R/B/VTB, tam tablo
    - vaka ve sınıf kartları
    - `scripts/guncelle.py` plan/durum/`isaretle`/`kapanis` (eksik kalem → çıkış ≠ 0; rapor script'ten)
    - motor `origin/main`'den geçici kopya
    - `yayinlar.json` yapısal değişiklik listesi
    - `session_brief` günlük/kritik satırı
  - İş paketleri P1-P9. Paralel başlangıç P1 ∥ P6. Başlangıç koşulu: adım 4 ✅ merge + K1/D1 merge.
  - **✅ Kullanıcı kararları (2026-09-14, AskUserQuestion — dördü de önerilen):**
    - **K1:** hariç listesi YOK. Geri getirme görünür log satırıyla yapılır ("GERİ GETİRİLDİ: <dosya> — istemiyorsan tekrar sil").
    - **K2:** 2 düzeltme turundan sonra FAIL → DUR + üç seçenek: hepsini geri al (varsayılan) / yalnız sorunlu kalemi geri al / FAIL'i kabul et, raporda kalıcı.
    - **K3:**
      - B1, B2 ve B4 bütünlük turunda WARN ölçümü olarak çalışır, engellemez.
      - B3 mevcut sap-code-review testinin ters yönlü genişletmesi olarak eklenir.
      - Onay kapsamı: bu, gate moratoryumu 5. şartının açık onayıdır. Onay yalnız bu ağırlık için geçerli; BLOCKER'a yükseltme ayrı onay ister.
    - **K4:** motor ve kartlar `origin/main`'den geçici kopyada çalışır.
      - `origin` resmi template adresi değilse DUR.
      - Motor klondaki eski `scripts/*.py` modüllerini import etmez (TASARIM §6 lider notu).
  - Lider varsayılanları (itiraz yoksa): K5 `templates/package` kapsam dışı + bilgi satırı · K6 eşik >3 çakışma bloğu ya da yerel fark >%50.
- **Yayın modeli bulgusu (lider, 2026-09-15):** `maintenance/yayin_hazirla.py:2,142` her yayında tek commit'lik YENİ geçmiş kuruyor. İkinci yayında tüketici klonuyla ortak taban kalmaz, 3-yollu güncelleme ve düz pull bozulur. Öneri: ilk yayın tek commit, sonrakiler public geçmişin üstüne kalem başı commit. Araştırma ajanı doğruluyor.

**ESKİ — tüketici değişiklikleri ve yerel katman (tarihçe; yerine yukarıdaki KARAR geçti):**
- Kullanıcı kararları:
  - Tek bakımcı kullanıcının kendisi.
  - Öneri gönderen tüketicilerde GitHub hesabı zorunlu (OK).
  - Konu ikiye ayrılır:
    - (1) Tüketici **yerelde** yeni dosya ekler: ders, bilinen hata, script, skill. Ajan buna teşvik edilir ve yönlendirilir. Dosyalar core'u bozmaz, güncellemede ezilmez, template standardında yazılır.
    - (2) Ekip geneline yayılma: öneri → bakımcı.
- Ölçülen zemin:
  - Proje `.axet-code/` katmanı zaten var ve güncellemeden etkilenmiyor: `templates/project/.axet-code.json:3`, `recall.py:112-114`.
  - **`%remember` bugün ekip dersini klondaki `memory/`'ye yazıyor** (`skills/remember/SKILL.md` adım 1). Takipli `MEMORY.md` değiştiği için klon kirleniyor ve `kur.ps1:513-516` güncellemeyi durduruyor.
  - `kur.ps1` yalnız `pull --ff-only` + install + doctor yapıyor. Yerel katman denetimi, test ve geri dönüş YOK (`kur.ps1:8-13`).
- Lider önerisi (sohbette sunuldu):
  - Klon dışında kullanıcı-geneli katman `%USERPROFILE%\axet-yerel\` (memory/skills/scripts). install bunu context_paths ve skills_paths'e kaydeder, recall de kapsar.
  - Standart iskelet `templates/yerel/`. doctor kontrolleri yerel katmanda da koşar.
  - Çekirdek §9'a tetikler eklenir; `%gun-sonu` sorusu.
  - Kayıtlarda `oneri:` alanı ve `%template-oneri`.
  - Güncelleme akışı: geri dönüş noktası → pull → yerel uyumluluk denetimi + yerel testler → uyumsuzlukta karantina + rapor, `-GeriDon`, uyarlama skill'i.
  - Klondaki core dosyası değişikliklerini 3-yollu birleştirme ÖNERİLMEDİ.
- ❓ Açık sorular:
  1. Kullanıcı-geneli yerel katman açılsın mı? Bu, 2026-09-13'teki "ayrı kişisel katman yok" kararını değiştirir; müşteriye özel olan projede kalır.
  2. Onay ayrımı: ders → yaz + bildir; script/skill → öner + onay.
  3. Yerel script SAP'ye yazamaz (yazma yalnız `sap_adt_cli` kapısından).
  4. Zamanlama: öneri, yayından önce `%remember` yönlendirmesi + yerel katman + iskelet + doctor kapsamı.
  5. Güncellemede uyumsuzluk varsayılanı: öneri karantina + rapor.
  6. Yerel script'e test zorunlu mu: öneri evet, testsiz → DOĞRULANAMADI.
- **Güncelleme felsefesi — kullanıcı yönü (2026-09-15, sohbet):**
  - Kurulumdan sonra sorumluluk tüketicide: tüketici dosya ekler, siler, değiştirir. Template bir başlangıç noktası; sonrasında yeni yetenek ve bug düzeltmesi sunar. "Tek repo" katılığı yok.
  - **İki ayrı güncelleme modu:**
    - (A) **Seçmeli güncelleme:** ajan repodaki `GUNCELLE.md`'yi okur. Tüketicide olmayan ya da yanlış çalışan template dosyalarını yalnız bizim repoya göre günceller. Mekanizma: 3-yollu (taban/yerel/yeni) vaka tablosu, test ölçümü önce/sonra, geri dönüş etiketi.
    - (B) **Sıfırlama:** yerel = repo. Kullanıcı yerel kurguyu tamamen atmak isteyebilir. Mevcut `kur.ps1` güncelleme komutu bu amaçla KALIR.
  - Ölçülen gerçek (`kur.ps1:513-516`): bugün `pull --ff-only` yapıyor. Yerel değişiklikte DURUYOR; sıfırlamıyor, saklamıyor. (B) için açık bayrak ve yedek gerekecek (yerel değişiklikler ve kullanıcı dosyaları bir yere alınmalı, sonra reset). Tasarım kararı açık.
  - Lider cevabındaki 4 karar sorusu cevap bekliyor:
    - (1) `CLONE_PROTECTED` kaldırılsın mı
    - (2) varsayılan seçmeli mi
    - (3) yasak damgası ve SAP kapısı farkı raporlansın mı
    - (4) zamanlama

**Bekleyen kullanıcı kararları:**
- Önceden var olan "30 sn sarmalayıcı zaman aşımı → WARNING → yazma" sınıfının genel düzeltmesi (tüm canlı BLOCKER validator'lar): sıkılaştırır, yavaş sistemde yanlış BLOCKER üretebilir.
- Ek deny desenleri.
- doctor: override-by-length kontrolü.
- K3: search truncated davranışı.

**Diğer bilgisayar (orijinal DEV_CORE):**
- Ajan bekçisi (adım 5): paket `C:\IX\bekci-tasima-2026-09-14\` (`OKU-BENI.txt` + TaskStop sahipsiz süreç bulgusu). Çekildikten sonra bu makinedeki `C:\IX\.wt\DEV_CORE\2026-09-14-ajan-bekcisi` worktree'si kapatılır (`--wt-denetim` o zamana kadar işaretler, beklenen).
- Kilit kalemleri: DEV_CORE `sap_client.py:826` · `sap_adt_lib.py:4311`, `:3085`, `:3124-3138` · `populate_message_class.py:307` aynı otomatik temizleme; `lock_manager` / `write_workflow` ölü kod (ayrıntı D11 satırı; rapor `C:\IX\PROVA\.tmp\devam-2026-09-14\kilit-arastirma\RAPOR.md`).
- PROVA hook yanlış pozitifleri (PostToolUse "SAP işlemi BAŞARISIZ" kod metni gösteriminde).

**Kalıcı kopyalar:** `C:\IX\PROVA\.tmp\devam-2026-09-14\` (gate-k1d1, kilit, kilit-arastirma, commit mesajları, sahte kök, doğrulama çıktıları, d3). `%LOCALAPPDATA%\axet-code\projects.json` 9 scratch kaydı silindi (yedek `projects.json.bak-2026-09-14`, kalan 7).

