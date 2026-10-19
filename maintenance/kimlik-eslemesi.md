# Kontrol listesi kimlik eşlemesi (Z206)

> **Tarih:** 2026-10-19 · **Kaynak:** çekirdek `254134f` (kimlik kaydı `maintenance/kimlik-kaydi.json`, 454 kimlik; FS/TS şablonunun 6 örnek kimliği dışlanır)
> · **Kapsam:** 115 eski aXet kimliği · bugünkü tanımları 9 dosyada (aşağıdaki «Bugünkü tanım» sütunu; sayılar tablodan ölçülür). Bu dosya **tarihçe ve çeviri tablosudur** — eski numarayla
> yazılmış bir kayıt (iş listesi, yayın notu, eski oturum notu) okunurken yeni karşılığı buradan bulunur.
> Çekirdek başlık alıntıları («…») `maintenance/` altında bilerek tutulur (yayına girmez); kayıt dosyası
> (`kimlik-kaydi.json`) başlık taşımaz.

## Neden

aXet'in kontrol listesi maddeleri çekirdeğin kurallarından türer ama numaraları zamanla ayrışmıştı: aynı kural iki
depoda farklı numarayla (ör. aXet `FE-46` = çekirdek `FE-42`), farklı kural aynı numarayla (aXet `FE-42` sıfır
dolgusu ↔ çekirdek `FE-42` büyük yük) yaşıyordu. Aktarım haritası (`sync-rules.json`) her turda bunu elle not
düşüyordu; bir sonraki aktarımda yanlış kurala atıf riski sessizdi.

**Kural (2026-10-19'dan itibaren):**

1. **Numara sahipliği:** çekirdek ailelerinin (`BE-`, `FE-`, `DOC-*`, `UI-*`, `CLC-*`, `C-CDS-*`, `C-STR-*`,
   `C-TBL-*`, `DE-*` …) numarasını yalnız çekirdek verir. aXet bu ailelerde yeni numara **açmaz**.
2. **aXet'e özgü kural** `AX-<AİLE>-<nn>` alır (iki haneli numara; ör. `AX-FE-01`, `AX-CLC-ATC-01`). Bir `AX-`
   kimliği aXet'te **tek yerde** tanımlanır; çekirdek kimliği birden çok skill'de tanımlanabilir (aynı kural
   farklı bağlamda).
3. **Eşleme içerikten yapıldı**, numaradan değil: her eski satırın metni çekirdekteki kural metniyle karşılaştırıldı.
   Çekirdekte karşılığı olan → çekirdek kimliği; olmayan → `AX-`. Karşılık **aynı amaçlı listede** aranır: aXet'in
   bir OLUŞTURMA maddesinin çekirdekte yalnız İNCELEME karşılığı (`BE-nn` / `FE-nn`) varsa madde `AX-` kalır ve gerekçe
   sütunu o inceleme kimliğini gösterir (inceleme satırı aXet'te `sap-code-review` listelerinde çekirdek kimliğiyle durur).
4. **Birleşik satır:** aXet'in tek satırı çekirdekte birden çok kurala karşılık geliyorsa, aXet satırı ilk
   çekirdek kimliğini alır; diğerleri tabloda "birleşik" notuyla yazılır (içerik bölme ayrı iştir — Z196).

**Mekanik bekçi:** `python maintenance/sync_check.py --kimlik-denetle` (kök test takımında
`tests/test_kimlik_hizasi.py` koşar). Kayıt `--kimlik-kaydi` ya da `--update-lock` ile yenilenir. Kilit ve
kayıt aynı çekirdek commit'ini anlatır. `--update-lock` verildiğinde kural dosyası hatalıysa, KURALSIZ dosya
varsa, `CEKIRDEK_KAYNAK` kural dosyasının `sources` anahtarlarında yoksa ya da çekirdek kaydı üretilemiyorsa
**ikisi de yazılmaz**, çıkış kodu 0 olmaz ve mesaj basılır (`--json` kipinde stderr'e). Yazma sırası önce kayıt,
sonra kilit (ikisi de geçici dosya + `os.replace`): kayıt yazılamazsa kilit eski kalır. Kayıt yazılıp kilit
yazılamazsa (G/Ç hatası) kayıt yeni, kilit eski kalır — tam atomiklik YOK; bu yön güvenlidir çünkü sonraki
koşum farkı DEĞİŞEN olarak yine gösterir (çıkış 3 + mesaj). Yalnız `--kimlik-kaydi` kilide dokunmaz; KURALSIZ
dosya onu durdurmaz, kural dosyası hatası ve üretilemeyen kayıt durdurur. Kirli çekirdek ağacında kayıt `kirli: true` taşır;
aktarım denetimi (`--source DEV_CORE=…`) her koşumda **KİMLİK UYUMU** uyarı listesini basar (çıkış kodunu
değiştirmez): çekirdekte olup aXet'te olmayan kimlikler + aynı numarada başlığı uzaklaşmış satırlar.

**Dar muafiyet:** `skills-sap/sap-adt-foundation/references/known-errors-adt.md` içindeki `K-nn` başlıkları
bilinen-hata kataloğunun indeksidir (kontrol listesi değil); çekirdekte `K-` ailesi yok. Muafiyet yalnız
(o dosya, `K` ailesi) çiftine verilir; tekillik yine aranır. Çekirdek bir gün `K-` açarsa denetim UYARI basar.

## Kontrol listeleri (FE · UI · DOC · CLC · AF · sap-code-review)

| Eski | Yeni | Gerekçe (eşleşen çekirdek başlığı ya da aXet'e özgü) | Bugünkü tanım |
|---|---|---|---|
| `FE-42` | `AX-FE-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; eski aXet FE-42 sıfır dolgusu kuralıydı; çekirdek FE-42 başka kural (büyük yük → HTTP 414) | `skills-sap/sap-ui5-fiori/references/checklists.md:125` |
| `FE-43` | `FE-46` | çekirdek «UI5 bootstrap'ı dış CDN'e sabitlenmiş patch'ten yükleniyor →» | `skills-sap/sap-ui5-fiori/references/checklists.md:121` |
| `FE-44` | `FE-45` | çekirdek «Tarih-yalnız (Edm.DateTime + sap:display-format="Date", arka» | `skills-sap/sap-ui5-fiori/references/checklists.md:120` |
| `FE-45` | `FE-47` | çekirdek «Function import urlParameters'ına null değer verildi → 400 "» | `skills-sap/sap-ui5-fiori/references/checklists.md:122` |
| `FE-46` | `FE-42` | çekirdek «OData V2 callFunction BÜYÜK YÜK taşıyor → HTTP 414 (Request-» | `skills-sap/sap-ui5-fiori/references/checklists.md:118` |
| `FE-47` | `FE-43` | çekirdek «İkinci ODataModel kuruldu ama metadataUrlParams DEVRALINMADI» | `skills-sap/sap-ui5-fiori/references/checklists.md:119` |
| `DOC-TS-06` | `AX-DOC-TS-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-TS-06` başka kural («Legacy (ECC) izi mi, S/4 standardı mı?») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:65` |
| `DOC-TS-07` | `AX-DOC-TS-02` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-TS-07` başka kural («Obje listesi ↔ tasarım iki yönlü kapalı:») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:66` |
| `DOC-TS-08` | `AX-DOC-TS-03` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek CLC-SCR7'nin belge tarafı genellemesi; belge kuralı olarak aXet'e özgü | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:67` |
| `DOC-CR-04` | `AX-DOC-CR-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-CR-04` başka kural («Muğlak ifade kararı gizler:») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:75` |
| `DOC-CR-05` | `AX-DOC-CR-02` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-CR-05` başka kural («Zorunlu kesitler SESSİZCE yok olamaz:») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:76` |
| `DOC-CR-06` | `AX-DOC-CR-03` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-CR-06` başka kural («Kaynak izi — etiketsiz varsayım YOK:») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:77` |
| `DOC-CR-07` | `AX-DOC-CR-04` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:78` |
| `DOC-CR-08` | `AX-DOC-CR-05` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:79` |
| `DOC-FS-08` | `AX-DOC-FS-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `DOC-FS-08` başka kural («Gereksinim izlenebilirliği — yetim gereksinim YOK:») | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:55` |
| `DOC-KD-17` | `AX-DOC-KD-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-fs-ts-docs/references/doc-checklist.md:42` |
| `OD-01` | `AX-OD-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-odata-backend.md:11` |
| `OD-02` | `AX-OD-02` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-odata-backend.md:12` |
| `OD-03` | `AX-OD-03` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-odata-backend.md:13` |
| `OD-04` | `AX-OD-04` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-odata-backend.md:14` |
| `OD-05` | `AX-OD-05` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-odata-backend.md:15` |
| `CC-01` | `AX-CC-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-clean-core.md:18` |
| `CC-02` | `AX-CC-02` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-clean-core.md:19` |
| `CC-03` | `AX-CC-03` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-clean-core.md:20` |
| `SR-01` | `AX-SR-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-common.md:12` |
| `SR-02` | `AX-SR-02` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-common.md:13` |
| `SR-03` | `AX-SR-03` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-code-review/references/checklist-common.md:14` |
| `UI-BOOT-05` | `AX-UI-BOOT-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek UI-BOOT-05 başka kural (aXet'te eski UI-BOOT-06 olarak duruyordu) | `skills-sap/sap-ui5-fiori/references/checklists.md:21` |
| `UI-BOOT-06` | `UI-BOOT-05` | çekirdek «Manifest DIŞI her istek (new ODataModel(...) — varyant/$batc» | `skills-sap/sap-ui5-fiori/references/checklists.md:20` |
| `UI-SAVE-05` | `AX-UI-SAVE-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-22` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok; çekirdek UI-SAVE-05 başka kural (aXet'te eski UI-SAVE-06 olarak duruyordu) | `skills-sap/sap-ui5-fiori/references/checklists.md:40` |
| `UI-SAVE-06` | `UI-SAVE-05` | çekirdek «Belge kilidi varsa: unload bırakma = fetch + keepalive + CSR» | `skills-sap/sap-ui5-fiori/references/checklists.md:39` |
| `UI-ARCH-05` | `AX-UI-ARCH-01` | aXet'e özgü oluşturma maddesi — ALV özellikleri ayağı çekirdek oluşturma listesinde kısmen `UI-PERSO-01` (ui-freestyle-creation; aXet'te aynı kimlikle `checklists.md:56`); grid ayağı yalnız çekirdek inceleme maddesi `FE-13` (bug-checklist-frontend) | `skills-sap/sap-ui5-fiori/references/checklists.md:30` |
| `UI-BIND-04` | `AX-UI-BIND-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-07` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-ui5-fiori/references/checklists.md:48` |
| `UI-VH-03` | `AX-UI-VH-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-32` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-ui5-fiori/references/checklists.md:55` |
| `UI-FIN-05` | `AX-UI-FIN-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-11` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-ui5-fiori/references/checklists.md:65` |
| `UI-FIN-06` | `AX-UI-FIN-02` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-20` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-ui5-fiori/references/checklists.md:66` |
| `UI-FIN-07` | `AX-UI-FIN-03` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `FE-17` (bug-checklist-frontend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-ui5-fiori/references/checklists.md:67` |
| `CLC-SCR7` | `AX-CLC-SCR-01` | aXet'e özgü — çekirdekte içerik karşılığı yok; çekirdek `CLC-SCR7` başka kural («Üreteç kılavuzundaki &lt;!-- FM-IMZA --> bloğu FM kay») | `skills-sap/sap-classic-abap/references/checklists.md:35` |
| `CLC-ALV4` | `AX-CLC-ALV-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:23` |
| `CLC-ALV5` | `AX-CLC-ALV-02` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-63` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:24` |
| `CLC-PRF` | `AX-CLC-PRF-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:12` |
| `CLC-TTL` | `AX-CLC-TTL-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:15` |
| `CLC-SEL` | `AX-CLC-SEL-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-58` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:41` |
| `CLC-ATC` | `AX-CLC-ATC-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-12` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:43` |
| `CLC-ATC2` | `AX-CLC-ATC-02` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-classic-abap/references/checklists.md:44` |
| `AF-ERR` | `AX-AF-ERR-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-classic-abap/references/forms-f1-help.md:52` |

## DDIC ve CDS (sap-cds-ddic · sap-code-review CDS satırları)

Eski aXet DDIC kimlikleri numarasızdı (`CDS-NAME`, `TBL-CUR`, `STR-FIELD-2` …); çekirdeğin `C-CDS-*`, `C-STR-*`,
`C-TBL-*`, `DE-*` ailelerine içerikten eşlendi. **Birleşik** notlu satırlar: aXet'in tek satırı çekirdekte
birden çok kuralı kapsıyor.

| Eski | Yeni | Gerekçe (eşleşen çekirdek başlığı ya da aXet'e özgü) | Bugünkü tanım |
|---|---|---|---|
| `CDS-NAME` | `C-CDS-NAME-01` | çekirdek «View adı ZSD&lt;NNN>_DDL_ pattern'inde mi?» | `skills-sap/sap-cds-ddic/references/checklists.md:15` |
| `CDS-TYPE` | `AX-CDS-TYPE-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:16` |
| `CDS-SQLV-1` | `C-CDS-SQLV-01` | çekirdek «@AbapCatalog.sqlViewName annotation var mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:17` |
| `CDS-SQLV-2` | `C-CDS-SQLV-02` | çekirdek «sqlViewName whitelist regex'ine uyuyor mu? Regex SABİT DEĞİL»; **birleşik** — çekirdekte ayrıca C-CDS-SQLV-03 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:18` |
| `CDS-LABEL` | `C-CDS-LABEL-01` | çekirdek «@EndUserText.label annotation var mı ve TR dolu mu?» | `skills-sap/sap-cds-ddic/references/checklists.md:19` |
| `CDS-AUTH-1` | `C-CDS-AUTH-01` | çekirdek «@AccessControl.authorizationCheck annotation var mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:20` |
| `CDS-AUTH-2` | `AX-CDS-AUTH-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-67` (bug-checklist-backend) ve ADT deseni `CDS-DCL-01` (aXet `cds.md` §2'de aynı kimlikle tanımlı); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:21` |
| `CDS-DEPR` | `C-CDS-DEPR-01` | çekirdek «@AbapCatalog.preserveKey kullanılmış mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:22` |
| `CDS-WIN` | `C-CDS-WIN-01` | çekirdek «OVER PARTITION BY (window function) kullanılmış mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:23` |
| `CDS-FROM-1` | `C-CDS-FROM-01` | çekirdek «Kaynak tablolar/CDS'ler SAP'de mevcut mu?»; **birleşik** — çekirdekte ayrıca C-CDS-FROM-02 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:24` |
| `CDS-FROM-2` | `C-CDS-FROM-03` | çekirdek «Standart tablo alanları (KNA1.name1 gibi) yeni sistemde var » | `skills-sap/sap-cds-ddic/references/checklists.md:25` |
| `CDS-FROM-3` | `C-CDS-FROM-04` | çekirdek «Clean Core: std tablo (MARA/VBAP/LIPS) yerine released CDS?» | `skills-sap/sap-cds-ddic/references/checklists.md:26` |
| `CDS-FROM-4` | `C-CDS-FROM-05` | çekirdek «Classic DDIC view» | `skills-sap/sap-cds-ddic/references/checklists.md:27` |
| `CDS-CUR` | `C-CDS-CUR-02` | çekirdek «CURR field'ın annotation'ı @Semantics.amount.currencyCode qu»; **birleşik** — çekirdekte ayrıca C-CDS-CUR-03 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:28` |
| `CDS-NS` | `C-CDS-NS-01` | çekirdek «Eski &lt;LEGACY_SOURCE> source'tan kopyalanmışsa zsd_007_ → zsd»; **birleşik** — çekirdekte ayrıca C-CDS-NS-02 (alan rename'leri) ve C-CDS-TD-02 (spesifikasyonda silinen alanlar) aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:29` |
| `CDS-KEY` | `C-CDS-KEY-01` | çekirdek «En az 1 key field var mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:30` |
| `CDS-AGG` | `C-CDS-AGG-01` | çekirdek «sum() / count() kullanılmış ise group by var mı?»; **birleşik** — çekirdekte ayrıca C-CDS-AGGUNIT-01 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:31` |
| `CDS-UNION` | `C-CDS-UNION-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:32` |
| `CDS-CONVEXIT` | `C-CDS-CONVEXIT-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:33` |
| `CDS-QTYEXPR` | `C-CDS-QTYEXPR-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:34` |
| `CDS-CONSUME` | `C-CDS-CONSUME-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:35` |
| `CDS-FIELDRM` | `C-CDS-FIELDRM-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:36` |
| `CDS-2PHASE` | `C-CDS-2PHASE-01` | çekirdek «MUST» | `skills-sap/sap-cds-ddic/references/checklists.md:37` |
| `CDS-JOINCAST` | `AX-CDS-JOINCAST-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:38` |
| `CDS-CONCAT` | `AX-CDS-CONCAT-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-59` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:39` |
| `CDS-CURRCONV` | `AX-CDS-CURRCONV-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:40` |
| `CDS-CAPA` | `AX-CDS-CAPA-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-27` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:41` |
| `CDS-VERIFY` | `AX-CDS-VERIFY-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:42` |
| `CDS-DESC` | `AX-CDS-DESC-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:43` |
| `CDS-DUP` | `AX-CDS-DUP-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:44` |
| `CDS-DCL-03` | `AX-CDS-DCL-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/cds.md:159` |
| `DE-REUSE-1` | `DE-REUSE-01` | çekirdek «Reuse-first:» | `skills-sap/sap-cds-ddic/references/checklists.md:53` |
| `DE-REUSE-2` | `DE-REUSE-02` | çekirdek «Aynı işi gören mevcut Z DTEL/domain var mı? (adt_search_obje» | `skills-sap/sap-cds-ddic/references/checklists.md:54` |
| `DE-NAME` | `DE-NAM-01` | çekirdek «Naming: Domain ZSD&lt;pkg>_D_, Data Element ZSD&lt;pkg>_E_ (std 01» | `skills-sap/sap-cds-ddic/references/checklists.md:55` |
| `DE-LANG` | `DE-TR-01` | çekirdek «TR master:» | `skills-sap/sap-cds-ddic/references/checklists.md:56` |
| `DE-LABEL` | `DE-TR-02` | çekirdek «DTEL 4 field label (short/medium/long/heading) TAM TR doldur» | `skills-sap/sap-cds-ddic/references/checklists.md:57` |
| `DE-TEXT` | `DE-TXT-01` | çekirdek «Açıklama/label spec'ten (&lt;LEGACY_SOURCE>/proje) — ASLA tahmi» | `skills-sap/sap-cds-ddic/references/checklists.md:58` |
| `DE-DOM` | `DE-DOM-01` | çekirdek «Domain fixed values / value table gerekiyorsa tanımlı; data » | `skills-sap/sap-cds-ddic/references/checklists.md:59` |
| `DE-BUILTIN` | `AX-DE-BUILTIN-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:60` |
| `DE-VERIFY` | `DE-ACT-01` | çekirdek «Aktivasyon öncesi REST GET ile TR text + tip doğrulanır; son» | `skills-sap/sap-cds-ddic/references/checklists.md:61` |
| `DE-STD` | `DE-005` | çekirdek «Standart DTEL/domain'e dokunma YASAK; append field/DTEL adın» | `skills-sap/sap-cds-ddic/references/checklists.md:62` |
| `STR-NAME` | `C-STR-NAME-01` | çekirdek «Obje adı ZSD&lt;NNN>_S_&lt;NAME> regex'ine uyuyor mu?»; **birleşik** — çekirdekte ayrıca C-STR-NAME-02 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:69` |
| `STR-LABEL` | `C-STR-LABEL-01` | çekirdek «@EndUserText.label annotation var mı?»; **birleşik** — çekirdekte ayrıca C-STR-LABEL-02, C-STR-LABEL-03 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:70` |
| `STR-FIELD-1` | `C-STR-FIELD-01` | çekirdek «Her field için DTEL referansı var mı (built-in tip değil, cu» | `skills-sap/sap-cds-ddic/references/checklists.md:71` |
| `STR-FIELD-2` | `C-STR-FIELD-02` | çekirdek «Kullanılan tüm ZSD&lt;NNN>_E_ DTEL'ler SAP'de aktif mi?» | `skills-sap/sap-cds-ddic/references/checklists.md:72` |
| `STR-FIELD-3` | `C-STR-FIELD-03` | çekirdek «Standart SAP DTEL referansları (MANDT, ERNAM, ERDAT, vb.) do» | `skills-sap/sap-cds-ddic/references/checklists.md:73` |
| `STR-FIELD-4` | `C-STR-FIELD-04` | çekirdek «İki field aynı isimde mi (case-insensitive duplicate)?» | `skills-sap/sap-cds-ddic/references/checklists.md:74` |
| `STR-CUR` | `C-STR-CUR-02` | çekirdek «CURR field var ise, hemen üstünde @Semantics.amount.currency»; **birleşik** — çekirdekte ayrıca C-STR-CUR-03..05 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:75` |
| `STR-UNIT` | `C-STR-UNIT-01` | çekirdek «QUAN field var ise, @Semantics.quantity.unitOfMeasure annota»; **birleşik** — çekirdekte ayrıca C-STR-UNIT-02 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:76` |
| `STR-DEPR` | `C-STR-DEPR-01` | çekirdek «@AbapCatalog.preserveKey annotation kullanılmış mı?» | `skills-sap/sap-cds-ddic/references/checklists.md:77` |
| `STR-COMMENT` | `AX-STR-COMMENT-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:78` |
| `STR-SPEC` | `C-STR-KAP-01` | çekirdek «&lt;LEGACY_SOURCE> md'sinde "silinen alan" var ise yeni source'»; **birleşik** — çekirdekte ayrıca C-STR-KAP-02 (field rename'leri) aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:79` |
| `STR-VERIFY` | `AX-STR-VERIFY-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:80` |
| `TBL-APPROVAL` | `AX-TBL-APPROVAL-01` | aXet'e özgü oluşturma maddesi — çekirdekte inceleme karşılığı `BE-13` (bug-checklist-backend); çekirdeğin oluşturma listesinde karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:89` |
| `TBL-NAME` | `C-TBL-NAME-01` | çekirdek «Tablo adı ZSD&lt;NNN>_T_ pattern'inde mi?» | `skills-sap/sap-cds-ddic/references/checklists.md:90` |
| `TBL-SOURCE` | `C-TBL-SOURCE-01` | çekirdek «Mevcut SAP source'u GET ile alındı mı (yeni alanlar arası re» | `skills-sap/sap-cds-ddic/references/checklists.md:91` |
| `TBL-MANDT` | `AX-TBL-MANDT-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:92` |
| `TBL-ENH` | `AX-TBL-ENH-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:93` |
| `TBL-NOTNULL` | `AX-TBL-NOTNULL-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:94` |
| `TBL-DTEL` | `C-TBL-DTEL-01` | çekirdek «Yeni alanların DTEL'leri SAP'de aktif mi?»; **birleşik** — çekirdekte ayrıca C-TBL-STD-01 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:95` |
| `TBL-CUR` | `C-TBL-CUR-02` | çekirdek «CURR field için reference field (CUKY) aynı tabloda var mı V»; **birleşik** — çekirdekte ayrıca C-TBL-CUR-03, C-TBL-CUR-04 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:96` |
| `TBL-QUAN` | `C-TBL-QUAN-01` | çekirdek «QUAN field için reference unit (MEINS/VRKME tarz) tabloda va»; **birleşik** — çekirdekte ayrıca C-TBL-QUAN-02 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:97` |
| `TBL-DROP` | `C-TBL-DROP-01` | çekirdek «Mevcut alan SİLİNİYOR mu? (TEHLİKE — DROP risk)»; **birleşik** — çekirdekte ayrıca C-TBL-DROP-02, C-TBL-RENAME-01, C-TBL-TYPE-01 aynı aXet satırına karşılık gelir | `skills-sap/sap-cds-ddic/references/checklists.md:98` |
| `TBL-APPEND` | `C-TBL-APPEND-01` | çekirdek «Standart SAP tablosuna append eklenmiyor mu? (⛔ KATEGORİ A —» | `skills-sap/sap-cds-ddic/references/checklists.md:99` |
| `TBL-DLVCLASS` | `C-TBL-DLI-01` | çekirdek «DeliveryClass değişiyor mu?» | `skills-sap/sap-cds-ddic/references/checklists.md:100` |
| `TBL-MAINT` | `C-TBL-MAINT-01` | çekirdek «DataMaintenance değişiyor mu?» | `skills-sap/sap-cds-ddic/references/checklists.md:101` |
| `TBL-ORDER` | `C-TBL-ORDER-01` | çekirdek «Yeni iş alanı audit bloğunun ÜSTÜNE mi eklendi? Audit bloğu » | `skills-sap/sap-cds-ddic/references/checklists.md:102` |
| `TBL-SPEC` | `C-TBL-TD-01` | çekirdek «TD spec'teki alan listesi ile yeni source uyumlu mu (alan sa» | `skills-sap/sap-cds-ddic/references/checklists.md:103` |
| `TBL-VERIFY` | `AX-TBL-VERIFY-01` | aXet'e özgü — çekirdekte içerik karşılığı yok | `skills-sap/sap-cds-ddic/references/checklists.md:104` |

## Bilinçli olarak çevrilmeyen yerler

- `maintenance/IS-LISTESI.md` ve `guncelle/yayinlar.json`: tarihli kayıtlardır; o tarihteki numarayla kalır.
  Eski numara bu tablodan çevrilir.
- `maintenance/sync-rules.json`: notlarda aXet tarafı yeni kimliğe çevrildi, "eski adı …" / "Z206 öncesi …" eki
  bırakıldı; **kaynak tarafı** ("kaynak FE-45/46/47" gibi) çekirdek numarasıdır, değişmedi.
- `skills-sap/sap-adt-foundation/IMPLEMENTATION.md` `STR-FIELD-3` / `STR-FIELD-2` atıfları
  (→ `C-STR-FIELD-03` / `C-STR-FIELD-02`): o dosya aynı turda başka bir kulvarda; entegrasyonda çevrilir.

## İçerik farkları (numara korundu, metin ayrışmış — Z196)

- `UI-BOOT-01` ve `UI-SAVE-04`: konu çekirdekle aynı, aXet metni farklılaşmış; numara korundu.
- Çekirdek `FE-44` (istemci boyut kapısı) aXet'te henüz yok.
- Çekirdekte olup aXet'te olmayan kimliklerin tam listesi: `sync_check.py --source DEV_CORE=…` çıktısındaki
  KİMLİK UYUMU bölümü (2026-10-19 ilk ölçüm: 143 kimlik / 58 aile; şablon örnek kimlikleri dışlandıktan sonra 137 / 54). Birleşik satırın ikinci çekirdek kimliği (ör. C-CDS-TD-02, C-STR-KAP-02) bu listede yine «eksik» görünür: uyum raporu yalnız tanım hücresini okur, satır içi "çekirdekte ayrıca …" notunu okumaz.
