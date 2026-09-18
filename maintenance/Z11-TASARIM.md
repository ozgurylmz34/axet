> # ⚠ SÜRÜM 2 — PRIOR-ART DÜZELTMESİ (2026-09-18, aynı gün)
>
> **Sürüm 1 core'un mevcut mutasyon altyapısını görmeden yazıldı ve bir bölümünü yeniden
> icat ediyordu.** Düzeltme aşağıda; §2 ve §5 buna göre okunmalı.
>
> **Ölçülen prior-art (core):**
> - `core/tests/fixtures/` — **133 fixture'ın 56'sı `--mutasyon` kipli**.
> - `core/tests/run_battery.py` — **paylaşılan batarya koşucusu** (taban + tüm mutasyon
>   kipleri, tek turda). Başlığında **`⛔ Bu bir KAPI DEĞİLDİR`** yazıyor: §10'da
>   "keşfettiğim" gate-değil sözleşmesi **zaten core'un konvansiyonu**.
> - `taban_karari()` / `mutasyon_karari()` — **hüküm fonksiyonları**. §5'te tasarladığım
>   hüküm sözlüğünün muadili core'da **zaten var**.
> - ⭐ **En önemlisi — core gerekçeyi KORPUS ÜZERİNDE ÖLÇMÜŞ:**
>   *"'mutasyon exit!=0 vermeli' naif kuralı canlı korpusta **33 kipin 15'inde SAHTE-FAIL**"*
>   ⇒ §5'in "ikili sözlük sahte güvenin kaynağıdır" iddiası benim çıkarımım değil,
>   **core'un ölçümüdür**. Kanıt bana ait değil; ona ait.
> - Core'un mutasyon **modeli** farklı ve bazı yönlerden daha sağlam: mutasyon bir metin
>   değiştirme değil, **kusurun CANLI olduğu sabit bir SHA'dan** eski sürümü yüklemek ⇒
>   mutasyon **no-op olamaz** (D4'ün yapısal çözümü) ve **yeniden üretilebilir**.
>   Üstelik hareketli ref tuzağı da çözülmüş: *"`--ref`e DAL ADI VERME… korpus ayırt
>   etmiyormuş gibi görünür, **HATA VERMEDEN**"* + bunu yakalayan **taban öz-denetimi (exit 2)**.
>
> **İKİ MODEL RAKİP DEĞİL — FARKLI SORU SORUYOR:**
>
> | | Core'un batarya modeli | Z11'in ihtiyacı |
> |---|---|---|
> | Soru | *"Korpus **tarihsel kusuru** ayırt ediyor mu?"* | *"Test **bu kuralı** koruyor mu?"* |
> | Mutasyon | sabit SHA'dan eski sürüm | çapa ile kural kaldırma |
> | Ön koşul | **kusurun bir kez yaşanmış olması** | yok — hiç bozulmamış kural da ölçülebilir |
> | Dayanıklılık | yüksek (no-op imkânsız) | çapa doğrulaması gerektirir (D4/D5) |
>
> Core'un modeli **hiç bozulmamış bir kuralı ölçemez** (SHA yok). Z11'in modeli o boşluğu
> doldurur. ⇒ Z11 **core'un yerine geçmez, eksiğini tamamlar**.
>
> **SÜRÜM 2'DE DEĞİŞENLER (core'dan devralınanlar — icat değil, uyarlama):**
> 1. **Hüküm sözlüğü core'un ölçümüne dayandırılır** (33/15 sahte-FAIL), benim çıkarımıma değil.
> 2. **Taban öz-denetimi ZORUNLU** — ölçüm referansı kaydıysa `exit 2` ile dur. Core'un
>    `--ref` dersinin aXet karşılığı: kampanyanın taban commit'i beklenenden farklıysa DUR.
> 3. **Bağlam ekonomisi:** ham çıktılar `.tmp/` altına, ekrana **yalnız özet tablo**
>    (core: `OZET_SATIR_BUTCESI = 22`). Sürüm 1'de bu yoktu; rapor şişmesinin çaresi bu.
> 4. **Kip/kampanya keşfi `--help`'e GÜVENMEZ** — kaynaktan türetilir (core'un üç katmanlı
>    keşfi 90 koşuculuk korpusa karşı ölçülmüş: "0 hayalet").
> 5. **Mutasyonun ikinci türü eklenir:** kusurun yaşandığı bir SHA varsa, çapa yerine
>    **SHA-tabanlı mutasyon** tercih edilir (daha dayanıklı). Çapa yalnız SHA yokken.
>
> **AÇIK SORU (kullanıcı/sahip kararı):** `run_battery.py` aXet'e **doğrudan** koşulamaz —
> core'un fixture mimarisine bağlı, aXet'te ise düz `unittest` modülleri var. İki yol:
> ⓐ aXet kendi koşucularına `--mutasyon` kipleri ekleyip core'un konvansiyonuna geçsin
> (büyük, mimari değişiklik) ⓑ Z11 dar kapsamlı kalsın, core'un **hüküm disiplinini**
> devralsın (küçük). **Öneri: ⓑ** — ⓐ ayrı ve büyük bir karardır, bu turda yapılmaz.
>
> ⚠ **ÖLÇÜLMEDİ:** `run_battery.py`'nin aXet'e uyarlanabilirliği fiilen denenmedi; yukarıdaki
> "doğrudan koşulamaz" hükmü **kod okumasına** dayanıyor (fixture düzeni ↔ unittest modülü).


---

# Z11 — `maintenance/mutasyon_kos.py` TASARIMI

> **Bir cümle:** Bir testin *koruduğunu iddia ettiği kuralı gerçekten koruyup
> korumadığı* hakkında **savunulabilir bir hüküm** üreten, elle koşulan teşhis aracı.
>
> ⛔ **GATE DEĞİL** (ADR 0019). CI'ya, pre-commit'e, hook'a **bağlanmaz**.
> Bağlamak ayrı ve bilinçli bir karardır: 5 şart + kullanıcının açık onayı.

---

## 1. Hangi problemi çözüyor — ölçülen gerekçe

2026-09-18 oturumunda **24 ajan 90 ayrı `.py` dosyası** yazdı. `run_tests.py`
çağıran 31 ajanın koşucuları tarandı; **çekirdek herkeste vardı, eksik olanlar
tam da güvenlik korkuluklarıydı**:

| Özellik | Kaç ajanda | Sınıf |
|---|---|---|
| `run_tests.py` alt süreç | 31/31 | çekirdek |
| sha256 doğrulama | 25/31 | güvenlik |
| `(stderr+stdout)` birleşik okuma | **17/31** | **güvenlik** |
| `py_compile` geçerlilik | **8/31** | **güvenlik** |
| desen-bulunamadı koruması | **2/31** | **güvenlik** |

⚠ Tarama sezgiseldir (komut metninde desen arar) ⇒ sayılar **alt sınırdır**.

**Bu bir verimlilik problemi değil, DOĞRULUK problemidir.** Üç kör nokta sınıfı:

1. **Yalnız stdout ayrıştıran 14 ajan** "hangi test kırıldı"yı ölçemedi.
   `unittest.TextTestRunner` FAIL/ERROR özetini **stderr**'e yazar. Ellerinde
   yalnız *"bir şey kırıldı"* vardı — `rc≠0` mutantın öldüğünü **kanıtlamaz**.
2. **`py_compile` koşmayan 23 ajan** çöken mutantı "öldü" saydı. Çöken mutant
   testin kuralı koruduğunu değil, **dosyanın bozulduğunu** gösterir.
3. **Desen-bulunamadı koruması olmayan 29 ajan** en pahalı sınıfa açıktı:
   `metin.replace(eski, yeni)` deseni bulamazsa **sessizce hiçbir şey yapmaz**,
   test doğal olarak yeşil kalır, ajan bunu **"mutant SAĞ KALDI = test kör"**
   diye raporlar. ⇒ **Hiç uygulanmamış bir mutasyon, sahte bir BULGU üretir.**
   Yanlış-negatif değil **yanlış-POZİTİF**.

⚠ Bu üç sınıfın fiilen kaç sahte hükme yol açtığı **ÖLÇÜLMEDİ**. "Olmadı"
demiyoruz, "ölçülmedi" diyoruz — Z11'in ilk işi bunu ölçmektir (§14/A).

**İkincil kazanç (asıl gerekçe değil):** GATE-P4'ün ürettiği 60.704 token'ın
~14.800'ü (%24) sıfırdan yazılan alet koduydu, ~12.400'ü (%20) rapor metni.
Araç ikisini de küçültür — ama **bu tasarımın gerekçesi doğruluktur**; hız yan
üründür ve hız uğruna hiçbir korkuluk feda edilmez.

---

## 2. Prior art — neden hazır araç değil

`mutmut` · `cosmic-ray` · `MutPy` · `mutatest` · `Poodle` incelendi
(karşılaştırmalı literatür). **Z11 bunların rakibi değil, farklı kategoridir.**

| | Hazır araçlar | Z11 |
|---|---|---|
| Mutasyonu kim seçer | araç (sözdizimsel operatör: `+`→`-`, `<`→`<=`) | **inceleyen akıl** (anlamsal: *"bu kuralı tümden kaldır"*) |
| Kaç mutant | yüzlerce, kapsamlı tarama | ~6-20, hedefli |
| Çıktı | mutation **score** (sayı) | **hüküm + kanıt** (savunulabilir metin) |

Kararı belirleyen üç ölçülmüş olgu:

1. **Bu takım yavaş.** Ölçüldü: `-k doctor` **191,6 sn** · `-k yeni_proje`
   **206 sn** · `-k precommit` **96 sn**. Hazır araçların modeli *"her mutant
   için tüm takımı koş"*tur ve paralelleştirilmemiştir ⇒ tek modülde kapsamlı
   tarama **saatler** sürer. Hedefli 16 mutasyon ise ~21 dk (ölçüldü: GATE-P4).
2. **Aradığımız kusur sözdizimsel değil anlamsal.** *"Onay kapısı `isaretle`'nin
   üç kolundan yalnız birinde ölçülüyor"* bir operatör mutasyonu değildir;
   kuralın **ne olduğunu anlamayı** gerektirir.
3. ⭐ **Literatürün kendi tespiti:** *"None of the tools can mark equivalent
   mutants."* — **Geçersiz mutantı işaretleyememek**, bizim en çok ihtiyaç
   duyduğumuz yetenektir (§5). Bu oturumda geçersiz mutantın **dört ayrı biçimi**
   fiilen ölçüldü; hazır bir araç dördünü de "sağ kaldı" diye raporlardı — yani
   **dört sahte bulgu**.

⚠ **ÖLÇÜLMEDİ:** hazır araçlardan birinin *kapsamlı süpürme* için sonradan
benimsenmesi denenmedi. Z11 onu dışlamaz; farklı işi vardır.

---

## 3. Kullanıcı kim — ve bu tasarımı nasıl belirliyor

| Kullanıcı | Özellik | Tasarıma etkisi |
|---|---|---|
| **Alt-ajan** (gate, düzeltici) — baskın kullanıcı | **geçici, durumsuz, auto-memory'yi GÖRMEZ** | ⭐ **Araç kendini öğretmek zorundadır** |
| Lider | doğrulama, yeniden ölçüm | kampanya **yeniden koşulabilir** olmalı |
| CI / insan | — | **YOK. Bağlanmaz.** |

⭐ **Birinci ilke: ARAÇ REDDEDEREK ÖĞRETİR.** Ajan metodolojiyi başka hiçbir
yerden öğrenemez (brifingde yazılmadıysa bilmez). Her korkuluk tetiklendiğinde
**kuralın NEDEN var olduğunu** da yazar — kuru bir hata değil:

    DESEN-BULUNAMADI: M7 capasi 'scripts/doctor.py' icinde 0 kez gecti.
      Mutasyon UYGULANMADI. Bu bir BULGU DEGILDIR.
      NEDEN ONEMLI: capa bulunamazsa replace() sessizce hicbir sey yapmaz,
      test dogal olarak yesil kalir ve bu "mutant sag kaldi = test kor"
      diye raporlanir. Olculen vaka: 31 ajanin 29'unda bu koruma yoktu.
      YAP: capayi dosyanin GUNCEL icerigiyle karsilastir (satir numarasi
      kullanma - paralel duzenlenen dosyada dakikalar icinde bayatlar).

---

## 4. Değişmezler — her biri ölçülmüş bir vakadan doğdu

| # | Değişmez | Doğuran vaka |
|---|---|---|
| **D1** | Geri alma **DAİMA** repo-dışı kopyadan + sha256. `git checkout -- / restore / stash / reset` **YASAK** | Commit'siz lane'de git-tabanlı geri alma **tüm işi siler** |
| **D2** | Mutasyondan **ÖNCE** `yedek_dogrula()`: yedek var mı **ve** diskle aynı mı | Z7: sürücü `replace("/","__")`, kabuk `tr '/' '_'` ⇒ yedek bulunamadı |
| **D3** | `geri_al` **önce kaynağı okur, sonra** hedefe yazar | Z7: hedef `"wb"` ile önce açıldı ⇒ `yeni_proje.py` **0 bayta düştü** |
| **D4** | Çapa **bulunmalı**; 0 eşleşme = `DESEN-BULUNAMADI`, asla "sağ kaldı" | 29/31 ajanda koruma yoktu |
| **D5** | Çapa **BENZERSİZ** olmalı; >1 eşleşme = `ÇAPA-BELİRSİZ`, reddet | `replace(eski, yeni, 1)` **ilk** eşleşmeyi alır ⇒ yanlış yer sessizce mutasyona uğrar |
| **D6** | Mutasyon sonrası `py_compile`; derlenmiyorsa `GEÇERSİZ-MUTANT/çöken` | 23/31 ajanda yoktu |
| **D7** | Kırılan test adları **`(stderr+stdout)` birleşik** havuzdan | `TextTestRunner` özeti stderr'e, `SONUÇ:` stdout'a |
| **D8** | `rc=2` (hiç test eşleşmedi) ve `rc=124` (zaman aşımı) **asla** "geçti" | Çıkış kodu **sinyaldir**, ölçüm değil |
| **D9** | Dar süzgeçle **"öldü" denebilir, "sağ kaldı" DENEMEZ** | Sağ kalma kanıtı ~**20x** pahalı: 8,6 sn dar vs 191,6 sn tam modül |
| **D10** | **Beklenen test** kırılmalı; başka test kırıldıysa ayrı hüküm | `rc≠0` "doğru test kırıldı" demek değildir |
| **D11** | Paylaşılan ürün dosyası mutasyonu **serileştirilir** (kilit) | Z7 yapısal bulgusu — ⚠ etkisi **DOĞRULANMADI** |
| **D12** | **Çökme-güvenli**: niyet önce **günlüğe**; açık günlük varsa açılışta geri al + yüksek sesle bildir | D2/D3'ün dayanıklı hâli: süreç ölürse dosya mutasyonlu kalır |
| **D13** | Taban koşumu **yeşil** değilse kampanya **başlamaz** | Kırmızı tabanda her mutant "ölmüş" görünür |
| **D14** | Satır numarası **tanıtıcı olarak kullanılmaz** (yalnız bilgi) | PATTERN #36: paralel düzenlenen dosyada dakikalar içinde bayatlar |

---

## 5. Hüküm sözlüğü — tasarımın anlamsal çekirdeği

İkili `öldü/sağ kaldı` sözlüğü sahte güvenin **kaynağıdır**. Z11'in sözlüğü:

| Hüküm | Koşul | Bulgu değeri |
|---|---|---|
| **ÖLDÜ** | uygulandı · derlendi · **beklenen** test kırıldı | ✅ test kuralı koruyor |
| **ÖLDÜ-BAŞKA-TEST** | uygulandı · derlendi · kırıldı ama **başka** test | ⚠ **veri, gürültü değil**: kuralın kapsamı sanılandan geniş, ya da bu kural o testin sahibi değil |
| **SAĞ KALDI** | uygulandı · derlendi · **TAM MODÜL** koştu · kırılma yok | ✅ **kural korumasız** |
| **ÖLÇÜLEMEDİ** | dar süzgeç + kırılma yok · `rc=2` · `rc=124` · taban yeşil değil | ⛔ **bulgu DEĞİL** |
| **GEÇERSİZ-MUTANT** | dört alt biçim ↓ | ⛔ **bulgu DEĞİL** |
| **DESEN-BULUNAMADI** | çapa 0 kez geçti | ⛔ **sert hata** |
| **ÇAPA-BELİRSİZ** | çapa >1 kez geçti | ⛔ **sert hata** |

**GEÇERSİZ-MUTANT'ın dört biçimi** (dördü de bu oturumda ölçüldü; hazır
araçların **hiçbiri** bunları işaretleyemiyor):

- `çöken` — derlenmiyor / import'ta patlıyor
- `no-op` — uygulandı ama anlamca aynı
- `eşdeğer` — davranış tasarım gereği aynı *(vaka: `kur.ps1`'de ölü kod sanılan
  şey aslında **etiket-tabanlı ön-süzme** çıktı — iki kollu deneyle ayrıldı;
  "gereksiz diye silinmemeli" diye kaydedildi)*
- `zayıf-maskelenmiş` — ikinci bir guard mutantı maskeliyor *(vaka:
  `test_ayni_paket_ikinci_kez_red` — çapraz-modül kolu yol-çarpışması guard'ı
  tarafından maskeleniyordu; **yalnız iki kollu deneyle** görüldü)*

⭐ **Yalnız ÖLDÜ ve SAĞ KALDI bulgu-değerlidir.** Geri kalan her şey bir **ölçüm
başarısızlığıdır** ve öyle raporlanır. Bu, mevcut hata biçiminin tam tersidir:
bugün ölçüm başarısızlıkları sessizce bulguya dönüşüyor.

---

## 6. Mutasyon nasıl belirtilir

**Tanıtıcı = çapa (kaynak metnin benzersiz bir parçası).** Satır numarası değil
(D14), AST düğümü değil (mutasyonlar anlamsal, operatör değil).

Çok kollu kurallar için **iki kollu deney birinci sınıf vatandaştır** —
maskelenmiş zayıf mutant ancak böyle görülür:

```python
Mutasyon(
    ad="M4",
    aciklama="ayni paket ikinci kez engeli",
    dosya="scripts/new_package.py",
    beklenen_test="test_ayni_paket_ikinci_kez_red",
    kollar=[                      # her kol AYRI AYRI ölçülür + birlikte de
        Kol(capa="<capraz-modul blogu>", yeni=""),
        Kol(capa="<yol-carpismasi blogu>", yeni=""),
    ],
)
```

**Kampanya bir DOSYADIR**, gelip geçici bir betik değil — çünkü Z11'in ilk işi
*geçmiş hükümleri yeniden ölçmek*tir ve bu ancak kampanya saklanırsa mümkün olur.
Biçim: **Python veri modülü veya JSON** (ikisi de stdlib; yeni bağımlılık ve
yazılacak ayrıştırıcı yok).

---

## 7. Maliyet modeli — iki fazlı ölçüm

Ölçülmüş asimetri: **sağ kalmayı kanıtlamak ölmeyi kanıtlamaktan ~20x pahalı.**
Çoğu mutant ölür ⇒ pahalı yol **nadir** olmalı:

```
FAZ 1  dar süzgeç (beklenen testin modülü)
        beklenen test kırıldı        -> OLDU            [bitti, ucuz]
        başka test kırıldı           -> OLDU-BASKA-TEST [bitti, ucuz]
        hiçbir şey kırılmadı         -> FAZ 2'ye yüksel
FAZ 2  TAM MODÜL (yalnız faz 1'de ölmeyenler için)
        hiçbir şey kırılmadı         -> SAG KALDI       [pahalı ama nadir]
```

⛔ **Taban önbelleği YOK** — bilinçli. Kampanya başına 1 taban koşumu, N mutasyon
(tipik N=16) ⇒ kazanç ~%6, buna karşılık önbellek **sessiz bayatlama** sınıfı
açar. *Başarısızlığı sessiz olan bir mekanizmayı küçük bir kazanç için eklemeyiz*
— ADR 0019 moratoryumunun ruhu budur.

Ölçülmüş çekişme katsayısı **1,35x** (paralel lane'lerle). Süreler bu yüzden
**gürültülüdür**: araç süreleri **bilgi** olarak basar, **hükme dayanak yapmaz**.

---

## 8. Eşzamanlılık ve çökme güvenliği

- **Kilit** (D11): `(ağaç, ürün dosyası)` başına. Alınamıyorsa **beklemez**,
  sahibini adıyla söyleyip reddeder — sessiz kuyruk, sessiz bozulmadır.
- **Günlük** (D12): mutasyon niyeti (hedef · yedek yolu · sha256) **önce** günlüğe
  yazılır. Açılışta açık kayıt varsa: yedekten geri al, sha256 doğrula, **yüksek
  sesle** bildir. `yeni_proje.py`'nin 0 bayta düşmesi sınıfının dayanıklı çözümü.
- Her hüküm satırı **hangi ağaçta** ölçüldüğünü taşır — lane karışıklığı çıktıda
  görünür olur.

---

## 9. Çıktı

Araç **kanıt tablosunu kendisi yazar** (`--rapor <dosya.md>`); ajan onu alıntılar,
yeniden yazmaz. Tablo: mutasyon · çapa · hüküm · kırılan testler · beklenen ·
`SONUÇ:` satırı · süre · ağaç · sha256 geri-alma kanıtı.

**KAPSAM BEYANI zorunlu** (core §7) ve **koddan türetilir**, elle yazılmaz:
koşulmayan test modülleri · atlanan mutasyonlar · faz-2'ye yükselmeyenler ·
dokunulmayan dosyalar · platform. Her koşumda basılır — **en kritik an
sıfır-bulgu anıdır.**

---

## 10. Ne DEĞİLDİR

- ⛔ **Gate değil.** ⭐ **Çıkış kodu sözleşmesi: çıkış kodu ARACIN SAĞLIĞINI
  bildirir, bulguyu değil.** `0` = ölçüm tamamlandı (bulgu olsa da) · `≠0` = araç
  ölçemedi. Böylece bir gün yanlışlıkla CI'ya bağlansa bile **bulgu yüzünden akışı
  bloklamaz**. (`vakum_tara.py` aynı sözleşmeyi taşıyor ve bunu koruyan testi var.)
- ⛔ Kapsamlı/otomatik mutant üreteci değil (§2).
- ⛔ `run_tests.py`'nin yerine geçmez — onu **çağırır**, sözleşmesine uyar.
- ⛔ Commit/push **etmez**. Commit lider'in işidir.
- ⛔ SAP/ADT çağırmaz.

---

## 11. Kalibrasyon — araç kendini kanıtlamasın

Proje kuralı: her tarayıcı **bilinen doğru-pozitif + bilinen doğru-negatif** ile
kalibre edilir. `vakum_tara.py` kalibre edilene kadar **iki kez sessizce kördü**.
Z11 `tests/test_mutasyon_kos.py` ile gelir; her hüküm için bir fikstür:

| Fikstür | Beklenen hüküm |
|---|---|
| korunan kural | `ÖLDÜ` |
| gerçekten korumasız kural | `SAĞ KALDI` |
| sözdizimi bozan mutasyon | `GEÇERSİZ-MUTANT/çöken` |
| dosyada olmayan çapa | `DESEN-BULUNAMADI` |
| **iki kez geçen çapa** | `ÇAPA-BELİRSİZ` |
| ikinci guard'ın maskelediği kol | `GEÇERSİZ-MUTANT/zayıf-maskelenmiş` |
| başka testi kıran mutasyon | `ÖLDÜ-BAŞKA-TEST` |
| kırmızı taban | kampanya **başlamaz** (D13) |
| **süreç ortasında öldürülür** | günlükten geri alma · sha256 **eşit** |
| geri alma | kaynak **bayt bayt** aynı |

Son ikisi sıradan test değil; **D12'nin tek gerçek kanıtı** onlardır.

---

## 12. Arayüz taslağı

```
python maintenance/mutasyon_kos.py --kampanya <dosya> [--agac <worktree>]
                                   [--yalniz M3,M7] [--rapor <cikti.md>]
                                   [--faz1-only]
```

```python
kos(suzgec, *, tam_modul=False) -> Kosum(rc, sonuc_satiri, kirilan: list[str])
olc(mutasyon) -> Hukum          # D2→D6→D7→D9→D10 zincirini kendi yürütür
kampanya(dosya) -> Rapor        # taban(D13) + N mutasyon + kapanış yeşili
```

---

## 13. Yerleşim

`maintenance/mutasyon_kos.py` — `vakum_tara.py` ve `yayin_hazirla.py` ile aynı ev.
**Ölçüldü:** `maintenance/` `CLONE_PROTECTED` kümesinde **değil** ve
`install.py`/`new_project.py` ona atıf yapmıyor ⇒ tüketici projelere
**dağıtılmaz**; şablon reposunun kendi bakım alanıdır. Doğru yer.

**`vakum_tara.py` ile ilişki — ayrı kalırlar, boru hattı kurarlar:**
`vakum_tara` **durağan tarayıcıdır** (aday üretir: *"bu test vaadini kanıtlamıyor
olabilir"*), `mutasyon_kos` **dinamik ölçerdir** (adayı hükme çevirir). Z7 fiilen
böyle işledi: 43 aday → 23 ölçüm → 2 gerçek vakum. Birleştirmek ikisini de
bulanıklaştırır.

---

## 14. Kurulum sırası ve ilk iş listesi

**0. Doğrulama (kontrol grubu — araç kendini kanıtlamasın):** kurulduktan sonra
**Z7'nin kampanyası** Z11 ile yeniden koşulur. Z7'nin hükümleri elde mevcut. Araç
ya aynı hükümleri üretir (güven), ya da farklı üretir — o zaman **hangisinin
haklı olduğu ölçülür**. İkisi de değerlidir; sessiz uyum değil.

**A. Geçmiş hükümlerin yeniden ölçümü (yanlış-pozitif avı).** Kapanan lane'lerin
mutasyon tabloları yeniden koşulur. Aranan: desen-bulunamadı yüzünden "sağ kaldı"
sanılmış **sahte bulgu** · çöken mutant yüzünden "öldü" sayılmış **geçersiz hüküm**.

**B. P5-FIX'in kendi kapsam beyanında açık bıraktıkları.**
1. `--karar ertelendi` ve `--karar yerel` kolları **ölçülmedi**: `onay_dogrula`
   orada atlanırsa **durum kaydının onaysız değişmesi** zarar mı?
2. `uygula` ve `kapanis` onay kapıları için **seçici mutasyon koşulmadı**. Ajan
   *"guard'ları argümana dallanmıyor, bu kusur yapısal olarak daha zor"* dedi —
   ama bunu **kod okuyarak çıkardı, ölçmedi.** ⚠ KG-1'in kendisi tam olarak böyle
   bir çıkarımın yanlış çıkmasıydı: `isaretle`'nin guard'ı da tek satırdı ve
   seçici mutasyon altında **3 koldan 2'si korumasız** çıktı.
   *(Kapılar **adıyla** anılır, satır numarasıyla değil — D14.)*
3. Süzgeçsiz tam paket koşumu yapılmadı → merge öncesi sağlık koşumu kapatır.

**C. Kalan 20 Z7 adayı:** `test_guncelle` 10 · `test_doctor` 4 · `test_install` 3 ·
`test_behavior_manifest` 2 · `test_yayin_surumleri` 1.

---

## 15. Riskler ve açık kararlar

| Risk | Karşı önlem |
|---|---|
| Alışkanlıkla fiilî gate'e dönüşür | §10 çıkış kodu sözleşmesi + başlıkta yazılı + testle korunur |
| Aracın kendi körlüğü | §11 kalibrasyon + her koşumda KAPSAM BEYANI |
| Aşırı mühendislik | Önbellek yok · YAML yok · yeni bağımlılık yok · AST yok |
| Kilit kilitlenmesi | Beklemez, reddeder ve sahibini söyler |
| Kampanya dosyası bayatlar | Çapa doğrulaması (D4/D5) bayatlığı **sert hata** yapar — sessiz geçemez |

**AÇIK KARAR (kullanıcıya):** Z11 şablon reposunun bakım aracı olarak mı kalsın,
yoksa tüketici projelerin de kendi testlerini ölçebilmesi için dağıtılan kümeye mi
alınsın? **Şimdilik dağıtılmıyor** (§13) — bilinçli ve geri alınabilir.

**AYRICA (DEV_CORE):** Bu tasarımın 14 değişmezi ve hüküm sözlüğü **aXet'e özel
değil, metodoloji düzeyindedir.** Core'da mutasyon turu metodolojisi ölçüldü:
**yok.** DEV_CORE sahibine ayrı bir bildirim hazırlandı (bu oturumun scratchpad'i,
`z11/DEV_CORE-BILDIRIM.md`) — 6 bulgu, kanıtlarıyla. Taşıma kararı sahibindir.
