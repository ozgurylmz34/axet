# Uyum turu 8 — A2 kulvarı karar tablosu (yeni ADT yetenekleri + istemci düzeltmeleri)

Kaynak: DEV_CORE `dd9ba0f..c457161` — b0bcfac · 2cc3454 · f646f36 · d85de77 · 9b38ab6 · 0ec670c · d5da3c1 · 1228623 · 2fd6e11 ·
d7f2fa0 · c457161 (query.py) · 6811b83 / d6572b3 (pull kısmı) · 8565c9d (#408 docstring) · tarih 2026-11-17.
Kulvar: `sapadt/tools/*` · `lib/sap_adt_lib.py` · `lib/sap_client.py` · `pull_state.py` · `_app.py` · `_reviewer.py` ·
`lib/utils/abap_metot_blok.py` · `lib/utils/cds_metin.py` · `scripts/sap_adt_cli.py` · `references/tool-catalog.md` · `IMPLEMENTATION.md`;
ortak (yalnız Edit/eşsiz parça): `lib/object_types.py` · `gate.py`. Yol kısaltması: `F` = `skills-sap/sap-adt-foundation`.
Testler `F/tests` içinde, her biri ayrı komut (`python -m unittest discover -s tests -p <dosya>` ya da `cd tests && python -m unittest <modül>`).
Hiçbir test SAP'ye bağlanmadı (sahte istemci / 127.0.0.1 sahte HTTP sunucusu).

## Karar tablosu

| Kaynak commit / dosya | Karar | aXet hedef | Ne aktarıldı / gerekçe | Test → sonuç |
|---|---|---|---|---|
| b0bcfac `scripts/object_types.py` (FUGR/I) | UYARLA (eşsiz parça + Edit) | `F/scripts/sapadt/lib/object_types.py` | `FUGR_INCLUDE_TYPES` · `get_fugr_include_url` (yol `url_segmenti`) · `include_fugr_baglami` · `fugr_include_grup_kaniti(xml, grup, root=)` (tam bir FUGR bağlamı + `contextRefCount=1`; Z: `FUGR/I SAPL<G>`; bildirilmiş NS: `/NS/SAPLFG` ya da `FUGR/F`=grup) · `fugr_include_ad_alani_hatasi` (grup müşteri adı + include öneki `fugr_include_oneki`). Kaynak yorumundaki iç ad nötrleştirildi | `test_fugr_include_yazim` 18/18 |
| b0bcfac `scripts/sap_client.py` | UYARLA (eşsiz parça) | `F/scripts/sapadt/lib/sap_client.py` | `fugr_include_grubunu_dogrula` · `push_fugr_include` (kanıt → ETag → LOCK → PUT → UNLOCK → ACT → READ) · `activate_object(..., group=)` (kanıtsız aktivasyon yok) | aynı (C1–C4) |
| b0bcfac `scripts/sap_adt_lib.py` (kilit özeti) | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` | Kilit hatası SAP gövdesinin sebebini taşır (`sap_hata_sebebi`, kilit özeti); `activate_object(..., object_type=)` | `test_kilit_bildirimi` 13/13 · `test_lib_regressions` 13/13 |
| b0bcfac `mcp_servers/.../tools/atom.py` · `query.py` | UYARLA | `F/scripts/sapadt/tools/atom.py` · `query.py` | `adt_get` / `adt_push_source` / `adt_activate` / `adt_lock_check` `group` argümanı; `group_required` · `group_not_applicable` · `fugr_group_unverified` · `fugr_group_mismatch` · `fugr_include_also_unsupported` (hepsi ağdan önce ya da kanıt adımında, yazmadan önce) | aynı (T1–T8) |
| b0bcfac `mcp_servers/.../_reviewer.py` | UYARLA (aXet farkı) | `F/scripts/sapadt/_reviewer.py` | FUGR/I → `program_push` (kaynak `None`) — OTONOM KARAR ② | `test_verdict_reviewer_k1_d1` 41/41 |
| b0bcfac kapı | UYARLA (Edit, ortak) | `F/scripts/sapadt/gate.py` | `check_names(..., grup=)` FUGR/I dalı (`tool_args["group"]`); `_fugr_include_tipi_mi` | G1–G2 · `test_cli_gate` test_05 (FUGR/I standart grup CLI'da `ADR_0005_A`) |
| b0bcfac `pull_state` | UYARLA | `F/scripts/sapadt/pull_state.py` | `tip_anahtari` tüm FUGR/I eşanlamlılarını `fugr_include`'a indirger | T3 (`fugr_include:LZAXFGF01`) |
| b0bcfac `scripts/push_object.py` · `tests/fixtures/fugr_include_yazim/*` | ALMA (dosya) / UYARLA (test) | `F/tests/test_fugr_include_yazim.py` (YENİ) | Kaynak CLI aXet'te yok (araç katmanı); fikstür vektörleri aXet testine çevrildi | 18/18 |
| 2cc3454 (fikstür mutasyon çapası) | ALMA | — | Kaynak fikstürünün kendi `--mutasyon-csrf` çapası; aXet mutasyonları kendi koşucusunda (aşağıda) | — |
| f646f36 playbook (FM güncelleme modülü metadata PUT · FM readback 2 boş satır · ENHO'lu exit include) | VAR (başka kulvar, belge) | `skills-sap/sap-classic-abap/references/fugr-fm.md` §0/§2.2/§2.3/§3 · `F/references/foundation-ops.md` (exit include) | Çalışma ağacında başka kulvar tarafından işlenmiş (ölçüldü: `fugr-fm.md:24,108,112-124,129`). aXet'te araç YOK (kullanıcı SE37; ham REST ile yazma yasak) — A2 ek yapmadı | — |
| d85de77 `scripts/sap_adt_lib.py` (ENHS lib) | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` | `get/create/write/activate_enhancement_spot` + `enhs_*` (ayrıştır/kur/spec/kıyas/ad denetimi `musteri_karari`, kabuk gövdesi, worklist hedefi, sıra tuzağı reddi) | `test_badi_spot` S1–S4 · W1–W3 |
| d85de77 `scripts/populate_badi_spot.py` | UYARLA (araç olarak) | `F/scripts/sapadt/tools/badi.py` (YENİ) | Kaynak CLI → iki araç: `adt_badi_spot_read` (okuma) · `adt_badi_spot_write` (yazma, transport, `s4_private`). Lider onayı ③. Kapsam `definitions` + `remove_badis` — OTONOM KARAR ⑤ | R1–R2 · Y1–Y8 · `test_cli_gate` test_01/05 |
| d85de77 `tests/fixtures/enhs_badi_spot/canli/*` | AL | `F/tests/fixtures/enhs_badi_spot/readback_aktif.xml` · `put_kabul.xml` | Ölçülmüş canlı belgeler (örnek adlar, yer tutucu kimlik); S2 bayt-eşit kıyası | S2 |
| d85de77 / 9b38ab6 `playbook/adt-enhancement-spot-badi.md` | UYARLA | `F/references/enhancement-spot-badi.md` (YENİ) — OTONOM KARAR ⑦ (hedef seçimi kulvara bırakıldı) | Kaynak CLI kullanımı → aXet araç akışı; ölçüm etiketleri ([758]/[816]) korundu; iç ad/iz yok; `SKILL.md` referans tablosuna satır | `test_static` 3/3 · `test_sap_skill_bilgi` 24/24 |
| 9b38ab6 `scripts/object_types.py` (ENHS işlem-izinli girdi) | UYARLA (eşsiz parça) | `F/scripts/sapadt/lib/object_types.py` | `enhancementspot` (eşanlamlı `enhs`, `enhsxsb`, `enhs/xsb`) · `generic_islemler` = silme · kilit · metadata · `islem_reddi` · `get_object_url(..., islem=)` fail-closed | A1 (`get_object_url(enhs)` ValueError · silme URL'i) |
| 9b38ab6 `sap_client.py` · `tools/query.py` · `run_atc_check.py` | UYARLA | `F/scripts/sapadt/lib/sap_client.py` (`islem='silme'/'metadata'/'atc'`) · `tools/query.py` (`adt_atc_check` → `atc_kapsam_disi`, istek yok; kilit sondası `islem="kilit"`) | ATC ENHS'te "0 bulgu" yokluktan ayırt edilemiyor (kaynak ölçümü) | A1 |
| 9b38ab6 `tests/fixtures/enhs_tip_yuzeyi` | UYARLA | `F/tests/test_badi_spot.py` A1 | — | A1 |
| 0ec670c `sap_adt_lib.py` CSRF (#411) | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` `_csrf_reddi_mi` (4 çağıran) | 403 + (gövdede CSRF ya da `x-csrf-token: Required`); 403 dışı CSRF metni tekrar ETMEZ (davranış değişikliği, kaynakla aynı) | `test_csrf_custom_entity` 6/6 |
| 0ec670c `sap_adt_lib.py` custom entity (#410) · `scripts/utils/cds_metin.py` | UYARLA · AL | `_validate_cds_source` · `F/scripts/sapadt/lib/utils/cds_metin.py` (YENİ) | `define [root] custom entity` kabul (⚠GEVŞETME, kaynakta kullanıcı onaylı); yorum/string ayıklayıcı tek kaynak; tool-catalog satırı (lider kararı ④) | aynı (C) |
| 0ec670c fikstürler (`csrf_tanima_ortak`, `cds_kaynak_kapisi`) | UYARLA | `F/tests/test_csrf_custom_entity.py` (YENİ) | S/N/Q/W/C vektörleri | 6/6 |
| d5da3c1 (ENDMETHOD'dan sonra kod) | VAR | `F/scripts/sapadt/lib/utils/abap_metot_blok.py:24,105` (`bitis_sonrasi_kod`) · `references/tool-catalog.md` `adt_get_method` | aXet'te `belirsiz` + `end_line:null` (kaynakta `sinir_belirsiz`); katalogda yazılı (B2 notu ① kontrol edildi) | `test_abap_metot_blok` G35 · W10 (mevcut) |
| 1228623 `sap_adt_lib.find_ghost_transports` · `sap_client` 409 dalı | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` · `sap_client.py` | Okunamayan liste `SAPADTError`; `[]` yalnız geçerli boş yanıtta; değer `<dp:data>` metninden; push 409 dalı "okunamadı — SE10'da elle bakın", push sonucu değişmez | `test_kucuk_duzeltmeler_tur8` H |
| 1228623 `scripts/list_revisions.py` (tablo ucu) | VAR | `F/scripts/sapadt/tools/diag.py` `adt_revisions` → `object_types` | aXet zaten `object_types` üzerinden `/ddic/tables` (ölçüldü: `get_object_url(..,'tabl')`) | H revizyon tablo ucu |
| 2fd6e11 `sap_adt_lib.py` oturum kapatma | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` `_oturumu_kapat` · `_sonlandirici_kapat` · `new_session` | ICF logoff → 404'te bağlam düşürme; SAML'de logoff yok; çerezsiz oturumda ağ yok; hata yutulur, çerez değeri basılmaz | O (127.0.0.1 sahte sunucu) |
| 2fd6e11 `sap_client.run_sql_query` · `scripts/run_sql_query.py` (ms) | UYARLA | `sap_client.py` `execution_time_ms` · `tools/query.py` `adt_sql_query` yanıtına `execution_time_ms` | Kaynak CLI çıktısının karşılığı araç alanı (birim adda) | Q |
| d7f2fa0 `sap_adt_lib.set_object_source` | UYARLA | `F/scripts/sapadt/lib/sap_adt_lib.py` | Sonraki biçime yalnız biçim reddinde (409/412/Parameter); içerik reddinde DURDU; son biçimde Parameter reddi sahte `True` değil; hata `denemeler` taşır | B (4 test) |
| d7f2fa0 `sap_client._hata_ayrintisi_ekle` · `scripts/push_object.py` ipuçları | UYARLA · ALMA | `sap_client.py` (`put_denemeleri` · `error_response_text` · `error_t100`, `sapadt.redact` ile) | Ayrıntı araç yanıtına temizlenmiş girer (`result`); kaynak CLI'nin "ÖNCE O YANITA BAK" / "başka geliştirici" basımı CLI'ye özgü (aXet'te araç yanıtında liste var) | B hata ayrıntısı |
| d7f2fa0 checklist / RAP V2 maddeleri | — (kulvar dışı) | — | `checklist_check.py` A1 ALMA; RAP V2 belgeleri B kulvarı | — |
| c457161 `tools/query.py` (BDEF where-used #434) | UYARLA (tamamlama turu) | `F/scripts/sapadt/tools/query.py` | `_WHERE_USED_DAR_UC = {"bdef": "bo/behaviordefinitions"}` · `_where_used_dar_url` (yol `url_segmenti`) · `_dar_url_var_mi` (yalnız 404 = yok; 500 yükselir). Eşleme yalnız bu araçta (genel `OBJECT_TYPES`'a BDEF eklenmedi — kaynakla aynı gerekçe); yanıt BDEF'in kendisini de sayar (süzülmez). Katalog satırı eklendi | `test_tur8_tamamlama` W1–W5 |
| 6811b83 | ALMA (lider onaylı) | — | Kaynak oturum/worktree damgası; aXet'te karşılık mekanizma yok | — |
| d6572b3 pull kısmı (`#ns#` dosya adı → pull_state) | VAR / ALMA (lider onaylı) | `F/scripts/sapadt/pull_state.py` | aXet pull kaydı DOSYA adıyla değil SAP ADI + tip anahtarıyla tutulur (`anahtar(ad, tip)`) ⇒ `#ns#` dosya adı dönüşümüne gerek yok; dosya adı ↔ ad çevirisi A1 (`dosya_adindan_ad`) | `test_pull_before_edit` 22/22 |
| 8565c9d #408 docstring | UYARLA (tamamlama turu, metin) | `F/scripts/sapadt/_reviewer.py` · `tools/atom.py` (`adt_push_source.ack_drop`) · `F/IMPLEMENTATION.md:94` | "TYPE/RENAME change still BLOCKER" → ack_drop'un tip hükmüne etkisi yok (daralma/tür/çözülemeyen tip BLOCKER, genişleme WARNING, aynı fiziksel tip INFO). Validator'daki #408 davranışı başka kulvarda zaten aktarılmış (`lib/validators/check_table_field_drop.py:18-35`); aXet kapısı `ack_drop`'u zaten reddeder (`reviewer_bypass_forbidden`) | metin — test yok |
| ce8a124/e52ad6f `scripts/check_package.py` | VAR | — | Paket URL'i `object_types.get_object_url` → `quote(ad.lower(), safe='')` (= `url_segmenti`) | — |
| ce8a124 `scripts/create_lock_object.py` | VAR / ALMA | — | Kilit nesnesi ad kuralı kapıda (`ad_politikasi.musteri_adi_mi`: E+Z/Y ya da bildirilmiş /NS/…); kaynağın değişikliği yalnız 'E ile başlar' UYARISI — aXet'te o uyarı yok, kapı Z/Y'de E'yi zorunlu tutar | — |
| e52ad6f/ce8a124 `scripts/create_rap_service.py` | UYARLA | `F/scripts/sapadt/lib/rap_service.py` · `tools/atom.py` (`adt_publish_service`) | Yol parçaları `url_segmenti` (önceki adımda) + G3 `odata_servis_yolu` → yanıtta `metadata_path` (/NS/X → `/sap/opu/odata/ns/X/$metadata`; namespace'li yol canlı ÖLÇÜLMEDİ); publish ÖLÇÜLEMEDİ notu `metadata_path`'e yönlendirir | `test_tur8_tamamlama` P1–P2 |
| ce8a124 `scripts/download_ddic_objects.py` · `download_object.py` (G1 `yerel_ad`) | UYARLA (lib) | `F/scripts/sapadt/lib/sap_client.py` | Araçlar dosyayı modelin `output_path`'ine yazar (ad türetmez, VAR); ama `SAPClient.download_object` / `push_object` / `delete_object` adı dosya adına çeviriyordu — `/NS/X` sürücü köküne kaçar, `delete_object` oradaki aynı adlı dosyayı `unlink` ederdi ⇒ üç yer `yerel_ad` (`#ns#x`) | `test_tur8_tamamlama` Y1–Y4 |
| d6572b3/6811b83 `scripts/hooks/pull_before_edit.py` | ALMA | — | Namespace'li adın kabuk komutunda tırnaklanması: aXet'te hook yok; önerilen adım kabuk komutu değil araç çağrısı (JSON argüman) ⇒ `/` yol dönüşümü / `#` yorum tuzağı yok. 6811b83 lider kararıyla ALMA | — |
| ce8a124 `scripts/sap_set_object_description.py` | UYARLA (metin) | `F/scripts/sapadt/tools/description.py` | Ad kararı kapıda (A1, namespace dahil); URL `quote(ad.lower(), safe='')` (VAR); kilit bırakılamadı uyarısı aXet'te adsız SM12 metni (VAR); docstring 'Z/Y' → 'Z/Y ya da projede bildirilmiş /<NS>/' | `test_set_description` 24/24 (regresyon) |
| d6572b3 `scripts/sap_sync_pull.py` · `scripts/source_drift.py` | ALMA | — | Dosya adı ↔ SAP adı (`dosya_adindan_ad`), tırnaklı tekrar komutu, repo dosyası arama: aXet'te ad JSON argümanı, dosyadan ad çözülmez, pull kaydı SAP adı + tip anahtarlı (d6572b3 kararı, lider onaylı); `source_drift` ek store damgası 6811b83 (ALMA) | — |
| ce8a124 `scripts/syntax_check.py` | VAR | `F/scripts/sapadt/lib/sap_adt_lib.py` | DDIC sözdizimi yolu `/sap/bc/adt/ddic/{endpoint}/{_adt_seg(name)}` (bu turun URL kodlaması) | U (önceki adım) |
| Lider kararı — URL kodlama (~40 kodsuz yol parçası) | UYGULANDI | `sap_adt_lib.py` 34 + tablo `packageRef` 1 · `sap_client.py` 11 · `tools/composite.py` 2 · `lib/rap_service.py` 1 | `{ad.lower()}` → `_adt_seg(ad)` (= A1 `url_segmenti`); `sap_adt_lib.py:685` ad doğrulamasına dokunulmadı; bilinçli kalan 2 satır kaynak metni (`define table`, `type-pool`); araçlardaki `quote(ad.lower(), safe="")` bayt-eşit, dokunulmadı. `rap_service.py` ve `composite.py` brifte sayılmıyordu — aynı kusur sınıfı, bu işi etkiliyor ⇒ düzeltildi + raporlandı | U (`/NSX/`→`%2Fnsx%2F…`, Z aynen) · U kablolama |
| `sap-dev/references/role-briefs.md` S2 listeleri (lider talebi) | UYARLA (Edit, iki satır) | `skills-sap/sap-dev/references/role-briefs.md:42-43,52-53` | OKUMA'ya `adt_badi_spot_read`, YAZMA'ya `adt_badi_spot_write` | kök `test_sap_skill_bilgi` 24/24 |

## Mutasyon (hepsi öldü; her dosya kopyadan geri yazıldı, md5 eşit = True)

Koşucu: scratch `mutasyon.py` (dosyayı kopyala + md5 → boz → hedef test dosyasını koş → kopyadan geri yaz → md5 kıyasla); "öldü" = beklenen
test(ler) FAIL/ERROR listesinde.

| Kip | Bozulan yer | Kırılan test |
|---|---|---|
| M1 | `gate.check_names` FUGR/I dalı `elif False` | test_G1_check_names_fugr_include |
| M2 | kapı grup denetimi devre dışı | test_G1_check_names_fugr_include |
| M3 | `adt_activate` grup kanıtı atlanır | test_T6_aktivasyon_kapilari |
| M4 | `also` + FUGR/I reddi yok | test_T6_aktivasyon_kapilari |
| M5 | push grup guardrail'i kaldırıldı | test_T1 · test_T2 |
| M6 | push'ta FUGR/I transport zorunlu değil | test_T4_push_transport_zorunlu |
| M7 | `adt_lock_check` kanıt atlanır | test_T8_lock_check |
| M8 | `pull_state` FUGR/I kanonik anahtar yok | test_T3_get_push_akisi |
| M9 | kanıtta `contextRefCount` denetimi yok | test_L2_grup_kaniti |
| M10 | `push_fugr_include` kanıt atlanır | test_C1_kanit_tutmazsa_yazma_yok |
| M11 | namespace grubunda `FUGR/F` kabulü yok | test_L4_namespace |
| E1 | kapı `arg_adlari` BAdI dalı yok | test_G2_standart_adlar_kapida_red |
| E2 | `adt_badi_spot_write` READ_TOOLS'ta | test_G1_sinif_ve_transport |
| E3 | pull kaydı aranmaz | test_Y1_kayit_yok_red |
| E4 | canlı özet kıyası yok | test_Y2_canli_degisti_red |
| E5 | araç ad denetimi yok | test_Y3_standart_badi_adi_agsiz_red |
| E6 | `masterSystem=SAP` reddi yok | test_Y4_standart_spot_canlida_red |
| E7 | readback farkı `ok`'u düşürmez | test_Y6_readback_farki |
| E8 | lib kilit altı taban kıyası yok | test_W2_kilit_alti_taban_degisti |
| E9 | `adt_atc_check` ENHS reddi yok | test_A1_atc_kapsam_disi |
| K1 | CSRF yükleminde 403 şartı yok | test_S_tanir_N_tanimaz |
| K2 | CSRF başlık dalı yok | test_S_tanir_N_tanimaz |
| K3 | `_should_retry` eski İngilizce yüklem | test_S_should_retry_ayni_yuklem · test_W1_dort_cagri |
| K4 | `_request_with_csrf_retry` CSRF tanımaz | test_Q_taze_token_ve_yetki (+ W1) |
| K5 | custom entity başlığı yok | test_C_kabul_ve_red |
| K6 | custom entity gövde kuralı yok | test_C_kabul_ve_red |
| D1 | hayalet: 200-dışı → `[]` | test_H_okunamayan_hata_bos_yalniz_gecerli |
| D2 | hayalet: değer `value` özniteliğinden | test_H_okunamayan_hata_bos_yalniz_gecerli |
| D3 | biçim: her ret sonraki biçime | test_B_icerik_reddinde_durur |
| D4 | son biçim Parameter → `True` | test_B_son_bicim_parameter_sahte_basari_degil |
| D5 | oturum: SAML'de de logoff | test_O_dallar |
| D6 | oturum: 404 geri düşüş yok | test_O_dallar |
| D7 | araç `execution_time_ms` taşımaz | test_Q_istemci_ve_arac_ms |
| U1–U2 | yol parçası kodlaması geri alınır (bkz. aşağı) | test_U_ns_kodlu_z_aynen · test_U_kablolama_kodsuz_url_kalmadi |
| T1 | `_WHERE_USED_DAR_UC = {}` | W1 · W2 (+W3) |
| T2 | bdef yol parçası `name.lower()` | W2 |
| T3 | `_dar_url_var_mi` her hatada `False` (500 = yok) | W4 |
| T4 | bdef varlık sorulmaz (`varlik = True`) | W3 (+W1, W4) |
| T5 | where-used URL'i dar uçtan alınmaz | W1 (+W2) |
| Y1 | `download_object` eski ad | Y1 · Y4 (+Y3) |
| Y2 | `delete_object` eski ad | Y3 · Y4 |
| Y3 | `push_object` eski ad | Y4 |
| P1 | `metadata_path` sabit `/sap/opu/odata/sap/` | P2 |

Tamamlama turu (T/Y/P): 9/9 öldü, md5 geri = True (scratch `kipler5.json`). Y kiplerinde bozulma `object_name.replace('/', '')` —
sürücü köküne yazma/silme denenmesin diye; Y3 testi `Path.unlink`'i geçici kök dışında no-op yapar.

## OTONOM KARARLAR (lider onayı olmadan kulvar içinde verilen; gerekçeli)

1. **FUGR/I push'ta transport zorunlu** — sınıf include'u ve BDEF yazımıyla aynı (atom `sinif_include or bdef_mi or fugr_inc`); kaynak
   CLI transport'u isteğe bağlı bırakıyordu. Gerekçe: include yazımı bağlam programı üzerinden kayda girer; transportsuz yazım SAP'nin
   kendi seçimine kalır.
2. **Reviewer FUGR/I → `program_push`** — kaynak `None` (SKIP). aXet'te include → `program_push` (2026-09-14 kararı) ile tutarlı;
   abaplint include'u ölçemezse SKIP = WARNING + ÖLÇÜLEMEDİ, engellemez.
3. **`adt_get` FUGR/I okuması grup kanıtı değildir** — kanıt yalnız `programs/includes` `contextRef`'ten; okuma URL'deki grubu aynalar.
4. **BAdI ilk yaratımda pull kaydı aranmaz** — spot yokken ezilecek içerik yok; var olan spot'ta kayıt zorunlu.
5. **BAdI aracı yalnız `definitions` + `remove_badis`** — kaynak CLI'nin ince kaldırma bayrakları (fallback/örnek sınıf/filtre) canlıda
   ÖLÇÜLMEMİŞ yollar; alınmadı.
6. **BAdI araçları yalnız `s4_private`** — kaynak ölçümü yalnız bu profilde.
7. **ENHS belge hedefi `references/enhancement-spot-badi.md`** — foundation referansı (araçlar foundation'da); sap-classic-abap'a değil.
8. **URL kodlamasına `tools/composite.py` (2) + `lib/rap_service.py` (1) + tablo `packageRef` (1) dahil edildi** — brifteki sayımın dışında
   ama aynı kusur sınıfı (kaynak çekirdek e52ad6f composite'i de değiştirmiş).
9. **`adt_sql_query` yanıtına `execution_time_ms`** — kaynak CLI'nin basımının araç karşılığı (ek alan; mevcut alanlar değişmedi).
10. **`adt_publish_service` yanıtına `metadata_path`** (tamamlama turu) — kaynağın G3 `odata_servis_yolu`'nun araç karşılığı: kaynak
    e2e/verify adımı servis yolunu kendisi kurar; aXet'te doğrulamayı çağıran yapar, yolu yanıt verir (ek alan, mevcut alanlar aynı).
11. **`SAPClient.push_object` / `delete_object` yerel ad da `yerel_ad`'dan** — kaynakla aynı üç yer; aXet araçları `push_object`'e daima
    `source_file` verdiği için push dalı araç yolundan erişilmez, `delete_object` ise `adt_delete`'ten erişilir (sürücü kökü `unlink` riski).

## AÇIK KALAN

1. ~~c457161 BDEF where-used (#434)~~ — tamamlama turunda UYARLANDI (karar tablosu; W1–W5, T1–T5). BDEF ucu aXet'ten canlı ÖLÇÜLMEDİ.
2. ~~8565c9d #408 docstring~~ — tamamlama turunda UYARLANDI (metin).
3. **Canlı doğrulama** — FUGR/I yazma, BAdI okuma/yazma, oturum kapatma ve namespace'li URL'ler aXet'ten canlı SAP'de **ÖLÇÜLMEDİ**.
4. ~~`test_cli_gate` tamamı koşulmadı~~ — tamamlama turunda son hâlle koşuldu: `run_tests.py -k cli_gate` → 146/146 senaryo, 17 test,
   0 failure (test_01 okuma 29→30 + `adt_badi_spot_write`; test_05 yeni yazma aracı ve standart BAdI/FUGR/I vakaları).
5. `test_ddic_textpool` sahte ADT'sine `_csrf_reddi_mi` bağlandı (#411 sonrası `_should_retry` ortak yüklemi çağırıyor; sahte nesnede
   yoktu → S9/S9b/S9d düşüyordu). Davranış değişikliği değil, test düzeneği uyumu.

## KAPSAM BEYANI

Bakılanlar: yukarıdaki commit'lerin `scripts/` · `mcp_servers/sap_adt/` · `tests/fixtures/` · ilgili `playbook/` parçaları (A2 kalemleri).
Bakılmayanlar: namespace çekirdeği (A1), validator'lar (A1), belge/skill kulvarları (B1/B2/D), `governance/` kayıtları, CI dosyaları.
Testler hedefli koşuldu (tam takım koşulmadı — CI'a bırakıldı).
