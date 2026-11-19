# İzlenebilirlik, numaralandırma, değişiklik ve veri kaybı kontrolü

## 1. Numara, dosya adı, durum
```
No    : <TİP>-<MODÜL>-<SIRA>          FS-SD-001 ↔ TS-SD-001 ↔ KD-SD-001 = aynı geliştirme
Dosya : <TİP>-<MODÜL>-<SIRA>_<Ad>_v<Sürüm>.md   (PDF/HTML aynı gövde adıyla)
        FS-SD-001_Siparis_Onay_Ekrani_v1.0.md · TS-SD-001_<ANA_OBJE>_v1.0.md · KD-SD-001_Siparis_Kullanici_Kilavuzu_v1.0.md
F1    : DOCU-<MODÜL>-<SIRA>_<Uygulama>_GUI_Yardim.md   (yalnız klasik GUI KD'sinde)
Yer   : <source_root>/<MODÜL>/<PAKET>/docs/     (kaynak/dönüşüm belgeleri ref_docs/ altında; canlı teslimat değil)
```
- İlk `_` öncesi doküman kimliğidir; üretici (Mermaid PNG ön eki) buna dayanır. Aynı klasörde iki doküman aynı kimliği taşımaz.
- **Durum akışı:** `Taslak → İncelemede → Revize Gerekli → Onaylandı → Arşivlendi` (Revize Gerekli → İncelemede döngüsü).
- **Modül kodları:** SD · MM · FI · CO · PP · PM · QM · HR · WM/EWM · PS · BC (temel/modüller arası).
- **Teslim biçimi (varsayılan; proje başka karar verebilir):** FS ve TS için `.md` + `.pdf`. HTML yalnız PDF'e giden yolda
  **ara üründür**, sürüm kontrolüne alınmaz ve ayrıca güncellenmez; FS/TS için "HTML bayat" diye bulgu yazılmaz. KD için
  `.md` + `.pdf` + `.html`, çünkü KD'nin HTML'i uygulama içi yardım kopyası olarak kullanılır (`kd-authoring.md` §8).
  Gerekçe: kimsenin okumadığı üçüncü bir biçimi senkron tutmak her doküman turuna maliyet ekler.

## 2. İzlenebilirlik matrisi (TS'te zorunlu)
| FS gereksinim | FS açıklaması | TS bölümü | TS obje/metot | Test |
|---|---|---|---|---|
| FR-001 | <kısa> | §5.3 | `<SINIF>=>METOT` | UT-001, IT-001 |

- FS'teki **her** FR/KR bir satırdır; boş hücre = eksik TS (İlke 3).
- Kabul kriteri → test bağlantısı ters yönde de kontrol edilir: her test bir kabul kriterine, her kabul kriteri bir teste (DOC-CR-01 ④).
- Matris kaynağa bağlıdır: "N gereksinim karşılandı" yerine "FS §4.1'deki tüm FR'ler" yazılır (DOC-CR-02).
- KD tarafında: FS'teki her kullanıcıya görünen işlev (ekran, buton, mesaj) KD'de bir bölüme karşılık gelir.

## 2-B. Kaynak paketi ve kaynak → belge iz tablosu (FS ikili bir istek belgesinden yazılıyorsa)
Kullanıcının isteği `.docx`/`.xlsx` olarak geldiyse oturumun **ilk** işi kaynak paketidir; intake, FS yazımı ve
inceleyici aynı paketi okur. Kaynak metni model yeniden yazmaz, özetini kaynağın yerine koymaz.
```
python <TEMPLATE>/skills-sap/sap-fs-ts-docs/scripts/kaynak_paketi.py cikar <istek.docx|.xlsx>
      → <proje>/.axet-code/tmp/<ad>-<özet8>/  INDEX.md · metin.md · media/ · gomulu/ · paket.json   (git dışı)
python <TEMPLATE>/skills-sap/sap-fs-ts-docs/scripts/kaynak_paketi.py iz <paket> \
      --tablo <source_root>/<MODÜL>/<PAKET>/ref_docs/iz-<belge no>.md --belge <FS.md>
```
- **Paket:** `metin.md` kaynağın **çıkarım kapsamındaki** metnidir, sırası korunur; her başlık, paragraf ve metinli
  tablo satırı bir **kaynak maddesi** `KM-nnnn`. Metin kutusunun paragraf ve tabloları bulunduğu paragrafın satırına,
  iç içe tablo hücre metnine düzleşir; denklem metni satır içinde `⟦denklem⟧` işaretiyle durur. SmartArt (`D01`) ve
  grafik (`G01`; başlık, seri, kategori ve değer metni) kendi KM satırındadır; xlsx'te çizimdeki metin kutuları
  (`K01`) de. Her görsel `KG-nn`, her gömülü nesne `KN-nn` (OLE paket nesnesinin asıl dosyası — ör. danışmanın HTML
  ekran prototipi —, OLE içindeki Excel/Word, altChunk; tanınmayan ya da bozuk nesne ham kopyalanır ve INDEX'te
  "TANINMADI" yazar). `INDEX.md` kaynağın ayrı kodla yapılan sayımını (madde, başlık, tablo, satır, karakter, denklem,
  SmartArt, grafik, metin kutusu, nesne metni karakteri, görsel, gömülü nesne; xlsx'te karakter yalnız metin
  hücrelerinden) diskteki paketle karşılaştırır: **DOĞRULAMA FAIL olan paket kullanılmaz.** Çıkış `2` = okunamadı ya
  da boyut sınırı (zip üyesi 100 MiB, açılmış toplam 512 MiB) aşıldı; çıkış `3` = biçim desteklenmiyor (`.pdf`,
  `.doc`, `.xls`): kullanıcıdan `.docx`/`.xlsx` hâlini iste; olmuyorsa kaynak izi "ÖLÇÜLEMEDİ" kalır, metni elle yazıp
  paket gibi sunma.
- **Kapsam dışı (INDEX'te yazar):** üst/altbilgi, dipnot, yorum, izlenen değişiklikte silinen metin, Word'ün otomatik
  numaraları, gömülü dosyanın ve görselin içindeki metin, metin taşımayan çizim öğeleri, xlsx'te sayı/tarih hücresinin
  biçimli gösterimi (satırda durur, karakter sayımına girmez) ve nesnenin hangi hücrede durduğu. Gömülü HTML prototip
  tarayıcıda açılır; ekranı `capture_kd_screens.js` `file://` adresinden çeker.
- **İz tablosu** git'te izlenen yerde durur: kaynak paketinin yanında değil, FS'in SAP paket klasöründe
  `ref_docs/iz-<belge no>.md` (kaynak ve dönüşüm belgelerinin yeri; FS gövdesine girmez — İlke 2b). Ölçüldü: proje
  şablonunun `.gitignore`'larıyla `git check-ignore` bu yolu izler, `.axet-code/tmp/**`'yu yok sayar. Kaynak paketi
  git dışıdır; aynı kaynaktan
  `cikar` aynı kimliklerle yeniden üretir. Bu yüzden tablonun ilk satırı kaynağı adlandırır:
  `Kaynak: <dosya adı> · sha256 <ilk 16 hane>` (`iz` çıktısının `kaynak:` satırından kopyalanır). Her kaynak maddesi
  bir satırda; aralık yazılabilir (`KM-0004..KM-0009`):

| Kaynak | Belge kimliği | Not |
|---|---|---|
| KM-0001..KM-0006 | BİLGİ | kapak, doküman kontrolü |
| KM-0007 | FR-001, KR-002 | |
| KM-0021 | TC-01 | kaynaktaki test satırı 1 |
| KM-0022 | TC-02 | (belge kimliği aralıkla yazılmaz; her biri ayrı) |
| KM-0042 | KAPSAM-DIŞI | standart nesne değişikliği — kesin yasak A, kullanıcıya soruldu (S-03) |
| KN-01 | SCR-001, SCR-002 | HTML prototip |

  `BİLGİ` = gereksinim taşımayan madde · `KAPSAM-DIŞI` = bilerek alınmayan madde, gerekçe zorunlu. Geri kalan her
  satır belgede gerçekten geçen kimlik(ler)e bağlanır. `iz` denetimi: tabloda olmayan madde · pakette olmayan madde ·
  boş eşleme · belgede olmayan kimlik · gerekçesiz KAPSAM-DIŞI · tablodaki sha256'nın paketin kaynağıyla uyuşmaması =
  **FAIL**; aynı madde iki satırda, belgede olup tabloda anılmayan FR/KR, boş paket (0 madde) ve sha256'sız tablo =
  UYARI. **Ölçmedikleri:** eşlemenin anlamca doğruluğu ve BİLGİ/KAPSAM-DIŞI işaretinin haklılığı — inceleyici bunları
  okur (`doc-checklist.md` §E "İZ TABLOSUNA DAYALI İNCELEME", AX-DOC-CR-06).
- TS için kaynak FS'in kendisidir: §2 matrisi FS'in her FR/KR'sini satır olarak taşır, iz tablosu yerine geçer.

## 3. Değişiklik kuralları
- FS değişirse → TS güncellenir → versiyon artar → yeniden onay.
- TS değişirse → FS değişikliği gerekmeyebilir → teknik lider onayı yeter; FS'i etkiliyorsa FS §11-A/§11-B'ye döner.
- Arayüz değişirse → KD aynı revizyonda güncellenir; klasik GUI'de F1 yardımı da.
- Build sırasında yeni mesaj ya da alan doğarsa TS **önce** revize edilir, sonra kodlanır.
- Belgeler proje kapanışına kadar güncel tutulur.
- **Doküman turu donmuş kod ister.** TS/KD, ekran görüntüleri ve PDF kodun o anki hâline bağlıdır: satır referansları,
  mesaj metinleri, görüntüler. Kod düzeltme turu sürerken doküman turu **başlatılmaz**; sıra seridir: kod donar (dosya
  özeti/commit kaydedilir) → doküman turu. Paralel koşturmak zaman kazandırmaz: referanslar kayar, görüntüler yeniden
  çekilir ve kusur **sessizdir** (doküman derlenir, inceleme geçer, yanlışlık ancak satır açılınca görülür). Tur yine de
  çakışmak zorundaysa doküman yazarına sabit bir dosya özeti verilmez; yazar başlarken kendisi ölçer, tutmuyorsa durur
  ve sorar. Aynı turda dosya sahipliği açıkça bölünür (bir dokümana tek yazar).
- **Koda çapa ad ile atılır, satır numarasıyla değil.** Doküman değişebilecek koda metot/FORM/dal adıyla bağlanır (ad
  da yazılmadan önce kaynakta doğrulanır); satır numarası ilk düzeltmede kayar (AX-DOC-CR-03).
- **Dışarı gönderilen paket ayrıca ölçülür.** Zip, e-posta eki ya da teslim klasörü çalışma dosyasının bir kopyasıdır ve
  hiçbir inceleme onu görmez: kaynak dosya düzeltilince paket sessizce bayatlar. Paket **teslim anında** güncel dosyalardan
  yeniden kurulur ("zaten kurmuştum"a güvenilmez) · açılıp üye üye özet (md5/sha) alınır ve çalışma ağacındaki dosyayla
  eşitliği ölçülür (boyut yetmez) · beklenen özetler eşlik eden nota yazılır ki alıcı doğrulayabilsin · eski sürüm
  paketler aynı klasörde bırakılmaz (yanlışının gönderilme riski) (AX-DOC-CR-04).

## 4. Karar yayılımı ve ikinci kapı
Bir karar birden çok yerde yaşar (gövde kuralı, ekran tablosu, sözde kod, test, ek belge, onay listesi). Her karar kaydında
**yayılım tablosu** tutulur: `Karar no | Dokunulacak yer | Durum | Kim / ne zaman`. Liste tamamlanmadan karar kapanmış sayılmaz;
boş tablo kayıt geçersizdir. Düzeltme turu **ikinci kapıdan** geçer (`doc-checklist.md` — değişen satırlar, değişen sayı/adın
diğer geçtiği yerler, yayılım listesi; başka taze inceleyici).
Değişen bir sayı/adın eski değeri teslimden önce doküman **genelinde** aranır (`grep` ya da `doc_equivalence_check.py --closed-decision`).

## 5. Yeniden yazımda veri kaybı — `doc_equivalence_check.py`
FS gövdesi temizlenirken (İlke 2b) ya da doküman yeniden düzenlenirken çıkan her bilgi EK'e taşınır; kayıp ölçülür:
```
python <TEMPLATE>/skills-sap/sap-fs-ts-docs/scripts/doc_equivalence_check.py --old ESKI.md --new YENI.md --new EK-KARAR.md \
       [--closed-decision <kapanmış kararın eski değeri> …] [--report RAPOR.md]
```
| Ölçüm | Ne | Geçme koşulu |
|---|---|---|
| 0 Kapsam | taranan dosyalar + aynı klasörde **taranmayan** `.md` uyarısı | paket dosyaları eksiksiz verildi |
| 1 Kimlikler | FR-/BR-/AC-/TC-/SCR-/S-/K… kimlik kümeleri | eski \ yeni = boş |
| 2 Mockup/kod blokları | eski bloğun satırlarının ≥ %90'ı yeni kümede | kayıp blok yok |
| 3 Değerler | BÜYÜK_HARF obje/alan adları, 4+ haneli sayılar, tarihler, `kod` tokenları | eski \ yeni = boş (harf duyarsız) |
| 4 Cümleler | eski her cümle (≥ 40 karakter) yeni kümede bulanık eşleşmeyle | kayıp oranı ≤ eşik (varsayılan %3) |
| 5 Ters yön | `--closed-decision` değeri yeni pakette hâlâ geçiyor mu | geçiş yok ya da her geçiş "reddedilen alternatif" diye açıkça yazılı |

Çıkış: `0` denk · `1` kayıp var ya da kapanmış karar yaşıyor · `2` girdi okunamadı (bu "denk" **değildir**).
Rapor inceleyiciye kanıttır. **Aracın ölçmedikleri** (rapor §6): yeni içeriğin doğruluğu, belgeler arası tutarlılık, korunmuş ama
geçersiz değer (`--closed-decision` verilmezse), kapsam seçimi. Yeşil = "kayıp yok", "doküman doğru" değil.

## 6. Mevcut kaynaktan taslak spesifikasyon — `program_to_spec.py`
Eski ya da mevcut bir ABAP/CDS kaynağından yalnız **kaynakta gerçekten olan** teknik olguları (tablolar, seçim parametreleri,
çağrılan FM/BAPI, FORM/METHOD, ekran numaraları, sınıf/CDS varlıkları) çıkarır; anlatı bölümlerini `<TODO: …>` bırakır.
```
python <TEMPLATE>/skills-sap/sap-fs-ts-docs/scripts/program_to_spec.py <kaynak.abap> [<kaynak2.abap> …] [--out docs/TASLAK_<ad>.md]
```
- Kaynak yerelde yoksa önce `%sap-adt-foundation` ile okunur (`adt_get … include_source=true`); sistemden okunan kaynak taze kabul edilir.
- Çıktı **taslaktır**: `<TODO>`'lar kullanıcı spesifikasyonu ve çalışan uygulama davranışından doldurulur (tahmin yok), sonra
  şablona taşınır ve **spec mutabakatı** yapılır; mutabakatsız build yok.
- Regex tabanlıdır: yorum satırları (`*`) atılır, satır içi `"` yorumları ve makro/dinamik çağrılar ayrıştırılmaz; standart tablo
  listesi "Z/Y ile başlamayan" ipucudur, sistemde varlığı teyit edilir. "Tespit edilemedi" = "yok" değildir.
