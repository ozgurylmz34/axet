# Uyum turu 8 — A1 kulvarı karar tablosu (ad politikası · müşteri namespace'i · validator'lar)

Kaynak: DEV_CORE `dd9ba0f..c457161` (e52ad6f · ac9231e · 27ae65e · d6572b3 · ce8a124 · d8346ec · f15becb · 8565c9d ·
9c8c57a · 57295a3 · d7f2fa0) · tarih 2026-11-17.
Kulvar: `sapadt/gate.py` · `sapadt/guardrails.py` · `sapadt/lib/validators/*` · `sapadt/lib/utils/*` (abap_metot_blok hariç) ·
`scripts/check_package_naming.py` · namespace/validator testleri. Testler worktree `C:/AI_WORKS/.wt/axet/t8/skills-sap/sap-adt-foundation`
içinde, her biri ayrı komut, tek `-k`. Yol kısaltması: `F` = `skills-sap/sap-adt-foundation`, `VAL` = `F/scripts/sapadt/lib/validators`.

## Karar tablosu

| Kaynak dosya | Karar | aXet hedef | Ne aktarıldı / gerekçe | Test → sonuç |
|---|---|---|---|---|
| `scripts/utils/ad_politikasi.py` (YENİ; e52ad6f + ac9231e + ce8a124 + d8346ec) | UYARLA | `F/scripts/sapadt/lib/utils/ad_politikasi.py` (YENİ) | Tek ad politikası: Z/Y (+ENQU E+Z/Y) daima müşteri; `/<NS>/` YALNIZ `sap-project.json` `"customer_namespaces": ["/<NS>/"]` ile bildirilmişse. FAIL-CLOSED: liste değil · geçersiz öğe (`^/[A-Z0-9_]{3,8}/` ASCII) · kök düzeyde mükerrer anahtar · bozuk JSON · proje kökünde `.conn_adt` yok · açık kök ≠ bağlantı dizini ⇒ namespace kabulü KAPALI, Z/Y etkilenmez; ortam değişkeni listeyi genişletmez. `url_segmenti` (Z adında `.lower()` ile bayt-aynı, `/NS/X`→`%2Fns%2Fx`, idempotent) · `AD_ADAYI`/`AD_DESENI`/`ad_coz`/`musteri_karari` (iki katmanlı gramer) · `dosya_adi`/`dosya_adindan_ad` (`#ns#x`) · `yerel_ad` · `musteri_govdesi` · `odata_servis_yolu` · FUGR include/ana program. `project.yaml` → `sap-project.json` | `python tests/run_tests.py -k ad_politikasi` → 28/28 · 27 test 0 failure |
| `mcp_servers/sap_adt/guardrails.py` (e52ad6f) | UYARLA | `F/scripts/sapadt/guardrails.py` | `_is_customer_namespace` / `require_customer_namespace` / `reject_standard_delete` → `ad_politikasi.musteri_adi_mi`; red metni bildirilmemiş namespace gerekçesini söyler; `root=` parametresi | aynı (KapiNamespace K1-K11) + `-k guard` 35/35 |
| `mcp_servers/sap_adt/_app.py` · gate tarafı (e52ad6f) | UYARLA | `F/scripts/sapadt/gate.py` | `check_names(..., root=)` tüm koruyuculara kök geçirir; `check_write` aynı kökü kullanır | `-k ad_politikasi` KapiNamespace (CLI alt süreç) |
| `scripts/sap_adt_lib.py` — ad doğrulaması (e52ad6f, ce8a124 G6) | UYARLA (Edit, A2 dosyası) | `F/scripts/sapadt/lib/sap_adt_lib.py` `validate_object_name` · `validate_package_name` · `SAPADTClient._validate_object_name(referans=)` | Namespace dalı karakter regex'inden önce; `/`'lı paket bildirilmiş namespace olmalı; referans adda (ref_structure) yalnız biçim denetimi. URL kurucularının kodlaması A2'de | `-k ad_politikasi` Yuklayici · `-k lib_regressions` 13/13 · `-k inprocess` 34/34 |
| `governance/decisions/0005-*` (A-EK) — Yasak B tarayıcısı | UYARLA | `F/scripts/sapadt/std_dml_scan.py::_izinli` (+ `std_ext_scan.izinli` aynı fonksiyonu kullanır) | Z/Y ya da bildirilmiş namespace izinli; bildirilmemiş `/Z…/`, `/Y…/` artık STANDART ⚠SIKILAŞTIRMA (lider kabulü). `std_ext_scan` docstring + `test_std_ext_gate` g/g2 vakaları NEGATİF→POZİTİF taşındı | `-k StdDml` 40/40 · `-k std_ext` 160/160 (23 test) |
| e52ad6f — SKILL/IMPLEMENTATION metinleri | UYARLA (Edit, ortak dosya) | `F/SKILL.md` :115 · :126 · :127 · :128 · `F/IMPLEMENTATION.md` §12 · `F/references/foundation-ops.md` :265 | "Z/Y öneki" → müşteri ad alanı (Z/Y ya da bildirilmiş `/<NS>/`, fail-closed); "namespace bugün desteklenmiyor" bilinen sınırı kaldırıldı; std_dml/std_ext izinli hedef ifadesi | metin; `-k static` (yasak dizge) bu dosyalarda temiz |
| `scripts/utils/ddic_semantics.py` (f15becb + EK-3) | UYARLA | `F/scripts/sapadt/lib/utils/ddic_semantics.py` | `konwa`/`konws` CUKY · `kmein`/`konms` UNIT eklendi; `curr` CURR_DTELS'ten ÇIKARILDI ⚠GEVŞETME (kaynakta sahip onaylı; DD04L'de 0 satır, yalnız CDS ad sezgisini şişiriyordu) | `-k validator_ad` CurrReferansTipi + KapsamVeSozluk |
| `scripts/utils/project_config.py` (27ae65e yaml `#`) | ALMA | — | aXet `project_config` `sap-project.json`'u `json.loads` ile okur; yaml-lite tırnak/yorum ayrıştırıcısı yok ⇒ kusur sınıfı aXet'te yok | — |
| `scripts/validators/check_cds_currency_reference.py` (f15becb · d6572b3 ④ · ac9231e) | UYARLA | `VAL/check_cds_currency_reference.py` | Sözlük dışı CUKY tipli başvuru BLOCKER→WARNING ⚠GEVŞETME; qualified başka-tablo başvurusu; `abap.cuky`; takma adsız sade alan eleman sayılır; AD_ADAYI | `-k validator_ad` CurrReferansTipi (konwa temiz rc 0 · marker eksik rc 1) |
| `check_rap_readonly_consumption.py` (ac9231e + d6572b3) | UYARLA | `VAL/check_rap_readonly_consumption.py` | AD_ADAYI/ad_coz; katman `<ad-alanı><MOD><nnn>_C_*` (`c_katmani`); çözülemeyen ad → SKIPPED `ad-cozulemedi`; bildirilmemiş namespace katman adı → SKIPPED `namespace-kayitsiz`; BDEF `*.bdef.asbdef`; referans `ad_gecis_deseni`. aXet Rule B sırası (`.rules.md` kökü → proje dizini → ÖLÇÜLEMEDİ notu) KORUNDU. ⚠SIKILAŞTIRMA: Y'li katman adı da denetlenir | `-k validator_ad` RapReadonly 4 test |
| `check_reuse_gate.py` (ac9231e) | UYARLA | `VAL/check_reuse_gate.py` | AD_ADAYI + ad_coz; envanter katı gramerle; `define view entity` var ama ad çözülemedi → SKIPPED `ad-cozulemedi` | `-k validator_ad` ReuseGate 2 test |
| `check_sap_active_version.py` (ac9231e + e52ad6f) | UYARLA | `VAL/check_sap_active_version.py` | Yerel gevşek `_MUSTERI_AD_RE` (her namespace'i müşteri sayıyordu) → `musteri_karari`; `define root abstract/custom entity`; URL `url_segmenti` | `-k validator_ad` AktifSurumVeYapi |
| `check_sap_struct_consistency.py` | UYARLA | `VAL/check_sap_struct_consistency.py` | Yapı ve ALAN adı gramerden; çözülemeyen yapı/alan → SKIPPED; URL `url_segmenti` | `-k validator_ad` AktifSurumVeYapi |
| `check_struct_field_dtel_active.py` (e52ad6f + 9c8c57a beyanı) | VAR + UYARLA (URL) | `VAL/check_struct_field_dtel_active.py` | Aday çıkarımı aXet'te zaten `ddic_dtel.dtel_adaylari` (Z/Y + her `/ns/`, SAP'de varlık sorgulanır) — kaynağın namespace-kayitsiz SKIP'i aXet'te GERİLEME olurdu (standart `/SCWM/` DTEL'i okunabiliyor), ALINMADI. `abap.*` kapsam beyanı aXet `KAPSAM_BEYANI`'nda VAR. URL `quote(.lower())` → `url_segmenti` (tek kaynak) | `-k k10` 27/27 · `-k reviewer` 150/150 |
| `check_table_field_drop.py` (8565c9d #408 + ac9231e) | UYARLA | `VAL/check_table_field_drop.py` | Tip metni TAM (`abap.char(100)`); fiziksel tip kıyası (yerleşik doğrudan, DTEL ADT meta verisinden): tür/daralma/çözülemeyen BLOCKER · genişleme WARNING (FINDING, rc 0) · aynı tip INFO ⚠GEVŞETME; eksik uzunluk/ondalık 0 sayılmaz ⚠SIKILAŞTIRMA; çözülemeyen tablo/alan adı → SKIPPED (eski "kapsam dışı measured=true"); KAPSAM satırı; `sap-client` sabit '100' yerine bağlantıdan; checklist_check/BE-16 atıfları çıkarıldı | `-k validator_ad` TabloTipKiyasi 3 test + table_field_drop SKIPPED |
| `run_review.py` (d6572b3 ⑤ · 8565c9d · 9c8c57a) | UYARLA | `VAL/run_review.py` | DCL "ÖLÇÜLMEDİ — görev tipi YOK" kapsam beyanı (metin + `--json` `bakilmayan`); drop-guard açıklaması #408; `check_ddic_builtin_fields` zincir satırları ALINMADI (aşağıda) | `-k validator_ad` KapsamVeSozluk · `-k reviewer` 150/150 |
| `check_abaplint.py` · `check_audit_fields_autofill.py` · `check_bdef_backtick.py` · `check_released_objects.py` · `check_standard_table_fields.py` (ac9231e) | UYARLA | `VAL/` aynı adlar | Yerel `\w+` ad yakalamaları → AD_ADAYI/musteri_karari; namespace'li ad artık "tanım yok" sayılmaz | `-k validator_ad` GramerGerilemeBekcisi · `-k gate_status` 26/26 |
| `check_rap_managed_etag.py` (d6572b3 ②) | UYARLA | `VAL/check_rap_managed_etag.py` | Blok düzeyi etag: kök (lock master) etag master ister; çocuk etag'i master/dependent; yoksa "ÖLÇÜLMEDİ: çocuk blok etag'i"; ad yakalaması kaldırıldı | `-k fixtures` 10/10 |
| `check_sap_master_language.py` (d6572b3 ⑦) | UYARLA | `VAL/check_sap_master_language.py` | Dosya adı → SAP adı `dosya_adindan_ad` (`#ns#x`) | `-k gate_status` 26/26 |
| `check_dtel_creation_labels.py` (e52ad6f) | UYARLA | `VAL/check_dtel_creation_labels.py` | Ad kararı ad politikasından | `-k fixtures` 10/10 |
| `scripts/validators/check_package_naming.py` (d6572b3 ①) | VAR | `scripts/check_package_naming.py` | `*.asddls`/`*.asdcls`/`*.asbdef`, `#ns#ad`→`/NS/AD`, KAPSAM satırı aXet'te zaten var (satır 9, 52, 223). Bu turda bu dosyada A1 değişikliği YOK (1 satırlık `--package` klasör eşlemesi başka kulvarın) | — |
| `scripts/validators/check_object_in_correct_pkg.py` (27ae65e · d6572b3) | VAR (kapsanıyor) | `scripts/check_package_naming.py` | aXet'te paket `.rules.md` Naming regex'i paket-özgüdür (`templates/package/.rules.md.tmpl`: `^{PKG}_C_…`, `^{P}CL_{PKG_BODY}_…`) ⇒ başka paketin önekli dosyası o regex'e uymaz = "yanlış pakette" bulgusu; namespace'li paket klasörü `#ns#…` + namespace önekli regex `new_package.py` ile üretilir (başka kulvar). Ayrı validator taşımak çift kural olurdu | — |
| `scripts/validators/check_source_drift.py` (d6572b3) | ALMA | — | Bağlantılı, dönemsel elle koşulan sapma aracı; aXet karşılığı `pull_state.py` (pull-before-edit). Lider onaylı | — |
| `scripts/validators/checklist_check.py` (57295a3 + d7f2fa0) | ALMA | — | aXet'te `checklist-map.yaml` altyapısı yok; checklist'ler skill referansı. Lider onaylı | — |
| `scripts/validators/check_ddic_builtin_fields.py` (YENİ, 9c8c57a #406) | ALMA (şimdilik) | — | Yeni gate (kaynakta ADR 0019 beş şartı + kullanıcı onayı). Sözleşmesi kardeş `<GÖVDE>.README.md` istisna dosyasına dayanıyor; aXet'te inceleme artefaktı sistem geçici dizininde üretildiği için kardeş README hiç bulunmaz ⇒ her DTEL'siz alan kalıcı WARNING olur (gürültü). aXet'te `check_struct_field_dtel_active` `KAPSAM_BEYANI` "ÖLÇÜLMEDİ: abap.* ilkel tipler" der (kapsam boşluğu görünür; listelenmez). AÇIK KALAN'a yazıldı | — |
| d8346ec textpool/msag araçları | VAR | `gate.check_names` → `guardrails` → `ad_politikasi` | `adt_textpool_write`/`adt_msgclass_write` `name` argümanı kapının ad denetiminden geçer (gate.py:104-105); `lib/utils/textpool.py` ad kararı taşımaz. `tools/textpool.py`/`msgclass.py` A2'nin | `-k ad_politikasi` KapiNamespace |
| ce8a124 lib tarafı (G1/G4/G6) | UYARLA (kısmen) | `ad_politikasi` (`yerel_ad`, `odata_servis_yolu`, `musteri_govdesi`), `sap_adt_lib._validate_object_name(referans=)` | G2/G3 (`gen_field_table`, `program_to_spec`, `check_ui_odata_refs`) başka skill'lerde — kulvar dışı; URL'den ad çözümü A2 | `-k ad_politikasi` AdresVeDosya |
| `governance/infra-test-recipes.md` (B96 · B101 · B102 · #408 reçeteleri) | UYARLA | `F/tests/test_ad_politikasi.py` · `F/tests/test_validator_ad_grameri.py` (YENİ) | Reçeteler aXet'te doküman değil test olarak: q393/validator_ad_grameri/namespace_tesisat → test_ad_politikasi; q405/cds_curr_referans_tipi/table_field_drop_tip/validator_ad_deseni → test_validator_ad_grameri (validator'lar alt süreçle, ağsız) | `-k validator_ad` 8/8 · 16 test 0 failure |
| `tests/fixtures/issue391_ns_yaml_yorum` | ALMA | — | yaml-lite yok (project_config ALMA ile aynı gerekçe) | — |

## Mutasyon (hepsi öldü; her dosya md5 ile geri yazıldı = True)

Koşucu: scratch `a1_mut.py` (dosyayı boz → hedef testi koş → geri yaz → md5 kıyasla).

| Kip | Kırılan test |
|---|---|
| M1 bildirim denetimi kaldır | 6 (Karar + KapiNamespace bildirimsiz red) |
| M2 hatalı öğede kısmi liste | 6 (FailClosed) |
| M3 `.conn_adt` yokluk denetimi kaldır | 1 (test_baglanti_dosyasi_yok) |
| M4 mükerrer anahtar denetimi kaldır | 1 |
| M5 açık kök karşılaştırması kaldır | 3 |
| M6 std_dml eski `/Z…/` kabulü | 3 |
| M7 guardrails her `/NS/` kabul | 4 |
| M9 `re.ASCII` düşür | 1 (`/NSPC/Xı`) |
| M10 `url_segmenti` kodlamasız | 1 |
| V1 `.asbdef` uzantısı düşür | test_asbdef_bdef_sayilir |
| V2 BDEF referansı eski `\b` | test_namespace_bdef_referansi_ad_siniriyla |
| V3 kayıtsız NS katmanı 'hayir' | test_katman_ihlali_ad_alani_bazinda (`/ABC/SD001_C_Y`) |
| V4 RRC çözülemeyen ad → kapsam dışı | test_cozulemeyen_entity_adi_olculemedi |
| V5 reuse çözülemeyen ad → kapsam dışı | ReuseGate.test_cozulemeyen_ad_olculemedi |
| V6 active_version kayıtsız NS nedeni | test_active_version_bildirimsiz_namespace |
| V7 struct bozuk alan denetimi kaldır | test_struct_consistency_cozulemeyen_ad_ve_alan |
| V8 genişleme ondalık şartı düşür | test_fiziksel_karsilastirma (`dec(15,3)→dec(15,2)`) |
| V9 tip metni ilk ad parçası (eski) | test_alan_haritasi_tam_tip |
| V10 eksik uzunluk 0 okunur (eski) | test_dtel_xml_eksik_oge_cozulemez |
| V11 TFD çözülemeyen tablo adı → kapsam dışı | test_table_field_drop_cozulemeyen_ad_ve_alan |
| V12 DCL beyanında dosya türü | test_run_review_dcl_beyani |
| V13 `konwa` sözlükten çıkar | test_para_birimi_sozlugu (CurrReferansTipi bu mutasyonda YEŞİL kaldı: f15becb WARNING gevşetmesi yüzünden R1 rc 0 korunuyor — sözlük üyeliğini yalnız birim test ölçer) |
| V14 reuse `ENTITY_RE` eski `(\w+)` | GramerGerilemeBekcisi |

## OTONOM KARARLAR

1. **std_dml_scan sıkılaştırması** (lider kabul etti): bildirilmemiş `/Z…/`, `/Y…/` tablo/genişletme hedefi artık standart ⇒ Yasak B (DML) ve Yasak A (genişletme, `std_ext_scan` aynı `_izinli`'yi kullanır) reddeder. `test_std_ext_gate` g/g2 serbest vakaları pozitife taşındı (kendi değişikliğimizin yan etkisi — düzeltildi).
2. **`curr` CURR sözlüğünden çıkarıldı** (kaynakta sahip onaylı gevşetme; aXet'e aynen).
3. **project_config 27ae65e ALMA** (JSON; kusur sınıfı yok).
4. **guardrails `root=` parametresi**: kapı açık kökü koruyuculara geçirir; açık kök ≠ bağlantı dizini ⇒ namespace kapalı (env ile liste genişletme yok).
5. **sap_adt_lib `_validate_object_name(referans=)`**: başvurulan (ref_structure) adda yalnız biçim; yazılan adda müşteri kararı.
6. **check_struct_field_dtel_active namespace-kayitsiz SKIP'i ALINMADI**: aXet her `/ns/` DTEL'i SAP'de sorguluyor (ölçüyor); kaynağın SKIP'i aXet'te ölçen yolu ölçmeyen yola çevirirdi.
7. **check_ddic_builtin_fields ALMA**: yeni gate + kardeş README sözleşmesi aXet artefakt düzenine uymuyor (yukarıda).
8. **check_rap_readonly_consumption Y öneki**: ad politikasına bağlanınca Y'li katman adı da denetlenir (⚠SIKILAŞTIRMA, ADR A-EK tutarlı).
9. **check_table_field_drop `sap-client`**: kaynak DTEL GET'te sabit `'100'` kullanıyordu; aXet bağlantının client'ını kullanır.

## AÇIK KALAN

- `skills-sap/sap-abapgit-delivery/scripts/*.py:153` yalnız `/Z…/`·`/Y…/` namespace'i kabul ediyor; `customer_namespaces`'e bağlı değil (ölçüldü, dokunulmadı — kulvar dışı).
- A2: `sap_adt_lib`/`sap_client` URL kurucularında ~40 `{name.lower()}` (namespace'li adda `/` kodlanmaz) → `url_segmenti`; araç açıklamalarında "Delete a Z/Y namespace SAP object" gibi metinler.
- `check_ddic_builtin_fields` (#406): aXet'e alınacaksa istisna kaydının yeri (kardeş README yerine `sap-project.json` ya da intake artefaktı) kullanıcı kararı ister.
- `tests/test_static.py::test_yasak_dizgeler` KIRMIZI: `sap-ui5-fiori/tests/test_ui5_sablon.py:46: kaynak-adi` — A1 dosyası değil, başka kulvarın yeni dosyası (lidere bildirildi).
- ce8a124 G2/G3 (`sap-fs-ts-docs` `gen_field_table`/`program_to_spec`, `sap-ui5-fiori` `check_ui_odata_refs`) namespace tesisatı — ilgili kulvarlar.
