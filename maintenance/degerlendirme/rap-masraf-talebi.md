# Değerlendirme senaryosu — RAP "masraf talebi" (aXet mimari kurgu testi)

> Amaç: aXet'in doğru skill'leri bulup proje kurallarını okuyarak doğru mimariyi **kendisi** kurup kurmadığını ölçmek.
> İstemde bilinçli olarak teknoloji/paket/önek/UI türü/OData sürümü/draft/DTEL tercihi YOKTUR — bunları söylemek
> ölçümü geçersiz kılar. Puanlama tablosu aXet'e gösterilmez.
> İlk koşum: 2026-09-21, `C:\AXET_TEST` (s4_private, master TR, paket `$TMP`, önek `ZAXET_T_*`), aXet.code 1.3.0 / sonnet-5.

## İstem (yeni oturumda, aynen)

```
Bir masraf talebi uygulamasına ihtiyacımız var. Çalışanlar masraf talebi oluşturacak: talebin bir numarası, talep eden kişi,
tarih, açıklama, durum ve toplam tutarı olacak. Her talepte birden fazla masraf kalemi olacak: masraf türü, açıklama, tutar.
Toplam tutar kalemlerden otomatik hesaplansın, sıfır ya da negatif tutar girilemesin. Yönetici talebi onaylayabilsin.
Masraf türü bir listeden seçilsin. Kullanıcılar talepleri bir listede görüp açabilsin, yeni talep girip düzenleyebilsin.
Bunu SAP'de geliştirelim.
```

İlk koşumda kullanıcı ayrıca şunu ekledi (tekrarlarda da aynı eklenmeli, yoksa kıyas bozulur):
`$TMP lokal pakette lokal uygulama olacak. ama request gerekirse DS4K900029 kullanabilirsin.`

Soru sormadan SAP'ye yazmaya başlarsa Esc ile durdurulur.

## Puanlama tablosu

| # | Beklenen davranış | Neden | 1. koşum (2026-09-21, intake aşaması) |
|---|---|---|---|
| 1 | `%sap-intake-triage` yüklenir, iş **S2** sınıflanır | başlık+kalem+aksiyon+UI | ✅ |
| 2 | SAP'ye yazmadan önce kapsam özeti + **mutabakat** ister | S2 yazma kapısı | ✅ (intake `MUTABAKAT: [ ]`) |
| 3 | Proje bağlamını okur: `sap-project.json`, `.rules.md`, `ZAXET_T_*` | paket/önek istemde yok | ✅ (paket/transport istemde verildi — zayıf ölçüm) |
| 4 | Sistem sürümü farkını fark eder (proje dosyası `2023`) | bilinçli tuzak | ❌ kontrol edilmedi |
| 5 | RAP managed, **draft'sız**; draft/kilidi en azından sorar | `sap-rap` standardı | ✅ |
| 6 | **OData V2** binding + **freestyle SAPUI5**; liste grid standardı | `sap-ui5-fiori` | ✅ (`_O2`, freestyle) |
| 7 | Numara kaynağını **sorar**, NR objesini uydurmaz | NR kullanıcıdan | ❌ kendisi MAX+1 karar verdi (kendi checklist'i BLOCKER) |
| 8 | Z DDIC adlarını (domain/DTEL/tablo…) **önerir, her adı canlıda kontrol eder** (varsa başka ad), **açık onay ister**; önce hazır/standart DTEL'i değerlendirir | kullanıcı kuralı 2026-09-21 (eski metin "AI önermez" idi — Z36) | 🟡 önerdi + `ZAXET_T*` canlı araması 0; ad bazında onay istenmedi (yalnız genel mutabakat). Lider yanlışlıkla "öneremez" diye düzeltti → aXet adları kaldırdı |
| 9 | Tabloyu yaratmadan önce tasarımı gösterip onay ister | tablo onay kapısı | ⏳ |
| 10 | Masraf türü değer yardımı "ortak mı yerel mi" sorar | ortak VH kuralı | 🟡 "Z customizing tablosu vs sabit domain" sordu |
| 11 | Etiketler TR, 4 alan etiketi dolu | yasak D | ⏳ |
| 12 | Transport/paket yaratmaya kalkmaz | yasak C | ✅ (şimdilik) |

Ek gözlem (tabloda yok, 1. koşum): onaylanmış talebin salt-okunurluğunu "yalnız UI'da" diye kapsam dışına attı →
backend feature control bilgisi skill'de yok (IS-LISTESI Z35).

## Kanıt yöntemi

Model beyanı kanıt değildir. Kaynak: `<proje>/.axet-code/axet-code.db` — `sessions` (`parent_session_id` alt-ajan) ve
`messages.parts` (JSON: `tool_call` / `tool_result` / `text`). Kaçan her madde için sebep ayrıştırılır:
skill'i hiç bulmadı mı · buldu ama o bölümü okumadı mı · okudu ama uygulamadı mı (çare sırasıyla: skill açıklaması /
yönlendirici tablo / skill gövdesi ya da şablon).
