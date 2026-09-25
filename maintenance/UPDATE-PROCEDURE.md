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
2. `python scripts\doctor.py` (frontmatter, çekirdek boyutu, damga/kanonik bütünlük, davranış yüzeyi) — 0 FAIL.
3. Değişen skill'in testleri (ör. `python skills-sap\sap-adt-foundation\tests\run_tests.py`, `skills-sap\sap-fs-ts-docs\tests\run_tests.py`).
4. Davranış değiştiyse `_lab`'da ölçüm ve `docs/axet-davranis-olcumleri.md` güncellemesi.
5. Çekirdek içeriği değiştiyse kimlik satırını artır (`CORE-ID` / `SAP-CORE-ID`) ve `doctor.py --live` ile gör.
6. **aXet.code sürümü değiştiyse:** ölçüm tablosundaki davranışları yeniden ölç; farklı çıkan satırı düzelt,
   etkilediği kuralı/script'i güncelle.

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

## Parti kapanış kuralı
Bir parti ancak şu üçü sağlanınca "tamam" sayılır: o partinin kurallarında `bekliyor` kalmadı · `sync_check`
KURALSIZ = 0 · o partinin hedeflerinde durumu `tamam` olup diskte olmayan dosya yok.
