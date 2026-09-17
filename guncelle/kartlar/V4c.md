# V4c — çakışmalı birleşme (yargı gerekir)

**Tek cümle:** Sen de biz de aynı yerlere dokunmuşuz; git tek bir doğru cevap üretemedi, birleşmeyi
sen önereceksin, kullanıcı onaylayacak.

## Ne demek
Üç sürüm var: **taban** (en son aldığın hâl), **yerel** (senin değiştirdiğin hâl), **yeni** (bu
yayındaki hâl). Git üçünü birleştirmeye çalıştı ve bazı bölgelerde iki tarafın satırları
kesiştiği için karar veremedi. O bölgeleri işaretledi:

```
<<<<<<< YEREL:<yol>
senin satırın
||||||| TABAN:<yol>
eski satır
=======
bizim satırımız
>>>>>>> YENİ:<yol>
```
(Etiketler motorun `git merge-file --diff3 -L YEREL/TABAN/YENİ` çağrısından gelir; ortadaki
`|||||||` bloğu TABAN'dır — neyin değiştiğini oradan okursun.)

**Bu en sık görülen yargı vakasıdır** ve çoğu zaman tehlikeli değildir: git **bitişik** satır
değişikliklerini de çakışma sayar (ölçüldü 2026-09-17 — 4. satır bizden, 5. satır senden ⇒ çakışma).
Yani "çakışma" çoğu kez "iki değişiklik yan yana düştü, insan baksın" demektir. Kullanıcıya bunu
böyle anlat; "bir şey bozuldu" izlenimi verme.

## Neden
Yerel değişikliğin bilinçlidir (bir kuralı gevşetmiş, bir eşiği değiştirmiş, kendi önekini
eklemiş olabilirsin) ve yeni sürüm de bir nedenle geldi. Varsayılan cevap çoğunlukla
**ikisini de koru**'dur; birini atmak sessiz bir kayıptır.

## Adımlar
1. `guncelle.py oneri <yol>` → çakışma işaretli dosya `.axet-guncelleme/oneri/<yol>`, ekranda
   iki fark + çakışma bloğu sayısı + yerel fark oranı.
2. Her çakışma bloğu için üç sürümü (taban / yerel / yeni) yan yana göster.
3. Kendi birleştirme önerini yaz ve **neden öyle birleştirdiğini** söyle. Varsayılan tutum:
   iki tarafın da niyetini koru; ancak gerçekten çelişiyorlarsa birini seç ve gerekçelendir.
4. Kullanıcı onaylarsa öneri dosyasını işaretsiz hâle getir (tüm `<<<<<<<`, `|||||||`,
   `=======`, `>>>>>>>` satırları gidecek).
5. `guncelle.py isaretle <yol> --karar birlesik` — motor çakışma işareti kalmadığını ve diske
   yazılanın geri okunduğunda aynı olduğunu doğrular.
6. Dosyanın sınıfı `validator` ya da `kritik_yol` ise akış adım 11: aynı örnek girdiyle önce/sonra
   hüküm karşılaştırması ZORUNLU.

## Örnek
`check_x.py` — sen bir kontrolü BLOCKER'dan WARNING'e düşürmüşsün; biz aynı fonksiyondaki ayrı bir
mantık hatasını düzeltmişiz. Doğru birleşme: **ikisi de kalır** (senin gevşetmen + bizim
düzeltmemiz) ve asgari güvence raporuna "yerelde gevşetilmiş validator" satırı girer.

## Beklenen çıktı
`oneri` çıkışı 1 (çakışma var) · sonra `İŞARETLENDİ: <yol> → birlesik (dogrulandi)`.
İşaret kalmışsa: `FAIL <yol>: öneri dosyasında çakışma işareti duruyor …` ve çıkış 1 — durum
`bekliyor` kalır, kapanış bu dosyayla 0 dönmez.

## DUR
- Çakışma bloğu 3'ten fazlaysa ya da yerel fark oranı %50'yi aşıyorsa motor vakayı
  **V4c+ESIK** olarak işaretler: birleştirmeyi DENEME, o kartı oku.
- Tahminle birleştirme. Bir bloğun ne işe yaradığını anlamıyorsan kullanıcıya sor ya da
  `--karar ertelendi --gerekce ...` ile o dosyayı açıkta bırak.
- Kullanıcı onaylamadan öneri dosyasını işaretleme.

## Geri alma
Bir şey ters giderse: `guncelle.py geri-al <yol>` o dosyayı güncelleme öncesi hâline döndürür
(`hazirla` adımında atılan `guncelle-oncesi-<tarih>` etiketi). Hepsini birden geri almak için
`guncelle.py geri-al --hepsi`. Durum kaydı `geri_alindi` olur; kapanış bunu görür.
