# HOWTO — Kaynak çekirdekte gördüğün kusuru bildirmek (aXet bakımcısı)

> **Kime:** aXet bakımcısı. **Ne zaman:** aXet'e kural/skill aktarırken ya da aXet'te bir kusuru izlerken
> kusurun aXet'in beslendiği **kaynak çekirdekte** (metodoloji kaynağı; `sync-rules.json` kaynak yollarının
> ait olduğu depo) de olduğunu gördüğünde.
> **Yayın:** `maintenance/` public yayına girmez (`yayin_hazirla.py` `DISLANANLAR`) ama bu dosya geliştirme
> deposunda herkese açık görünür ⇒ kişi, müşteri, kurum ve iç depo adı yazılmaz; hedef depo daima `<ORG>/<REPO>`
> yer tutucusudur.
> **aXet KULLANICISININ aXet'e bildirimi başka yoldur:** `%hata-bildir` skill'i + public şablondaki Issue formu
> (`.github/ISSUE_TEMPLATE/hata-bildirimi.yml`). Bu dosya yalnız bakımcı → kaynak çekirdek yönünü anlatır.

## 1. Bildirilir mi? — önce kusurun YERİNİ ayır

| Kusur nerede | Ne yaparsın |
|---|---|
| Yalnız aXet uyarlamasında (aktarım hatası, aXet'e özgü araç/ortam: aXet kabuğu, `%` skill çağrısı, config) | aXet'te düzelt, iş listesine yaz. Kaynağa **bildirilmez** |
| Kaynakta — aXet'e aynen aktarılmış | aXet'te düzelt **+** kaynağa bildir (iş listesindeki madde bildirimi anar) |
| Kaynakta — aXet'e aktarılmamış (aXet'i etkilemiyor) | Ölçtüysen bildir; aXet işi açılmaz |
| Emin değilsin / ölçmedin | Bildirim YOK — önce §2 |

⛔ Kaynak çekirdeğin yerel kopyasına **yama yapılmaz**: tüketiciyiz, kanal yalnız Issue. Düzeltme fikri Issue'nun
ÖNERİ bölümüne yazılır; kaynağa fork/PR önerilmez (kaynağın kendi bildirim rehberi bunu söyler — oku).

## 2. Önce ölç — kontrol grubuyla, GÜNCEL kaynağa karşı

1. **Kontrol grubu:** sorunlu vaka + aynı mekanizmanın **çalıştığı bilinen** vaka. Aynı kirli girdiyle beş başarısız
   deneme hipotezi test etmez. Kontrol grubu bulunamıyorsa bunu gerekçesiyle yaz.
2. **Güncel `main`'de doğrula (salt-okur, çalışma ağacına dokunmadan):**
   ```bash
   git -C <KAYNAK-KLONU> fetch -q origin
   git -C <KAYNAK-KLONU> rev-list --count HEAD..origin/main      # kaç commit gerideyim → ORTAM'a
   git -C <KAYNAK-KLONU> grep -n -i "<desen>" origin/main -- .    # "X yok" iddiasını TÜM ağaçta ara
   git -C <KAYNAK-KLONU> show origin/main:<yol>                   # dosyanın güncel hâli
   ```
   **"X kaynakta YOK" en pahalı iddiadır:** yalnız kural klasörlerine bakmak yetmez; şablon, test ve script
   klasörlerini de ara ve aramanın kendisini (desen · dizin · sonuç sayısı) KAPSAM BEYANI'na yaz.
3. **Önce ara:** aynı bulgu kaynakta zaten açık mı?
   `gh issue list --repo <ORG>/<REPO> --state all --search "<anahtar kelime>"`. Açıksa **yeni Issue açılmaz**;
   ek kanıt o Issue'ya yorum olarak gider (§4).

## 3. Taslak — kaynağın kanıt formatıyla

Taslak **git dışı** bir yere yazılır (`.tmp/` ya da oturum scratch dizini), repoya commit'lenmez. Kaynağın kendi
bildirim rehberi / Issue formu varsa **onun başlıklarını aynen** kullan; yoksa:

```markdown
## ÖZET            — tek cümle: hangi mekanizma, hangi koşulda, ne yanlış yapıyor
## ORTAM           — kaynak commit + dal · geride commit sayısı (§2) · araç sürümü · OS/kabuk · sağlık denetimi sayıları
## BEKLENEN / GÖZLENEN — beklenti neye dayanıyor (kural adı / dosya:satır)
## YENİDEN ÜRETİM  — kopyalanıp çalıştırılabilir en kısa komut dizisi (3-5 satır)
## KANIT           — komut ÇIKTISI (anlatım değil); kırpıldıysa nerede
## KONTROL GRUBU   — çalıştığı bilinen vaka ya da "bulunamadı, çünkü …"
## KAPSAM BEYANI   — neye bakılmadı; "ölçülemedi" ≠ "temiz"
## ÖNERİ (ops.)    — düzeltme fikri; denenip çalışmayan yollar ve nedeni
```

Varsa aXet tarafındaki düzeltmeyi (commit/PR) ÖNERİ'de **ölçülmüş bir çözüm örneği** olarak anlat — kaynağa kod
dayatması olarak değil; kaynak kendi sürecinde yeniden ölçer.

## 4. Sızıntı kontrolü — gönderimden ÖNCE, her seferinde

Kaynak depo herkese açık kabul edilir; Issue metni cache'lenir, **geri alınamaz**.
- Temizlenecekler: müşteri/kurum adı · SAP sistem kimliği (SID, host, URL, istemci) · kullanıcı/kişi adı
  (yollardaki `C:\Users\<ad>` dahil) · e-posta · gerçek belge/obje numarası · müşteri paket/obje adı (`ZSD001` kullan)
  · makine mutlak yolları (`<PROJE-KOKU>`, `<AXET_HOME>`).
- Mekanik yardım: `maintenance/yayin_hazirla.py` içindeki `DESENLER` listesi yayın sızıntı taramasının **tek
  kaynağıdır**; aynı desenleri taslakta `rg` ile ara. ⚠ Desen taraması bulgusuz ≠ temiz: müşteri adının yeni bir
  biçimini, kişi adını, kod içeriğini yakalamaz — metni satır satır oku.

## 5. Kullanıcı onayı → gönderim

1. Kullanıcıya **taslağın tamamını** göster ve onay iste (beş unsur): ① tetikleyici — bu dosya, dışa dönük yayın
   ② kapsam — hangi depo (`<ORG>/<REPO>`), yeni Issue mi mevcut Issue'ya yorum mu, **ne yapılmayacak** (kaynak
   deposunda kod/PR yok) ③ neden şimdi ④ onaylamazsa ne olur ⑤ öneri. Açık "evet" olmadan gönderilmez; cevapsız
   onay = HAYIR; "hepsini yap" gibi gömülü onay bu yayını kapsamaz.
2. Gönderim — hedef **DAİMA açık**; `gh` hedefi verilmezse cwd'den çıkarır ve yanlış depoya yayın yapabilir:
   ```bash
   gh issue create  --repo <ORG>/<REPO> --title "<tek cümle>" --body-file <taslak.md>
   gh issue comment <N> --repo <ORG>/<REPO> --body-file <ek-kanit.md>     # bulgu zaten açıksa
   ```
   Kaynağın etiket geleneği varsa `--label <etiket>` eklenebilir; yazma yetkin yoksa etiket reddedilir ya da
   sessizce düşer → komut etiket yüzünden hata verirse `--label`'ı çıkarıp **aynen** tekrar koş.
3. ⛔ Komut Issue/yorum URL'i basmadıysa bildirim **gönderilmemiştir** — "gönderildi" yazma.
4. `git commit` ile `gh issue create` aynı kabuk çağrısına konmaz (hata hangi adımda çıktı belirsizleşir).

## 6. Gönderimden sonra — iş listesine kayıt ve takip

- **Aynı turda** [`IS-LISTESI.md`](IS-LISTESI.md)'de ilgili maddeye yaz: `<ORG>/<REPO>#<N>` · tarih · yeni Issue mi
  yorum mu · durum ("cevap bekleniyor"). Ayrı liste tutulmaz; açık madde tek yerde yaşar.
- Takip: yayın öncesi ve gün sonunda `gh issue view <N> --repo <ORG>/<REPO> --json state,labels,comments`.
  Kaynağın durum etiketleri varsa (değerlendiriliyor / onay bekliyor / onaylandı / reddedildi) maddeye işle.
- Kaynak düzeltmesi geldiğinde: aXet'e olağan eşitleme akışıyla ([`UPDATE-PROCEDURE.md`](UPDATE-PROCEDURE.md)) aktar,
  aXet tarafındaki geçici düzeltmeyle çakışıyorsa uyumla ve kusurun **aXet'te de** kapandığını ölç —
  "kaynakta merge edildi" ≠ "aXet'te düzeldi". Sonra iş listesindeki maddeyi kaynağıyla kapat.

## 7. Geçmiş örnekler (iş listesinden, genelleştirilmiş)

- **Yeni Issue:** bir worktree kapatma aracının salt-okunur öznitelikli dizinlerde dizin iskeletini bırakması —
  kanıt formatı + izole depoda iki kollu kontrol grubu + önerilen düzeltmenin ölçümüyle gönderildi; iddia, kaynak
  güncellendikten sonra **yeniden ölçülüp** aynen durduğu görüldü.
- **Mevcut Issue'ya yorum:** kaynak sahibinin zaten onayladığı açık bir bulguya yeni ölçek verisi ve bir karşı-bulgu
  ("önerilen alternatif şu koşulda da ayırt etmiyor") yorum olarak eklendi; yeni Issue açılmadı.
- **İki tarafta birden düzeltilen kusur:** aXet'e aynen aktarılmış bir kural aXet'te çalışmayan bir kurulum üretti;
  aXet'te düzeltildi, kaynakta da aynı kural bulunduğu için Issue açıldı ve iş listesindeki madde Issue'yu andı.
