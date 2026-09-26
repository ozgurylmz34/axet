# IX → aXet Güncelleme Prosedürü

> Bu klasör template bakımcıları içindir. aXet oturumları `maintenance/`'ı yüklemez, `install.py` dokunmaz.
> Amaç: IX tarafı (DEV_CORE metodoloji çekirdeği + örnek proje) geliştikçe aXet template'ini **tüm araştırmayı
> tekrarlamadan**, yalnız değişen kısımları işleyerek güncel tutmak.

## Dosyalar
| Dosya | Ne işe yarar | Kim yazar |
|---|---|---|
| `sync-rules.json` | Kaynak dosya/desen → karar, hedef aXet dosyaları, parti, durum, gerekçe. Ayrıca dosya olmayan Claude/aXet yetenekleri. | Bakımcı (elle) |
| `sync-lock.json` | Son aktarımda her kaynak dosyanın hash'i ve kaynak commit'i. | `sync_check.py --update-lock` |
| `sync_check.py` | Güncel kaynağı kilitle karşılaştırır: KURALSIZ · YENİ · DEĞİŞEN · SİLİNEN. | — |

Karar sözlüğü: `al` (kopya/az uyarlama) · `uyarla` (içerik dönüştürülerek) · `telafi` (aXet'te mekanizma yok,
başka yolla) · `alinmaz` (gerekçe zorunlu) · `bekliyor` (henüz karar yok).
Durum: `tamam` · `kismi` · `yapiliyor` · `planli` · `bekliyor` · `-`.

## Ne zaman
- IX tarafında anlamlı değişiklik birikince (öneri: ayda bir ya da büyük bir IX PR'ından sonra).
- aXet.code yeni sürüme geçince (ayrıca: §5).
- Yeni bir parti aktarımı bitince (kilidi güncellemek için).

## 1. Hazırlık
1. DEV_CORE ve örnek projenin güncel klonunu çek (`git pull`); çalışma ağacı temiz olsun.
2. Template reposunda yeni dal aç: `git fetch origin` + `git switch -c sync/<tarih> origin/main`.

## 2. Farkı çıkar
```powershell
python maintenance\sync_check.py --source DEV_CORE=<DEV_CORE klonu> --source PROVA=<örnek proje klonu>
```
Çıktının sonundaki **KAPSAM** satırını oku: araç içerik doğruluğuna bakmaz, yalnız neyin değiştiğini söyler.

## 3. Farkları sırayla işle
1. **KURALSIZ** — hiçbir kurala düşmeyen dosya. `sync-rules.json`'a özel kural ekle (genel desenden ÖNCE):
   karar + hedef + parti + gerekçe. `alinmaz` ise gerekçe zorunlu.
2. **DEĞİŞEN (AKTARILMIŞTI)** — önce kaynağın farkını oku (çıktı `git diff <kilit>..HEAD -- <dosya>` komutunu
   verir), sonra hedef aXet dosyasına yalnız anlamlı değişikliği uyarla. Kopyala-yapıştır değil: aşağıdaki
   uyarlama kurallarından geçir.
3. **YENİ** — genel bir desene düşmüş yeni dosya. Kararını gözden geçir; genel desen yanlış karar veriyorsa özel
   kural ekle (ör. `scripts/*` → `alinmaz` genel kuralına düşen yeni bir SAP script'i).
4. **SİLİNEN** — kaynaktan kalkan dosya. Hedefte karşılığı hâlâ doğru mu? Kaynakta kaldırılan bir kural/ders
   aXet'te de kaldırılmalı mı?
5. **Hiç dosya eşlemeyen kurallar** — kaynak dosya taşınmış/yeniden adlandırılmış olabilir: deseni düzelt.
6. **DEĞİŞEN (henüz aktarılmamıştı)** — bilgi; o parti aktarılırken güncel hâl kullanılır.
7. **Kural dosyaları** (`CLAUDE.core.md`, `claude/kesin-yasaklar.canonical.md`, proje `CLAUDE.md`, `claude/memory-seed/*`)
   değiştiyse dosya düzeyi yetmez: farkı madde madde oku ve `rule-coverage.md`'deki satırları güncelle (yeni madde →
   yeni satır; aXet karşılığı yoksa durum `eksik` + öneri).

## 4. Uyarlama kuralları (her aktarımda)
- `C:\IX`, junction ya da DEV_CORE'a çalışma zamanı referansı YOK; içerik aXet klasörüne yazılır.
- Claude Code'a özgü mekanizmalar (hook, özel ajan, SendMessage, `paths:`, auto-memory, MCP) aXet'te yok:
  karşılığı `docs/axet-davranis-olcumleri.md`'deki ölçülmüş mekanizmalarla kurulur; ölçülmemiş yetenek iddia edilmez.
- Müşteri/proje/kişi/host izleri nötrleştirilir; şifre ya da token hiçbir koşulda taşınmaz.
- SAP'ye yazan her script tek yazma kapısından (`sapadt/gate.py`) geçer; geçmeyen yazma script'i alınmaz.
- Skill `description` alanı `>` blok biçiminde; çekirdek dosyalar ≤150 satır.
- Metin Türkçe, teknik adlar İngilizce.

## 5. Doğrula
1. Template script/şablon testleri: `python tests\run_tests.py` — 0 failure olmadan merge edilmez.
   **Tam takımları PR CI koşar, yerelde tekrarlanmaz (kullanıcı kararı 2026-09-26, Z149 aşama 1).** `main` ruleset'i
   `CI tamam` işi yeşil olmadan merge'e izin vermez (bypass YOK — Z156, ölçüldü) ⇒ kök · kök-public · foundation ·
   skill takımları ve yayın provası CI'da zorunludur; yerelde tekrarlamak güvence eklemez, yalnız süre yer
   (ölçüldü: kök ~30 dk + prova ~5,5 dk yerel). Yerelde koşulan: değiştirdiğin alanın hedefli `-k` testleri +
   yeni/değişen testin kendisi. CI kırmızıysa kırılan testi yerelde `-k` ile koş. İstisna: CI'ya çıkamayan iş
   (canlı SAP, lab, TUI) yerelde ölçülür. Küme süreleri değişince (yeni ağır test sınıfı) parça dengesi için
   `python tests\run_tests.py --agirlik-yaz` koşulup `tests/parca-agirlik.json` commit'lenir (bayatlaması kapsam
   düşürmez, yalnız dengeyi bozar; kümelerin %80'inden azı ölçülüyse test uyarır).
2. `python scripts\doctor.py` (frontmatter, çekirdek boyutu, damga/kanonik bütünlük, davranış yüzeyi) — 0 FAIL.
3. Değişen skill'in testleri (ör. `python skills-sap\sap-adt-foundation\tests\run_tests.py`, `skills-sap\sap-fs-ts-docs\tests\run_tests.py`).
4. Davranış değiştiyse `_lab`'da ölçüm ve `docs/axet-davranis-olcumleri.md` güncellemesi.
5. Çekirdek içeriği değiştiyse kimlik satırını artır (`CORE-ID` / `SAP-CORE-ID`) ve `doctor.py --live` ile gör.
6. **aXet.code sürümü değiştiyse:** ölçüm tablosundaki davranışları yeniden ölç; farklı çıkan satırı düzelt,
   etkilediği kuralı/script'i güncelle.
7. **Kullanıcı belgeleri turu — HER yayında, sorulmadan, yayın PR'ından önce (kullanıcı kuralı 2026-09-25).**
   Yayın, belgeleri de public'e taşır; kod ya da skill değişip belge eski kalırsa kullanıcı yanlış bilgiyle çalışır.
   - **Kapsam:** kökteki `README.md` · `GUNCELLE.md` · `AGENTS.md` · `docs/*.md` (`yayin_hazirla.DISLANANLAR`
     hariç) · `skills-sap/README.md` · `templates/project/AGENTS.md` · değişen her skill'in `SKILL.md` açıklaması.
   - **Kalem kalem sor:** yayındaki her katalog kalemi kullanıcının gördüğü bir akışı, komutu, sırayı, sayıyı ya da
     sınırı değiştiriyor mu? Değiştiriyorsa ilgili belge bölümünü güncelle; değiştirmiyorsa "belge etkisi yok" de.
   - **Sayılar koddan yeniden ölçülür, elle taşınmaz:** araç sayısı `sap_adt_cli.py --list` → `counts` · çekirdek
     kimlikleri `CORE-ID` / `SAP-CORE-ID` satırları · README sürüm satırını `yayin_hazirla` yazar. Elle yazılan
     sayı bayatlar ve hiçbir test yakalamaz.
   - Değişen belge katalogta bir kaleme beyan edilir (kalemsiz dosya tüketiciye uygulanmaz).
   - Sonucu `IS-LISTESI.md` yayın satırına yaz: "belge turu: değişen <dosyalar> · etkisiz <sayı> kalem".
   *Vaka (v0.5.10):* README'nin bildirim bölümü yeni kapanış akışını anlatmıyordu ve `docs/sap-api-policy.md`
   araç sayısı 2026-09-15'ten beri bayattı (37 → 41). İkisi de testlerden, üç bağımsız incelemeden ve sızıntı
   taramasından geçti; kullanıcı sormasa yayına öyle girecekti. İnceleme brifingi yalnız farkı gösterdiği için
   farkta OLMAYAN belgeyi göremez — bu adım o yüzden ayrıdır.

## 6. Haritayı kapat
1. `sync-rules.json`'da işlenen kuralların `status`/`targets` alanlarını güncelle (aktarılan → `tamam`).
2. Kilidi güncelle (yalnız KURALSIZ = 0 iken çalışır):
   ```powershell
   python maintenance\sync_check.py --source DEV_CORE=<...> --source PROVA=<...> --update-lock
   ```
3. Senkron notu **yayın kataloğuna** gider: aktarılan içerik sıradaki yayının `guncelle/yayinlar.json` kalemlerine
   (her dosya en az bir kalemde; `neden` kullanıcının diliyle, gerekiyorsa "install.py tekrar çalıştırılmalı").
   Kaynak repo adı ve commit YAZILMAZ (katalog public yayına girer); kaynak konumu yalnız `sync-lock.json`'da durur.
   README "Değişiklik notu" yeni kayıt almaz — `CHANGELOG.md` katalogdan üretilir.
4. Aktarım, `sync-rules.json` ve `sync-lock.json` **aynı commit/PR'da** gider; ayrı giderse harita içerikten kopar.

## 7. Araç radarı (elle, ~3 haftada bir)
IX'teki otomatik radar (hook + paralel araştırma) aXet'te yok. Yerine: şirket marketplace'inde (`skill_search`) ve
bilinen SAP/AI araç kataloglarında yeni skill/araç ara → aday varsa kurmadan önce `%skill-audit` → karar
(al / uyarla / alma) `sync-rules.json` `capabilities` bölümüne. Tarih ve sonucu bu satıra yaz: `son-radar: <YYYY-AA-GG> <sonuç>`.
Otomatik kurulum yok.

## 8. Template repo işletimi (sürüm, geri dönüş, onarım)
- **Yazma disiplini:** template reposuna doğrudan `main` commit'i yok; dal + PR (barındırma/CI kararı verilene kadar
  en az yerel pre-commit + `doctor.py` 0 FAIL + değişen skill testleri). Kişi/müşteri/host izi taşıyan içerik girmez (§4).
- **Bilinen-iyi sürüm etiketi:** her doğrulanmış kapanışta `stable` etiketi ilerletilir (remote varsa yalnız bakımcı:
  `git tag -f stable` → `git push -f origin stable`; etiket koruması barındırma tarafında açılır).
- **Geri dönüş:** template bir oturumu bozuyorsa kullanıcı merkezi klonu bilinen-iyiye çeker: `git -C <klon> fetch --tags`
  → `git -C <klon> checkout stable`. Tüm projeler aynı klonu okuduğu için hepsi birlikte döner; onarımdan sonra
  `git -C <klon> switch main`. Global config yolları değişmediği sürece `install.py` tekrar gerekmez.
- **Güncelleme tek yerden iner:** `git -C <klon> pull`; projelerde template kopyası yoktur. `session_brief.py` açılışta
  "template origin'in gerisinde" uyarısını saatte bir kontrolle verir → önce klonu güncelle, sonra işe devam.
- **Kurulum onarımı:** `python scripts/install.py [--sap]` idempotenttir (eksik olanı tamamlar, değişiklik yoksa
  "değişiklik yok") · `python scripts/doctor.py [--live]` kurulum + proje sağlığı · proje tarafında damga yenileme
  `new_project.py --sap` (mevcut projede damgayı yeniler).
- **Yeni içerik nereye:** projeye özel değer/istisna → proje (`AGENTS.md`, `sap-project.json`, paket `.rules.md`,
  `.axet-code/memory/`); her projeye genellenebilen yöntem/ders → template (skill/çekirdek/`memory/`, PR ile, nötr adlarla).
  Emin değilsen önce proje tarafına yaz, genellenince template'e taşı.
- **Müşteri/kurum ad listesi (yayın sızıntı taraması, 2026-09-25):** bu depo da public olduğu için müşteri ve kurum
  adları `yayin_hazirla.py`'de yazılı DEĞİLDİR (adı yakalayan desen adın kendisini yayınlar). Liste iki kaynaktan okunur,
  ikisi birleşir: ① `maintenance/sizinti-yerel.txt` — `.gitignore`'da, her çalışma ağacında (worktree dahil) elle kurulur;
  satır başına bir regex, büyük/küçük harf duyarsız, `#` yorum ② `AXET_SIZINTI_EK` ortam değişkeni (satır ya da `;`
  ayrımlı; CI gizli değişkeni için). Liste yoksa `--yalniz-tara` bunu KAPSAM satırında "YÜKLENMEDİ … ÖLÇÜLEMEDİ" diye
  söyler, **gerçek yayın başlamaz**. Liste dosyası git'te izleniyorsa ya da bir satır geçersiz regex ise araç durur
  (desenin kendisini basmaz). ⚠ CI'da gizli değişken tanımlı değilse CI taraması müşteri/kurum adlarına bakmaz — bu
  yüzden yerel yayın taraması asıl kapıdır. Geçmiş commit'lerdeki adlar bu değişiklikle silinmez.
- **Geliştirme deposu taraması (Z145, 2026-09-26):** yayın taraması `maintenance/`'ı görmez, ama geliştirme deposu da
  public'tir. PR açmadan / push etmeden önce: `python maintenance/yayin_hazirla.py --depo-tara` — depoyu yerinde tarar
  (izlenen + izlenmeyen, `.gitignore`'lular hariç, `maintenance/` dahil). Çıkış 1 = yerel listeden isabet (ya da liste
  yok: ÖLÇÜLEMEDİ); öbür sızıntı sınıfları yalnız UYARI'dır, "iç repo adı" yalnız sayılır. Geçmiş commit'leri ve commit
  mesajlarını taramaz.

## Parti kapanış kuralı
Bir parti ancak şu üçü sağlanınca "tamam" sayılır: o partinin kurallarında `bekliyor` kalmadı · `sync_check`
KURALSIZ = 0 · o partinin hedeflerinde durumu `tamam` olup diskte olmayan dosya yok.
