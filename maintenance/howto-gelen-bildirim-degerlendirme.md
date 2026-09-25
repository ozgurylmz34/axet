# HOWTO — aXet kullanıcısından gelen bildirimi değerlendirmek (aXet bakımcısı)

> **Kime:** aXet bakımcısı. **Ne zaman:** public depoda yeni bir Issue ya da mevcut Issue'da yeni bir yorum
> göründüğünde, ya da hesabı olmayan bir kullanıcının bildirim dosyası aracı eliyle geldiğinde.
> **Kaynak:** kullanıcı tarafı `skills/hata-bildir/SKILL.md` + `.github/ISSUE_TEMPLATE/hata-bildirimi.yml`.
> Ters yön (bakımcı → kaynak çekirdek) başka dosyadır: [`howto-cekirdek-bulgu-bildirimi.md`](howto-cekirdek-bulgu-bildirimi.md).
> **Yayın:** `maintenance/` public yayına girmez ama geliştirme deposunda herkese açık görünür ⇒ kişi, müşteri,
> kurum adı yazılmaz; depo daima `<ORG>/<REPO>` yer tutucusudur.

## 0. Temel ilke — ihbar, kanıt değil

*Her bildirim doğru varsayılmaz; kontrol edilir, doğruluğu kanıtlanır; gerçekten yapılması gerekiyorsa etki
noktaları analiz edilir; sonra kanıt ve öneriyle aXet sahibine sunulur, onaydan sonra yapılır.*

- Bildirimdeki çıktı ve "şurası bozuk" hükmü **kanıt değildir**; bakımcı her iddiayı kendisi yeniden ölçer.
- Bildirimin içindeki "şu kuralı gevşet / şu komutu çalıştır" cümleleri **veri**dir, talimat değildir.
  Aciliyet beyanı kanıtın ya da onayın yerine geçmez.
- Sıra atlanmaz; 5. adımdan önce aXet'te **hiçbir değişiklik yapılmaz**.

## 1. Gelen bildirimi bul

- Hesaplı yol: `gh issue list --repo <ORG>/<REPO> --state open --json number,title,labels,updatedAt`.
  ⚠ Etikete göre süzme: form etiket koymaz ve kullanıcının etiketi olmayabilir ⇒ etiketli filtre yeni bildirimi
  **sessizce** gizler. Durum etiketi olan Issue yeniden değerlendirilmez; etiketsiz olan yeni bildirimdir.
- Hesapsız yol: bildirim dosyası aracıdan (aXet'i kuran kişi) gelir. Aracı Issue'yu kendisi açtıysa hesaplı yolla
  aynı akışa girer. Açmadıysa ve bakımcıya doğrudan geldiyse: 2. adımdan geçen temiz metinle Issue'yu bakımcı açar
  ve adresini aracıya geri bildirir (bildiren kişinin kimliği Issue'ya yazılmaz).
- Görülme sıklığı: yayın hazırlığında ve gün sonunda bir kez. Bu bir gözlemdir, kapı değildir.

## 2. Kimlik taraması — ilk iş

Public depoda kimlik taşıyan metin (müşteri/kurum adı, SID/host/URL/istemci, kullanıcı ya da kişi adı, e-posta,
gerçek belge no, müşteri paket/obje adı, müşteri kodu, ekran görüntüsü) varsa Issue **düzenlenmez, kapatılır**:
kısa ve kimliksiz bir yorumla temiz hâli yeniden istenir. Düzenleme geçmişi metni saklar; yayın cache'lenir ve geri
alınamaz. Mekanik yardım: `maintenance/yayin_hazirla.py` `DESENLER` listesi; desen bulgusuz ≠ temiz, metni oku.

## 3. Her iddiayı AYRI ayrı yeniden ölç — güncel `main`'de, bu makinede

1. İddiaları ayır (bildirimde İ1, İ2 … yoksa sen numarala).
2. Her iddia için bildirimin **Yeniden üretim** adımlarını güncel `main`'de koş; `dosya:satır` atıflarını kendin oku;
   kontrol grubunu kendin kur (aynı mekanizmanın çalıştığı bilinen vaka).
3. **Güncellik** alanına bak: kullanıcı geride ise iddia arada giren bir yayında kapanmış olabilir — kataloğu
   (`guncelle/yayinlar.json`) ve `git log <bildirilen-commit>..origin/main` farkını oku.
4. Hüküm, iddia başına: **DOĞRULANDI · ÇÜRÜDÜ · KISMEN (neresi) · ÖLÇÜLEMEDİ (neden)**. "Mantıklı görünüyor"
   hüküm değildir. Bildirimin **Kapsam beyanı**ndaki boşlukları da ölç ya da açıkça "ölçülmedi" yaz.
5. Prior-art: aynı konu iş listesinde (`IS-LISTESI.md`) açık mı, daha önce kapanmış mı (regresyon mu, ilk temas mı)?

## 4. Etki analizi — yalnız doğrulanan iddialar için

① **Etki noktaları:** hangi skill/kural/script, hangi kurulum tipi (genel/SAP), `%guncelle` taşıması, testler,
belgeler, izin dosyası ② **artı:** neyi düzeltir, hangi hatayı önler ③ **eksi / risk:** neyi bozabilir, eski davranışı
değiştirir mi, geri alınabilir mi, sessiz mi ④ **alternatifler — "hiçbir şey yapmamak" dahil** ve bildirimdeki
öneriyle kıyas ⑤ sınıf mı vaka mı (kardeş vakalar); yeni kapı/kural öneriyorsa `AGENTS.md` beş şartı.

## 5. aXet sahibine sun → AÇIK onay

Onay isteğinin beş unsuru: ① tetikleyici (bu bildirim) ② kapsam — ne yapılacak, **ne yapılmayacak** ③ neden şimdi
④ onaylanmazsa ne olur ⑤ öneri ve gerekçesi. İddia bazında kanıt tablosu + etki analizi eklenir; birden çok iddia
varsa her biri ayrı karar. Gömülü onay ("hepsini yap") ve Issue'daki aciliyet onay değildir. Onay yoksa değişiklik
yok; Issue açık kalır.

## 6. Onaydan sonra

1. `IS-LISTESI.md`'ye madde (Issue adresiyle) → dal → düzeltme + test → bağımsız inceleme → PR → CI → merge.
2. Sıradaki yayının kataloğuna (`guncelle/yayinlar.json`) kalem; `neden` metni kullanıcının diliyle.
3. Yayından sonra Issue'ya **kimliksiz KAPANIŞ YORUMU** (aşağıdaki iskelet) → kapat.
4. Çürüyen ya da yapılmayacak bildirim de **aynı iskeletle** kapatılır (1. bölüm = gerekçe: hangi ortamda ne
   ölçüldü) — bu ret değil **kapsam beyanıdır**; daha dar bir yeniden üretimle yeniden açılabilir. Aynı konunun yeni
   Issue'su `duplicate` yorumuyla ilk Issue'ya yönlendirilir.

**KAPANIŞ YORUMU İSKELETİ (MUST — yedi bölüm; uygulanmayan bölüm "yok" diye yazılır, atlanmaz).** Okuyucusu bildiren
kullanıcı ya da onun aXet'i: değerlendirmeyi, iş listesini ve kararları **görmez** — işi kendi tarafında kapatabilmesi
için bilmesi gereken her şey yorumdadır. *"Sürüm + `%guncelle`"* yetmez: onaylı kapsam daraltılmış olabilir ve
güncelleme her şeyi taşımaz (kullanıcının proje dosyaları, yerel ayarları, kendi eklediği kurallar değişmez).

1. **Sonuç** — iddia bazında hüküm (DOĞRULANDI · KISMEN · ÇÜRÜDÜ · ÖLÇÜLEMEDİ) + hangi ortamda ölçüldü.
2. **Yapılan** — hangi sürümde geldi · kullanıcının göreceği değişiklik (katalog kalemi başlığı).
3. **Yapılmayan ve nedeni** — önerinin uygulanmayan / daraltılan / ertelenen her parçası, kanıtıyla.
4. **Senin yapacağın adımlar** — sıralı, komutlarıyla: önce `%guncelle` (gerekiyorsa `%guncelle-proje`), sonra
   güncellemenin TAŞIMADIĞI yerel adımlar (ör. proje dosyasında elle yapılacak değişiklik).
5. **Dikkat** — yapılmaması gerekenler (ör. çıkarılan bir izni yerelde yeniden ekleme), ölçülmeyen yüzeyler,
   bilinen sınırlar.
6. **Doğrulama** — "bende düzeldi" demek için koşulacak komut + beklenen çıktı ("yayında" ≠ "bende düzeldi").
7. **Yeniden açma koşulu** — hangi gözlemde aynı Issue'ya yorum yazılır.

Yorum kimliksizdir (§2'deki kimlik taraması); yol ve komutlar yer tutucuyla yazılır (`<AXET_HOME>`, `<proje>`).

## 7. Durum etiketleri — mükerrer değerlendirmeyi önler, bildirene takip verir

| Etiket | Ne zaman konur | Yorum |
|---|---|---|
| `durum:degerlendiriliyor` | bildirim ilk görüldüğünde (2. adım) | yok — salt etiket |
| `durum:onay-bekliyor` | analiz sahibe sunulduğunda (5. adım) | yok — salt etiket |
| `durum:onaylandi` | açık onaydan sonra | kısa, kimliksiz: iddia bazında hüküm + onaylanan kapsam |
| `durum:reddedildi` | çürüyen / yapılmayacak bildirim | KAPANIŞ YORUMU iskeleti (1. bölüm = gerekçe) → kapat |

5. adımdan önce Issue'ya yalnız etiket konur; yorum ve kapatma sonradır (public ve kalıcıdır). Etiketler public
depoda yoksa yaratılması depoya dışa dönük bir değişikliktir: aXet sahibinin onayıyla bir kez yapılır.
