# Araştırma: aXet.code (terminal ajanı) için tarayıcı-tabanlı UI test deseni

Tarih: 2026-09-22 · Kapsam: salt-okur web araştırması (repo koduna dokunulmadı)

---

## ① Kısa cevap (5 madde)

1. **Crush hipotezi DOĞRULANDI (güçlü kanıt, ama kısmi).** aXet'in araç listesi (`agent`,
   `agentic_fetch`, `bash`, `download`, `edit`, `fetch`, `glob`, `grep`, `job_kill`,
   `job_output`, `ls`, `lsp_diagnostics`, `lsp_references`, `lsp_restart`, `multiedit`,
   `sourcegraph`, `view`, `write`, `skill_install/publish/search`, `ask_user`, `todos`)
   charmbracelet/crush'ın belgelenmiş tool setiyle isim isim örtüşüyor (bkz. ③). MCP
   davranışı (aXet: yerel MCP config YOK SAYILIR, merkezi "Agentic connectors" var) ise
   crush'ın stock davranışından **AYRIŞIYOR** — bu, şirket-içi bir fork/katman olduğunun
   işareti; bu kısım web'den doğrulanamaz (aXet kapalı/şirket-içi).
2. **Crush'ın kendisi (ve muhtemelen aXet) yerleşik bir tarayıcı/ekran-görüntüsü aracına
   SAHİP DEĞİL.** charmbracelet/crush'ta "Add a browser tool" isteği hâlâ açık bir feature
   request (issue #2826, 7 Mayıs 2026, yanıtsız). Yani aXet'in bash dışında native browser
   aracı olmaması sürpriz değil, üst akış (upstream) davranışıyla tutarlı.
3. **MCP'siz, salt-CLI (stdin/stdout, ayrı process, kalıcı arka-plan tarayıcı) tarayıcı
   otomasyon araçları GERÇEKTEN VAR ve olgun:** Microsoft'un `@playwright/cli` (agent-cli)
   ve Vercel Labs'in `agent-browser`'ı; ikisi de "MCP şeması yükleme" maliyetini atlayıp
   düz kabuk komutlarıyla çalışıyor — aXet'in mevcut `bash` + `job_output` aracıyla
   doğrudan uyumlu (arka planda sunucu/tarayıcı sürekliliği bash job'a devredilebilir).
4. **SAPUI5/Fiori'ye özel, AI-ajan-bilinçli bir Playwright katmanı mevcut:**
   `playwright-praman` (mrkanitkar) — 199 UI5 kontrolünü tanıyor, OData mock/assert
   destekliyor, ve açıkça "CLI agents (stdin/stdout, Playwright CLI tabanlı) MCP
   ZORUNLU DEĞİL" diyor. Bu, aXet + UI5 kombinasyonu için en doğrudan aday.
5. **Görsel doğrulama için model görüntü GÖRMESE bile** a11y/DOM snapshot (erişilebilirlik
   ağacı, `@eN` referanslı kompakt metin) + konsol/network log kombinasyonu, çoğu
   fonksiyonel doğrulama (buton var mı, değer bağlandı mı, hata var mı) için yeterli bir
   ikame; gerçek piksel/görsel regresyon için ekran görüntüsü + insan/vision-model gözden
   geçirmesi hâlâ gerekiyor (repo'daki mevcut Playwright smoke + screenshot deseni zaten bu
   boşluğu kapatıyor).

---

## ② Aday araç tablosu

| Araç | Ne yapar | Bash'ten kullanım | CDP | Snapshot/a11y | Konsol/Network | Windows | Olgunluk | Lisans | Kaynak |
|---|---|---|---|---|---|---|---|---|---|
| **@playwright/cli (playwright agent-cli)** | Playwright'ın resmi, ajanlara özel CLI'ı: `open/navigate/click/type/snapshot/screenshot/console/requests/tracing-start` vb. alt-komutlar; tarayıcı process'i komutlar arası **canlı kalıyor** (state/cookie korunur). | `npx @playwright/cli <komut>` — düz shell çağrısı, MCP client gerekmez. | `playwright-cli attach --cdp=chrome -s=<oturum>` ile var olan Chrome'a bağlanabiliyor (playwright.dev/agent-cli/commands/attach). | Var — "erişilebilirlik ağacını yapılandırılmış metin olarak alıp dosyaya kaydediyor" (testcollab.com/blog/playwright-cli). | `console`, `requests`, `network-state-set` alt-komutları var (playwright.dev/agent-cli listelenen komutlar). | Playwright çekirdeği zaten Windows'u destekliyor; CLI sayfasında OS'a özel kısıtlama görülmedi (DOĞRULANAMADI: sayfa açıkça "Windows" demiyor). | ⚠ **ÇELİŞKİLİ KANIT:** testcollab.com "early 2026'da çıktı" diyor; microsoft/playwright releases sayfasından çekilen özet ise "1.59/1.62, 2024" tarihi veriyor — bu iki tarih birbirini TUTMUYOR, WebFetch özetleyici muhtemelen yanlış release notunu eşledi. **Sürüm/tarih DOĞRULANAMADI**, elle `npx @playwright/cli --version` ile canlı doğrulanmalı. | Playwright çekirdeği **Apache-2.0** (microsoft/playwright reposundan, playwright-cli reposu da Apache-2.0 rozeti taşıyor — ama microsoft/playwright-cli ile @playwright/cli'nin AYNI proje olup olmadığı da net değil, bkz. ⑥). | [playwright.dev/agent-cli/introduction](https://playwright.dev/agent-cli/introduction) · [testcollab.com/blog/playwright-cli](https://testcollab.com/blog/playwright-cli) · [github.com/microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) |
| **agent-browser (Vercel Labs)** | Headless tarayıcı kontrolü; Playwright/Puppeteer bağımlılığı YOK, CDP'yi doğrudan konuşuyor. Kompakt `@eN` referanslı a11y snapshot → sayfa başına ~200-400 token. | `npm install -g agent-browser` sonrası `agent-browser open/snapshot/...` komutları; native Rust binary. | Var, birebir: `agent-browser connect 9222` veya her komuta `--cdp` bayrağı; var olan Chrome'a `--remote-debugging-port=9222` ile bağlanabiliyor. | Var — `snapshot` komutu `-i` (yalnız etkileşimli), `-c` (kompakt), `-d` (derinlik), `-s` (CSS scope), `--delta` (artımlı) seçenekleriyle. | Doğrudan doğrulanamadı; genel README'de network/console'a atıf bulunamadı (DOĞRULANAMADI). | Evet, README'de açıkça ele alınıyor: "Windows'ta agent-browser headless Chrome'u özel bir masaüstünde başlatır (görünür pencere sızdırmaz)"; profil özellikleri için Windows'ta Chrome'un kapalı olması gerektiği notu var. | Repo aktif (684 commit), Apache-2.0 lisanslı. **Yıldız sayısı ("43.000") ŞÜPHELİ/DOĞRULANAMADI** — WebFetch özetleyicisinin başka bir rozetle (ör. genel Vercel projeleri) karıştırmış olma ihtimali yüksek; elle `gh api repos/vercel-labs/agent-browser` ile teyit edilmeli. | Apache-2.0 (README rozeti). | [github.com/vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) · [agent-browser.dev/installation](https://agent-browser.dev/installation) · CDP mode: [docs/src/app/cdp-mode/page.mdx](https://github.com/vercel-labs/agent-browser/blob/main/docs/src/app/cdp-mode/page.mdx) |
| **chrome-devtools-mcp (CLI modu)** | MCP sunucusu olarak tasarlanmış ama ayrıca **CLI wrapper**'ı var: `chrome-devtools <tool> [args] [flags]`. İlk çağrıda arka planda bir daemon (Windows'ta named pipe, Linux/Mac'te Unix socket) + tarayıcıyı otomatik başlatıyor, sonraki çağrılar aynı oturumu kullanıyor. | `npm i chrome-devtools-mcp@latest -g` sonra doğrudan `chrome-devtools list_pages` vb. — MCP client GEREKMİYOR. | CDP zaten temel protokolü (Chrome DevTools Protocol'ün kendisi); var olan Chrome'a bağlanma seçeneği dokümantasyonda var ama bu araştırmada ayrı doğrulanmadı (DOĞRULANAMADI — spesifik `--browser-url` bayrağı teyit edilmedi). | Var — `take_snapshot` komutu ayrı; ayrıca `take_screenshot`, `take_heapsnapshot`. | Var — `list_console_messages`/`get_console_message`, `list_network_requests`/`get_network_request`. | Named pipe desteği (Windows) README'de açıkça yazılı → **Windows desteği VAR** görünüyor (daemon iletişim katmanı OS'a göre ayrılmış). | Google/Chrome DevTools ekibi tarafından resmi olarak bakımı yapılıyor (github.com/ChromeDevTools/chrome-devtools-mcp); "skills/chrome-devtools-cli/SKILL.md" ayrı bir kurulu skill olarak paketlenmiş. Sürüm/tarih bu turda çekilmedi (DOĞRULANAMADI). | DOĞRULANAMADI (bu turda okunmadı). | [github.com/ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) · [docs/cli.md](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md) · [skills/chrome-devtools-cli/SKILL.md](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/skills/chrome-devtools-cli/SKILL.md) |
| **playwright-praman** | SAPUI5/Fiori'ye ÖZEL Playwright eklentisi: 199 UI5 kontrol tipini tanıyan `ui5.control({...})` API'si, OData V2/V4 mock/assert, Fiori Elements yardımcıları; ayrıca "Planner/Executor/Reporter" gibi 3 ajanlı otomatik test-üretim hattı (iş süreci tanımından Playwright koduna). | `npx playwright-praman init` sonrası proje içi test dosyaları; **CLI agent modu** (`-cli` soneki taşıyan agent dosyaları) "stdin/stdout üzerinden, Playwright CLI kullanır — MCP GEREKMEZ" (repo README, WebFetch özeti). Ayrıca `npm run start:mock` ile yerel mock-OData sunucusu. | Playwright'ın altyapısını kullandığı için CLI-CDP zincirinden yararlanabilir (DOĞRULANAMADI, ayrı test edilmedi). | Playwright'ın snapshot altyapısını + UI5 runtime registry sorgusunu birleştiriyor (SmartField iç kontrolleri, OData binding path'leri dahil) — bu **UI5'e özgü** ve diğer genel araçlarda YOK. | Repo README'sinde "tracing raporları" ve OData istek doğrulama geçiyor; ayrıntılı konsol/network API bu turda incelenmedi (DOĞRULANAMADI). | README: "Windows, macOS, Linux destekler." (WebFetch özeti) | 11 yıldız, 458 commit — **küçük/genç bir proje**, geniş topluluk kanıtı YOK; "CISO-onaylı, zero npm audit vulnerabilities" pazarlama ifadesi, bağımsız doğrulanmadı. | Apache-2.0 (repo rozeti). | [github.com/mrkanitkar/playwright-praman](https://github.com/mrkanitkar/playwright-praman) · [praman.dev](https://praman.dev/) · [praman.dev/docs/guides/playwright-cli-agents](https://praman.dev/docs/guides/playwright-cli-agents) (bu alt-sayfa bu turda AÇILMADI — DOĞRULANAMADI) |
| **Chrome uzantısı köprüleri (browser-bridge-cli, claude-browser-bridge, chromium-bridge vb.)** | WebSocket/native-messaging ile bir Chrome uzantısına bağlanıp KULLANICININ AÇIK sekmesini/oturumunu (login dahil) kontrol ediyor; "gerçek fare tıklaması" (chrome.debugger/CDP) kullananları var. | Evet, bash'ten CLI komutlarıyla (`browser-bridge-cli ...` vb.) çağrılıyor; bazıları ayrıca MCP sunucusu olarak da paketlenmiş. | Var — temel mekanizma CDP (`chrome.debugger`) veya uzantı-native-messaging köprüsü. | Değişken; bazıları erişilebilirlik ağacı, bazıları yalnız DOM/ekran görüntüsü sunuyor (proje bazında farklı, tek tek doğrulanmadı). | Bazılarında var ("network option enables per-tab CDP Network cache", "console/network first CDP touch of the tab" — chromium-bridge). | Chrome uzantısı tabanlı olduğu için OS-bağımsız (uzantı + native host); Windows'ta native-messaging host kaydı gerekiyor (genel Chrome native-messaging mimarisi). | Küçük/toplulukça bakımlı, resmi değil; Anthropic'in KENDİ "Claude in Chrome" entegrasyonu ayrı ve resmi ama Desktop/CLI native-host çakışma buglarıyla bilinen (issue #54567, #65682, anthropics/claude-code). | Proje bazında değişir, bu turda tek tek okunmadı (DOĞRULANAMADI). | [github.com/dreamhunter2333/browser-bridge-cli](https://github.com/dreamhunter2333/browser-bridge-cli) · [github.com/softwaresoftware-dev/claude-browser-bridge](https://github.com/softwaresoftware-dev/claude-browser-bridge) · [github.com/whg517/browser-bridge](https://github.com/whg517/browser-bridge) |
| **wdi5 + OPA5/QUnit + `@sap-ux/ui5-middleware-fe-mockserver`** | UI5'in KENDİ test ekosistemi: QUnit=birim, OPA5=entegrasyon (aynı runtime içinde, tarayıcı gerektirmez — `karma-ui5` + ChromeHeadless ile headless koşulabilir), wdi5=Webdriver.IO tabanlı E2E (gerçek tarayıcı/Appium). Mock backend `@sap-ux/ui5-middleware-fe-mockserver` ile. | `npm run test`/`karma start` gibi standart Node komutları; bash'ten sorunsuz çağrılabilir, MCP/tarayıcı-ajanı GEREKMEZ (bunlar zaten "headless test runner" mantığında). | Yok/İlgisiz — bu araçlar CDP değil WebDriver/JSDOM temelli. | Yok (görsel/a11y snapshot değil, assertion-tabanlı test). | wdi5 Webdriver.IO üzerinden network/console erişimine sahip olabilir (Webdriver.IO'nun kendi altyapısı); bu turda ayrı doğrulanmadı. | wdi5 headless Firefox/Chrome'u CI'da (BAS "Headless Testing Framework" dahil) çalıştırabiliyor — Windows dahil genel Node.js platformlarında çalışır (genel bilgi, bu turda özel doğrulanmadı). | Olgun, SAP ekosisteminde uzun süredir kullanılıyor (SAP Community blog 2020'den beri belgeleniyor); **"AI ajanıyla" doğrudan kullanım örneği web aramasında BULUNAMADI** (arama "no results specifically mentioning AI agent" döndü). | Açık kaynak (SAPUI5/OpenUI5 ekosistemi altında; spesifik lisans bu turda okunmadı). | [blogs.sap.com/2020/11/19/state-of-testing-in-ui5-opa5-uiveri5-and-wdi5](https://blogs.sap.com/2020/11/19/state-of-testing-in-ui5-opa5-uiveri5-and-wdi5/) · [github.com/skarolus/wdi5](https://github.com/skarolus/wdi5) |

---

## ③ Crush hipotezi sonucu — DOĞRULANDI (araç-adı düzeyinde), MCP-katmanı düzeyinde AÇIK

**Kanıt (tool adı eşleşmesi, DeepWiki + Mintlify resmi Crush dokümantasyonundan):**

| aXet aracı | Crush karşılığı (kaynak) |
|---|---|
| `agent` | "Agent Tool (`agent`)" — genel amaçlı alt-agent delegasyonu ([deepwiki.com/.../6.7-agent-tool](https://deepwiki.com/charmbracelet/crush/6.7-agent-tool)) |
| `agentic_fetch` | "Agentic Fetch Tool (`agentic_fetch`)" — web araştırmasına özel (aynı kaynak) |
| `view`, `edit`, `write`, `multiedit`, `grep`, `glob`, `ls`, `bash` | Crush'ın temel dosya/kabuk araçları ([charmbracelet-crush.mintlify.app/tools/overview](https://charmbracelet-crush.mintlify.app/tools/overview)) |
| `lsp_diagnostics`, `lsp_references` | Crush'ın "Diagnostics"/"References" LSP araçları (aynı kaynak) |
| `download` | Crush kaynak ağacında ayrı dosya: `internal/agent/tools/download.go` (DeepWiki) |
| `job_output`, `job_kill` | Crush'ın arka-plan iş yönetimi: "bash tool takes `auto_background_after` (varsayılan 60s); eşiği aşan komut öldürülmek yerine arka-plan işine taşınır"; `job_output`/`job_kill` Crush permissions config'de ayrı tool olarak listeleniyor ([charmbracelet-crush.mintlify.app/configuration/permissions](https://charmbracelet-crush.mintlify.app/configuration/permissions), FreePeak/xdev issue #317 karşılaştırması) |
| `sourcegraph` | Crush'ta VARDI, sonra context-yükünü azaltmak için kaldırıldı: PR "tools: drop sourcegraph tool by meowgorithm" ([github.com/charmbracelet/crush/pull/3859](https://github.com/charmbracelet/crush/pull/3859)) — **aXet'te hâlâ mevcut olması, aXet'in bu PR'dan ÖNCEKİ bir crush sürümünden fork'landığını veya aracı bilinçli geri eklediğini düşündürüyor (DOĞRULANAMADI, sadece çıkarım).** |
| `skill_install/publish/search` | Crush'ın "Skills System"i (proje-analiz sonucu context dosyası üretme, manuel/otomatik yükleme) — isim eşleşmesi tam değil (`install/publish/search` alt-komutları ayrı doğrulanmadı) |
| `ask_user` | Crush'ın "Question" aracı (bir kaynakta "Soru soruş" olarak geçti) — isim tam eşleşmedi (DOĞRULANAMADI) |
| `todos` | Crush'ın "Task Management" bileşeni — isim tam eşleşmedi (DOĞRULANAMADI) |
| `code_graph` | Crush dokümantasyonunda bu isimde bir araç BULUNAMADI (DOĞRULANAMADI/muhtemelen aXet'e özgü ek) |

**Soy zinciri:** Crush, 2025 ortasındaki "OpenCode" projesinin ikiye bölünmesinden doğdu:
Charm, orijinal yaratıcıyı işe alıp Go tabanlı devamını "Crush" adıyla sürdürdü; SST tarafı
ise TypeScript'e geçip "opencode" adını korudu (kaynak: [Ry Walker Research](https://rywalker.com/research/crush),
[github.com/charmbracelet/crush discussion #360](https://github.com/charmbracelet/crush/discussions/360) ve #1097). Yani "aXet ~ eski opencode" değil,
tool-adı kanıtı **doğrudan Charm'ın Crush'ına** işaret ediyor (opencode/TS tarafında bu isimler
bu turda karşılaştırılmadı — DOĞRULANAMADI).

**Sonuç:** aXet'in çekirdek tool-seti **crush ile isim-bazlı neredeyse birebir** — bu güçlü
bir kanıt (11+ tool adı örtüşmesi, tesadüf olasılığı düşük). Ama aXet'in MCP davranışı
("yerel MCP config yok sayılır, merkezi Agentic connectors var") **crush'ın stock
davranışından ayrışan şirket-içi bir katman/fork** olduğunu gösteriyor — bu kısım
kapalı/şirket-içi olduğu için web'den doğrulanamaz, yalnız log kanıtından (kullanıcı
verdi) biliniyor.

**Pratik sonuç — browser tool için:** Crush'ın kendisinde native browser/screenshot aracı
YOK (issue #2826 hâlâ açık, 7 Mayıs 2026'dan beri yanıtsız) → aXet'in de muhtemelen
YOK olması (gözlemlenen tool listesiyle tutarlı) sürpriz değil; MCP-tabanlı "playwright
MCP" gibi bir çözüm aXet'in mimarisinde (yerel MCP yok sayılıyor) **muhtemelen
çalışmayacak** — bash-tabanlı CLI araçları (④/②) daha uygun aday.

---

## ④ UI5'e özgü bulgular

- **`playwright-praman`** (② tablosunda detaylı) — şu ana kadar bulunan **tek**, UI5
  kontrol-tipi-farkında (199 kontrol), OData-farkında, hem MCP hem CLI-modlu açık kaynak
  araç. Küçük/genç proje (11 yıldız) — olgunluk riski var, ama **UI5 semantiğini bilen
  tek aday** olması nedeniyle önemli.
- **wdi5 + OPA5/QUnit + mockserver** — UI5'in resmi/olgun test yığını, ama "AI ajanıyla
  kullanım" için web'de doğrudan örnek/tarif **BULUNAMADI**. Bu, ajanın genel Playwright
  CLI/agent-browser ile ham DOM/a11y üzerinden çalışması gerektiği (UI5 kontrol
  semantiğinden bağımsız, düz HTML elemanı gibi davranarak) anlamına gelebilir —
  DOM-tabanlı bir freestyle UI5 uygulamasında (aXet template'inin hedefi) bu muhtemelen
  yeterli, çünkü nihai render edilmiş DOM standart HTML/ARIA'dır.
- **Genel Fiori "AI test" örneği** ([likweitan.github.io/ai-agent-fiori-testing](https://likweitan.github.io/ai-agent-fiori-testing/)):
  Claude Code + **Playwright MCP** (CLI değil) + özel "sap-fiori-apps-reservationreference"
  skill'i + "docx" skill'i kombinasyonuyla, fonksiyonel spec'ten test senaryosu çıkarıp
  canlı sistemde koşturup ekran-görüntülü rapor üretiyor. **Bu örnek MCP'ye dayanıyor** —
  aXet'in yerel MCP'yi yok saydığı göz önüne alınınca doğrudan taşınamaz, ama **desen**
  (spec→senaryo→canlı-koşum→ekran-görüntülü-rapor) CLI araçlarıyla da taklit edilebilir.
- SAP Fiori Tools'un kendi "mock server" özelliği (`npm run start:mock` /
  `@sap-ux/ui5-middleware-fe-mockserver`) — freestyle UI5 uygulamasını **backend'siz**
  başlatıp test etmek için standart, aracın kendisi AI'dan bağımsız; ajan bunu bash'ten
  başlatıp arka-plana alabilir (`job_output`/`job_kill` ile birebir uyumlu).

---

## ⑤ aXet için önerilen 1-2 yol + ilk ölçüm adımları

**Yol A (önerilen, en düşük riskli — mevcut deseni genişlet):**
aXet zaten Playwright smoke koşucusuna (`run_ui_smoke.py` + `ui.smoke.spec.ts`) ve
playwright-cli ile ekran görüntüsüne sahip (görev bağlamında belirtildi). Bunu **CLI-modda**
(`@playwright/cli` / `npx playwright cli`, MCP DEĞİL) çalıştırmaya devam et:
1. `ui5 serve` / Fiori Tools preview'ı **arka planda** başlat (`bash` + `job_output` ile
   log takip; `job_kill` ile durdur) — mevcut şablon zaten bu deseni yapıyorsa doğrula.
2. `npx @playwright/cli open <url>` → `snapshot` (a11y ağacı, ucuz) ile fonksiyonel
   kontrol (buton/etiket var mı, OData hata mesajı yok mu).
3. Görsel/nihai doğrulama gerektiğinde `screenshot` al, dosyaya kaydet — model görseli
   DOĞRUDAN göremiyorsa (aXet'in vision desteği bu turda doğrulanmadı — DOĞRULANAMADI),
   `view` aracının PNG dosyasını okuyup okuyamadığını **canlı test et** (küçük bir PNG
   ile: `view screenshot.png` çağrısı model çıktısında görüntüyü tanıyor mu?).
4. İLK ÖLÇÜM: `npx @playwright/cli --version` + `npx @playwright/cli open about:blank`
   komutlarını aXet'in `bash` aracından koşturup (a) kurulu mu (b) arka planda kalıp
   kalmadığı (c) `job_output` ile çıktısının okunabilirliği CANLI doğrulanmalı — bu
   araştırma raporu yalnız web kanıtı sunuyor, aXet ortamında ÇALIŞTIĞI DOĞRULANMADI.

**Yol B (UI5-spesifik, daha riskli — yeni bağımlılık):**
`playwright-praman`'ın CLI-agent modunu (`-cli` soneki, MCP gerektirmiyor) dener:
1. `npx playwright-praman init` ile şablon dosyalarını incele (repo koduna DOKUNMADAN,
   önce ayrı bir scratch dizinde dene).
2. `ui5.control({...})` API'sinin gerçekten UI5 runtime registry'sinden okuduğunu
   (yani statik selector değil, gerçek kontrol-tipi eşlemesi) küçük bir örnek uygulamada
   doğrula.
3. Olgunluk riski (11 yıldız, tek-geliştirici izlenimi) nedeniyle **üretim akışına
   bağlamadan önce** izole bir denemeyle sınırlı tut.

**Her iki yolda da:** aXet'in `agent`/`agentic_fetch` araçlarıyla "önce spec'i oku, sonra
canlı sistemde ajanı tarayıcı-CLI'a yönlendir, sonucu `job_output`'tan topla" zinciri,
mevcut tool-setiyle (ek MCP gerektirmeden) kurulabilir görünüyor — ama bu bir TASARIM
ÖNERİSİDİR, aXet üzerinde ÇALIŞTIĞI TEST EDİLMEDİ.

---

## ⑥ Doğrulanamayanlar (açıkça işaretli)

- **`microsoft/playwright-cli` (ayrı repo, "13.5k yıldız" iddiası) ile `@playwright/cli`
  (playwright.dev/agent-cli, "early 2026 launched" iddiası) AYNI PROJE Mİ** — WebFetch
  özetleri birbiriyle ÇELİŞTİ (tarih: 2024 vs 2026; repo: ayrı isim). **DOĞRULANMADI.**
  Kullanmadan önce `npm view @playwright/cli` + `gh repo view microsoft/playwright-cli`
  ile elle teyit gerekir.
- **`agent-browser`'ın "43.000 yıldız" iddiası** — bu, WebFetch'in sayfadan yanlış bir
  rozet/istatistik çekmiş olma ihtimaliyle **ŞÜPHELİ**; niş bir Vercel Labs aracı için
  aşırı yüksek. **DOĞRULANMADI**, `gh api repos/vercel-labs/agent-browser --jq .stargazers_count`
  ile teyit edilmeli.
- **chrome-devtools-mcp CLI'ın var olan bir Chrome'a (`--browser-url`/CDP) bağlanıp
  bağlanamadığı** — bu turda ayrı doğrulanmadı.
- **Crush'ın `view` aracının modele GERÇEKTEN görüntü (PNG) gönderip göndermediği** —
  bulunanlar, Crush'ın kendi TUI dosya-önizlemesinde (insan kullanıcı için) `fimage`
  paketiyle görüntü render ettiğini gösteriyor; bu, LLM'e multimodal görüntü GÖNDERME
  (`view` aracı çıktısı olarak) ile AYNI ŞEY DEĞİL. Ayrı, açık issue'lar (#995 Gemini
  400 hatası, #846 "paste image" isteği, #996 "slash-completion image attach" isteği)
  görüntü-ekleme akışının 2026 ortasında hâlâ kırılgan/eksik olduğunu düşündürüyor ama
  bu **aXet'in kendi vision desteğine** genellenemedi.
- **aXet'in kendi "Agentic connectors" katmanının** hangi araçları (MCP benzeri) sunduğu,
  browser-otomasyon connector'ı olup olmadığı — bu **şirket-içi/kapalı** bir konu, web
  araştırmasıyla erişilemez; yalnız aXet dokümantasyonu/loglarından teyit edilebilir.
- **wdi5/OPA5'in Windows'ta headless Chrome ile ajan-tetiklemeli çalıştığı** — genel
  bilgiye dayanıyor, bu turda spesifik kaynakla doğrulanmadı.
- **`playwright-praman`'ın CLI-agent kılavuzu** (`praman.dev/docs/guides/playwright-cli-agents`)
  bu turda AÇILMADI — yalnız README özetine dayanıldı.
- **Lisans bilgisi eksik olanlar:** chrome-devtools-mcp (bu turda okunmadı), tüm Chrome
  uzantı-köprüsü projeleri (tek tek incelenmedi).

---

### Kaynak listesi (tüm URL'ler)

- [github.com/charmbracelet/crush](https://github.com/charmbracelet/crush)
- [charmbracelet-crush.mintlify.app/tools/overview](https://charmbracelet-crush.mintlify.app/tools/overview)
- [charmbracelet-crush.mintlify.app/configuration/permissions](https://charmbracelet-crush.mintlify.app/configuration/permissions)
- [deepwiki.com/charmbracelet/crush/6.7-agent-tool](https://deepwiki.com/charmbracelet/crush/6.7-agent-tool)
- [deepwiki.com/charmbracelet/crush/6.5-mcp-integration](https://deepwiki.com/charmbracelet/crush/6.5-mcp-integration)
- [github.com/charmbracelet/crush/issues/2826](https://github.com/charmbracelet/crush/issues/2826) (browser tool feature request, açık)
- [github.com/charmbracelet/crush/pull/3859](https://github.com/charmbracelet/crush/pull/3859) (sourcegraph tool kaldırıldı)
- [github.com/charmbracelet/crush/discussions/360](https://github.com/charmbracelet/crush/discussions/360) · [issues/1097](https://github.com/charmbracelet/crush/issues/1097) (opencode/crush ayrımı)
- [rywalker.com/research/crush](https://rywalker.com/research/crush)
- [playwright.dev/agent-cli/introduction](https://playwright.dev/agent-cli/introduction) · [playwright.dev/agent-cli/commands/attach](https://playwright.dev/agent-cli/commands/attach)
- [testcollab.com/blog/playwright-cli](https://testcollab.com/blog/playwright-cli)
- [tester.army/blog/inside-playwright-cli-browser-automation-for-coding-agents](https://tester.army/blog/inside-playwright-cli-browser-automation-for-coding-agents)
- [github.com/microsoft/playwright-cli](https://github.com/microsoft/playwright-cli)
- [www.ytyng.com/en/blog/ai-browser-automation-tools-comparison-2026](https://www.ytyng.com/en/blog/ai-browser-automation-tools-comparison-2026)
- [github.com/vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) · [agent-browser.dev/installation](https://agent-browser.dev/installation) · [cdp-mode/page.mdx](https://github.com/vercel-labs/agent-browser/blob/main/docs/src/app/cdp-mode/page.mdx)
- [github.com/ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) · [docs/cli.md](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md) · [skills/chrome-devtools-cli/SKILL.md](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/skills/chrome-devtools-cli/SKILL.md)
- [developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session](https://developer.chrome.com/blog/chrome-devtools-mcp-debug-your-browser-session)
- [github.com/mrkanitkar/playwright-praman](https://github.com/mrkanitkar/playwright-praman) · [praman.dev](https://praman.dev/)
- [medium.com/@mrkanitkar/how-ai-agents-are-solving-sap-ui5-test-automation](https://medium.com/@mrkanitkar/how-ai-agents-are-solving-sap-ui5-test-automation-discovery-and-interaction-with-59b0e3e9d649)
- [likweitan.github.io/ai-agent-fiori-testing](https://likweitan.github.io/ai-agent-fiori-testing/)
- [blogs.sap.com/2020/11/19/state-of-testing-in-ui5-opa5-uiveri5-and-wdi5](https://blogs.sap.com/2020/11/19/state-of-testing-in-ui5-opa5-uiveri5-and-wdi5/)
- [github.com/skarolus/wdi5](https://github.com/skarolus/wdi5)
- [github.com/dreamhunter2333/browser-bridge-cli](https://github.com/dreamhunter2333/browser-bridge-cli)
- [github.com/softwaresoftware-dev/claude-browser-bridge](https://github.com/softwaresoftware-dev/claude-browser-bridge)
- [github.com/whg517/browser-bridge](https://github.com/whg517/browser-bridge)
- [code.claude.com/docs/en/chrome](https://code.claude.com/docs/en/chrome)
- [github.com/anthropics/claude-code/issues/54567](https://github.com/anthropics/claude-code/issues/54567) · [issues/65682](https://github.com/anthropics/claude-code/issues/65682)
- Crush görüntü-ekleme issue'ları: [#995](https://github.com/charmbracelet/crush/issues/995) · [#846](https://github.com/charmbracelet/crush/issues/846) · [#996](https://github.com/charmbracelet/crush/issues/996)
