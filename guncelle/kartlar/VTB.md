# VTB — taban bilinmiyor

**Tek cümle:** Bu dosyanın "en son aldığın hâli"ni bulamıyoruz; üç yollu birleştirme yapılamaz,
otomatik birleştirme YASAK.

## Ne demek
Karşılaştırmanın üçüncü ayağı (taban) yok. Tipik sebepler: klon sığ (`--depth` ile alınmış) ya da
geçmiş yeniden yazılmış; ya da bir proje dosyasının hangi şablon sürümünden türediği kayıtlı değil
ve geçmişte eşleşen bir sürüm de bulunamadı.

## Neden
Tabansız birleştirme = hangi değişikliğin kime ait olduğunu tahmin etmek. Tahminle birleştirilen
dosya sessizce yanlış olur; bu yüzden motor `oneri` komutunu bu vakada çalıştırmaz (çıkış 2).

## Adımlar
1. Kullanıcıya iki içeriğin farkını göster (yerel ↔ yeni).
2. Üç seçeneği sun: **yeniyi al** (`--karar yeni`) · **yereli koru** (`--karar yerel`) ·
   **elle karşılaştır** (`--karar ertelendi --gerekce "..."`).
3. Klon sığsa bunu ayrıca söyle: kalıcı çözüm `kur.cmd -Sifirla` ile temiz kuruluma dönmek ya da
   tam klon almaktır; sığ klonla her yayında aynı sorun tekrarlanır.
4. Kararı işaretle.

## Örnek
Yayın geçmişi bir sır sızıntısı nedeniyle temizlenmiş; eski taban commit'i artık yok.

## Beklenen çıktı
`DUR: <yol> için taban bilinmiyor (VTB) — otomatik birleştirme YASAK …` (çıkış 2) · karar sonrası
`İŞARETLENDİ: <yol> → yeni|yerel (dogrulandi)` ya da `ERTELENDİ: …`.

## DUR
Taban uydurma: "muhtemelen şu sürümdendi" diyerek birleştirme yapma. Emin değilsen ertele ve
gerekçesini yaz.

## Geri alma
Bir şey ters giderse: `guncelle.py geri-al <yol>` o dosyayı güncelleme öncesi hâline döndürür
(`hazirla` adımında atılan `guncelle-oncesi-<tarih>` etiketi). Hepsini birden geri almak için
`guncelle.py geri-al --hepsi`. Durum kaydı `geri_alindi` olur; kapanış bunu görür.
