# aXet Agentic Connectors — araştırma notu

> **Tarih:** 2026-09-13 · **aXet.code:** 1.3.0 (Windows)
> **Yöntem:** `axet-code --help` ve alt komut yardımları; binary'nin yazdırılabilir metin taraması (yalnız `connector`,
> `agentic`, `mcp` geçen metinler; adres, token ve benzeri değerler nota alınmadı); şirket içi kurulum/bağlantı
> dokümanlarının taranması; mevcut ölçüm tablosu (`docs/axet-davranis-olcumleri.md`).
> **Sınır:** aXet oturumu açılmadı, Connectors ekranı görülmedi, hiçbir connector senkronlanmadı. Aşağıda "ÖLÇÜLDÜ"
> yazmayan her davranış binary metninden ya da semboller üzerinden yapılan **çıkarımdır** ve DOĞRULANMADI sayılır.

## 1. Kısa cevap
- **Nedir:** aXet'in yerel MCP yerine koyduğu, merkezi "aXet Agentic" platformunda yönetilen araç/uzantı katmanı.
  Yapılandırma web arayüzünde yapılır, CLI "Sync" ile çeker; senkronlanan connector'lar oturumda MCP sunucusu gibi
  bağlanıyor ve araçlarına bir katalog + `call_mcp_tool` üzerinden erişiliyor görünüyor.
- **SAP CLI'mizin yerine geçer mi:** bugün **hayır**. Hazır bir SAP connector'ı görülmedi; merkezi bir connector'ın müşteri
  SAP sistemlerine ağ erişimi, kimlik saklama ve kesin yasak kapıları çözülmüş değil.
- **Karar önerisi:** **BEKLE** (+ §6'daki tek oturumluk ölçüm). Gerekçe §6.

## 2. Kanıtlar
| # | İddia | Kanıt | Durum |
|---|---|---|---|
| K1 | Yerel MCP yapılandırması yok sayılır, kullanıcı Agentic'e yönlendirilir | log: `Local MCP configuration is ignored. Configure connectors in Agentic.` · binary log anahtarı `connector.sync.local_mcp_ignored` | ÖLÇÜLDÜ (log) |
| K2 | Connector, aXet'in MCP yerine koyduğu ve ajanın dış sistemlere ulaştığı katman; "aXet Agentic" platformunun parçası | aXet'in yerleşik sistem prompt'undaki ürün tanımı metni ("Connectors … substitute for MCP; they are how the agent reaches external systems") | METİN |
| K3 | Kimlik bilgisi isteyen connector web arayüzünde yapılandırılır, sonra CLI'de Sync'e basılır | hata metni kalıbı: "connector … requires credentials — configure it in … connectors (<adres>), then press Sync." · "configure it from the Agentic web UI" | METİN |
| K4 | Connector'lar kullanıcının aXet girişine (Okta SSO) bağlıdır; token CLI tarafından alınır/yenilenir | metinler: "sign in to Agentic first, then try again", `connector.sync.skipped_not_authenticated`, `connector: get token`, `connector.auth.refresh_failed`, `connector: session expired` · `axet-code login --help`: "Okta device code authentication", `AXET_*` ortam değişkenleri | METİN + `--help` |
| K5 | TUI'de bir Connectors diyaloğu var: kurulu / kullanılabilir listeleri, Sync, Activate, devre dışı bırakma, filtre | Go sembolleri `ui/dialog.ConnectorsDialog` (`switchTab`, `installedRows`, `availableRows`, `activateSelected`, `toggleDisabledSelected`), `ui/model.(*UI).runConnectorSync / runConnectorActivate / runConnectorToggleDisabled` · metinler "filter connectors", "No connectors synced." | METİN; açma tuşu/komutu DOĞRULANMADI |
| K6 | CLI sunucudan "kurulu" ve "kullanılabilir" entegrasyon listelerini çeker ve kullanılabilir bir entegrasyonu aktive edebilir (sunucuda entegrasyon yaratma isteği) | semboller `connector.(*Client).ListIntegrations / ListAvailableIntegrations / CreateIntegration`, `(*Service).Activate / suggestActivateName`, `AxetAvailableIntegration.RequiresCredentials` · log anahtarları `connector.activate.start/complete/failed` | METİN; kimin hangi listeyi görebildiği (yetki modeli) DOĞRULANMADI |
| K7 | Devre dışı bırakılan connector'lar yerelde bir durum dosyasında tutulur ve MCP başlatılırken atlanır | metinler `_connector_state.json`, `connector.state: read/write`, "Skipping disabled MCP" | METİN; dosyanın yeri DOĞRULANMADI (`axet-code dirs data` ile bakılabilir) |
| K8 | Senkronlanan connector MCP sunucu tanımına dönüştürülür (sunucu adresi çözümlenir) ve MCP istemcisi olarak bağlanır | semboller `connector.Transform`, `TransformAllWithDisabled`, `mcpNameFor`, `resolveServerURL` · metinler "Initializing MCP clients", "preparing mcp sandbox" · merkezi bir MCP araç API uç noktası adresi (nota alınmadı) | METİN; uzak (HTTP) sunucu olduğu çıkarım, DOĞRULANMADI |
| K9 | Model connector araçlarını tek tek değil, bir katalog aracıyla arayıp `call_mcp_tool` ile çalıştırır | araç açıklaması: "connected MCP servers expose more tools than can be attached … discoverable through this tool and executable through `call_mcp_tool`" · araç adları dizisinde `call_mcp_tool` · `agentic_fetch` açıklaması: MCP araç adları `mcp_` ile başlar | METİN; katalog aracının adı binary'de bulunamadı. Ölçülen araç listesinde `call_mcp_tool` yok → connector senkronlanmamış oturumda görünmüyor olabilir (çıkarım) |
| K10 | CLI'de connector yöneten alt komut yok | `axet-code --help` alt komutları: `agent, completion, dirs, help, login, logout, logs, models, projects, run, stats` | ÖLÇÜLDÜ (`--help`) |
| K11 | Hazır connector kataloğunun içeriği (hangi sistemler; SAP var mı) bilinmiyor | binary'de görülen `connector_gmail`, `connector_googledrive`, `connector_sharepoint`, `connector_outlookemail` gibi adlar gömülü bir LLM SDK'sının sabitleridir; aXet kataloğunun kanıtı DEĞİLDİR | DOĞRULANMADI |
| K12 | Şirket dokümanlarında Agentic Connectors anlatımı yok | taranan: aXet kurulum/SAP bağlantı rehberi (docx), bulut bağlantı rehberi (md), eklenti README'si (md), iki araç arşivi (zip içerik listesi + metin araması); desen `connector`, `agentic`, `mcp` → connector'ı anlatan bölüm 0. README'lerdeki MCP içeriği başka bir kod asistanının yerel MCP eklentileri içindir | ÖLÇÜLDÜ (tarama; kapsam: bu 5 dosya) |
| K13 | Yerleşik sistem prompt'u "hooks" ve "slash commands"ı standart özellik olarak sayar | ürün tanımı metni | METİN — hook için ölçüm sonucu **yok**tur (`docs/axet-davranis-olcumleri.md`); ürün metni kanıt değildir |

## 3. Nasıl yapılandırılır (kanıttan çıkan akış — DOĞRULANMADI)
1. `axet-code login` ile giriş (Okta). Giriş yoksa senkron atlanır (K4).
2. aXet Agentic web arayüzünde Connectors sayfası: entegrasyonu seç, kimlik bilgisi gerekiyorsa orada gir (K3).
3. aXet TUI → Connectors diyaloğu → **Sync**; ya da "kullanılabilir" listesinden **Activate** (K5, K6).
4. İstenmeyen connector diyalogdan devre dışı bırakılır; bu yerel durum dosyasına yazılır (K7).
5. Yeni oturumda model araçları katalog aracı + `call_mcp_tool` üzerinden görür (K9).

**Kim açar:** kimlik bilgisi isteyen connector'u kullanıcı web arayüzünde yapılandırır; "kullanılabilir" listesinin
içeriği sunucu tarafında belirlenir (yönetici ya da platform ekibi — çıkarım). Kullanıcı/yönetici yetki ayrımı DOĞRULANMADI.

## 4. SAP CLI'mizin yerine geçer mi?
| Kriter | SAP CLI (`skills-sap/sap-adt-foundation`) | Agentic connector |
|---|---|---|
| Nerede çalışır | geliştirici makinesi | merkezi platform (çıkarım, K8) |
| SAP'ye ağ erişimi | geliştiricinin ağından doğrudan | merkezi sunucunun müşteri SAP sistemlerine erişimi gerekir — DOĞRULANMADI, genelde müşteri ağına kapalıdır |
| Kimlik bilgisi | kullanıcının yerel, git'e kapalı bağlantı dosyası | web arayüzünde saklanır (K3) → müşteri sistem şifresi üçüncü bir platformda |
| Kesin yasak kapıları (A/B/C/D, yazma kapısı, pull-before-edit, hassas veri) | kodda, çevrimdışı test edilmiş | connector tarafında bizim kontrolümüz yok; model `call_mcp_tool` ile bir yazma aracını doğrudan çağırabilir |
| Profil bazlı araç kapısı | var (`sap-project.json`) | bilinmiyor |
| İzin kuralı ile engelleme | `bash` deny kuralları ölçüldü | `permissions.rules`'ın connector araçlarını kapsayıp kapsamadığı DOĞRULANMADI |
| Hazır SAP entegrasyonu | var | görülmedi (K11) |

**Sonuç:** yerine geçmez. SAP CLI kalır. Connector'lar SAP dışı kurumsal sistemler (iş takibi, wiki, doküman deposu)
için adaydır; bunlar da §6 ölçümünden sonra değerlendirilir.

## 5. Riskler
1. **Kimlik merkezileşmesi:** müşteri sistemlerinin kimlik bilgisi merkezi platformda saklanır; sözleşme ve KVKK sorusu.
2. **Kural uygulayamama:** kesin yasaklar ve yazma kapısı connector araçlarında yok; aXet'te hook olmadığı için
   (ölçüldü) `call_mcp_tool` çağrısını mekanik denetleyen katman da yok.
3. **Sessiz araç yüzeyi değişimi:** katalog sunucuda değişir; Sync sonrası oturumdaki araçlar değişebilir.
   `doctor.py` ve ölçüm tablosu bunu görmez.
4. **Veri çıkışı:** connector araç sonuçları model bağlamına ve kurumsal denetime gider; ekran/tablo verisi kişisel veri
   içerebilir.
5. **Dış içerik:** connector'dan dönen içerik veridir, talimat değildir; iç wiki/iş takibi içeriği prompt enjeksiyonu
   taşıyabilir.
6. **SAP politika riski (DOĞRULANMADI):** şirket içi bir eklenti belgesi, SAP API politikasının (2026) ajan iş
   akışlarında ADT tarzı API'lerin iş verisi üzerinde kullanımını kısıtladığını aktarıyor. Merkezi bir SAP connector'ı bu
   soruyu büyütür. Birincil politika metni okunmadı.

## 6. Karar önerisi: BEKLE
**Neden "al" değil:** SAP için hazır connector görülmedi, yasak kapıları taşınamıyor, kimlik merkezileşiyor (§4, §5).
**Neden "uyarla" değil:** uyarlanacak davranışın hiçbiri canlı ölçülmedi; katalog aracı adı bile bilinmiyor (K9).
**Neden "alınmaz" değil:** SAP dışı sistemler için değerli olabilir ve aXet'in resmi entegrasyon yolu budur (K1, K2).

**Karar değişim tetikleri:**
- Katalogda iş takibi / wiki / doküman deposu connector'ı var ve `permissions.rules` ile araç bazında deny çalışıyor →
  o sistemler için **uyarla** (skill + deny kuralı + ölçüm tablosu satırı).
- Resmi bir SAP connector'ı çıkar, müşteri ağına erişim ve kimlik modeli kurumsal olarak onaylanır, yazma araçları deny
  ile kapatılabilir → SAP CLI'nin **yanında** salt-okur kullanım için yeniden değerlendir.

**Tek oturumluk ölçüm planı** (template bakım kuralı: `_lab/` projesinde, rastgele işaret + kontrol grubu; yapılmadan
önce ayrı onay):
1. TUI'de Connectors diyaloğunu aç (komut paleti / kısayol) → kurulu ve kullanılabilir listelerini kaydet; SAP ya da
   ilgili sistem connector'ı var mı.
2. Kimlik istemeyen, salt-okur bir connector'ı aktive et → Sync → `axet-code logs` içinde `connector.sync.*`,
   `connector.activate.*` satırları.
3. Yeni oturum: modelden araç listesini iste → katalog aracının adı ve `call_mcp_tool` görünüyor mu (kontrol grubu:
   connector'suz oturum).
4. `permissions.rules` ile connector aracına deny yaz → çağrı bloklanıyor mu (kontrol grubu: kuralsız aynı çağrı).
5. Diyalogdan devre dışı bırak → `axet-code dirs data` altında durum dosyası ve sonraki oturumda aracın kaybolması.
6. `agent` aracıyla alt ajanın connector araçlarını görüp görmediği.
Sonuçlar `docs/axet-davranis-olcumleri.md`'ye satır olarak yazılır; bu not güncellenir.
