# Z56 — aXet.code içinde tarayıcı testi: CANLI ÖLÇÜM RAPORU

Tarih: 2026-09-22 · Ölçen: alt-ajan (salt ölçüm; kod/skill yazılmadı)
Ortam: `axet-code version 1.3.0` (model: `eu.anthropic.claude-sonnet-5`, motor logundaki istek URL'sinden) ·
`@playwright/cli 0.1.21` (repo `github.com/microsoft/playwright-cli`, `npm view` ile doğrulandı; lab'a yerel `npm install`) ·
Node 22.19.0 · Python 3.12.10 · Chrome 153.0.8010.53 · Windows 11.
LAB: `scratchpad/z56-lab/` · ham çıktılar: `scratchpad/z56-*.out`, `z56-*-calls.txt`, `z56-*-server.log`.

## Kanıt yöntemi (ölçümün geçerliliği buna dayanır)

- **Motor logu (`axet-code logs`) araç çağrılarını GÖSTERMİYOR.** Görüntülü `view` çağrısının olduğu turda bile log
  `step_count=2 ... tool_call_count=0` yazıyor (`z56-a-log.txt:93`). Bu yüzden araç çağrısının kanıtı
  **oturum veritabanıdır**: `<cwd>/.axet-code/axet-code.db` → `messages.parts` (JSON; `tool_call` / `tool_result`).
  Döküm betiği: `scratchpad/z56-dbdump.py <db>` (son oturumun CALL/RESULT dizisi).
- **Tahmin edilemeyen işaret:** ⓐ'da sayı dosyada yazılıydı ama istemde verilmedi. ⓑⓒⓓ'de işaret **tıklama anında**
  `crypto.getRandomValues` ile üretiliyor. Yani kaynak dosyada yok, model tahmin edemez. İşaretin doğru olduğunu
  **sunucunun erişim logundaki** `GET /yok-<işaret>` satırı kanıtlar (modelin beyanından bağımsız).

---

## ⓐ `view` PNG'yi modele gösteriyor mu? — **ÇALIŞIYOR**

| | PNG (deney) | TXT (kontrol) |
|---|---|---|
| Komut | `axet-code run -q -d -c <LAB> "Bu klasördeki x.png dosyasını view aracıyla aç ve resmin içinde yazan sayıyı söyle..." </dev/null` | aynısı, `y.txt` |
| rc / süre | 0 / 9 sn | 0 / 11 sn |
| Cevap | `832671 — resmi View aracıyla görsel olarak açıp okudum.` | `167313 — view aracıyla y.txt dosyasını doğrudan okudum...` |
| Gerçek değer | 832671 (`z56-secret/png_num.txt`, lab dışında) | 167313 |
| DB tool_result | `view` · content=`Loaded image/png content` · **mime_type=`image/png`, data=20668 karakter base64** | `view` · content=`<file>\n 1\|Bu dosyadaki sayi: 167313` · mime_type boş, data boş |

- PNG, sayıyı içeren bir HTML sayfasının playwright-cli ile alınan ekran görüntüsüdür. Sayı PNG'nin dışında hiçbir
  yerde metin olarak yoktu: kaynak HTML lab dışında tutuldu, `.playwright-cli/` snapshot artığı silindi,
  `codegraph.json/html`'de `grep -c 832671` = 0. DB'de o turda tek araç çağrısı var: `view x.png`.
- **Sınır:** tek görüntü, büyük punto, tek model (sonnet-5) ile ölçüldü. Küçük yazı ya da karmaşık UI ekran görüntüsünün
  okunma kalitesi ölçülmedi.

## ⓑ bash arka plan işi + yerel sunucu + playwright-cli — **ÇALIŞIYOR (koşullu: `--no-sandbox` config şart)**

**Kontrol grubu (ben, aXet'siz, Git Bash):** `open` → `snapshot` → `click "getByRole('button', { name: 'Tikla' })"` →
`console` → `requests` → `close`: hepsi rc=0, 15 sn. `ISARET-ce3f610b` ve `/yok-ce3f610b` sunucu logunda da var.
playwright-cli hata durumunda gerçekten rc=1 döndürüyor (`file:` engeli ve oturumsuz `goto` ile ölçüldü).

**aXet koşumu** (`z56-b-axet.out`, `z56-b-axet-calls.txt`): rc=0, 149 sn.
- Cevaptaki işaret `ISARET-e848c248`, istek `http://127.0.0.1:8763/yok-e848c248`. Sunucu logunda
  `"GET /yok-e848c248 HTTP/1.1" 404`: **eşleşiyor.**
- Araç dizisi (DB): `bash{run_in_background:true} python -m http.server 8763 ...` → `Background shell started with ID: 001`
  → `job_output` (Status: running) → … → `bash npx playwright-cli -s=axet open --config=pw-nosandbox.config.json …` →
  `find "Tikla"` → `click e3` → `console` + `requests` → `close` → **`job_kill {shell_id:"001"}`** →
  `Background shell 001 terminated successfully`. Koşum sonrası 8763'te LISTENING yok.
- **Reddedilen biçim:** aXet'in bash'inde **varsayılan `open`** (config'siz) iki hatadan biriyle düşüyor:
  `Error: Session closed` (session.js:254) ya da `Error: Target crashed` (`--browser=chrome`). `--browser=msedge` ve
  `--browser=webkit` de düştü. Model 7. denemede kendi `--no-sandbox --disable-dev-shm-usage --disable-gpu` config'ini
  yazınca açıldı.
- **İzole tekrar** (tek komut, yeniden deneme yasak): aXet içinde `npx playwright-cli -s=rep open about:blank` →
  `Error: Session closed`. **Aynı komut benim kabuğumda açılıyor** (kontrol grubu). ⓓ'de yalnız `--no-sandbox`
  içeren config aXet'te yeterli oldu (Chrome'da). Ek ölçümde Edge için de yeterli oldu.
- **Sebep araştırması (daraltılmış):**
  - TEMP farkı **reddedildi**: aXet bash'inde TEMP/TMP=`<cwd>/.axet-code/tmp`. Benim kabuğumda bu TEMP ile `open`
    çalıştı, yani sebep bu değil.
  - Farklı olan tek ölçülen şey **Windows job object**. Kendi `jobcheck.ps1` betiğimle (`IsProcessInJob` +
    `QueryInformationJobObject`) ölçüldü:
    - aXet bash'i: `LimitFlags=0x2608` (KILL_ON_JOB_CLOSE, DIE_ON_UNHANDLED_EXCEPTION, PRIORITY_CLASS,
      ACTIVE_PROCESS), `ActiveProcessLimit=256`, `UIRestrictions=0xA9` (HANDLES, SYSTEMPARAMETERS, GLOBALATOMS,
      EXITWINDOWS).
    - Benim kabuğum: `LimitFlags=0x1800` (yalnız BREAKAWAY_OK), UI kısıtı yok.
  - Chromium sandbox'ının bu kısıtlı job içinde çökmesi `--no-sandbox` ile düzelmesiyle **tutarlı**, ama nedensellik
    **DOĞRULANMADI**.
- **Oturum aXet `run`'ı bitince ölüyor (ölçüldü):** aXet içinde `open` yapıldı, `list` → `kalici: status: open`
  döndü. Run bittikten sonra benim kabuğumdan `list` → `(no browsers)`, playwright chrome süreci 0. KILL_ON_JOB_CLOSE ile
  tutarlı. Tek `run` içinde ise ardışık bash çağrıları arasında oturum yaşıyor (open → click → console çalıştı).
  Etkileşimli TUI oturumundaki ömür ölçülmedi.
- **aXet izin kuralı:** `npx playwright-cli install-browser chromium` →
  `denied by agent permission ruleset (agent "coder", rule bash:"*install-browser*"=deny)`. Tarayıcı indirmek yasak,
  kurulu Chrome/Edge kullanılmalı.
- **Yan etki:** model bir denemede `npx playwright-cli install` koştu. Bu, lab'a `.playwright/` açtı ve
  `%LOCALAPPDATA%\ms-playwright\ffmpeg-1011` indirdi. Reçetede `install` gerekmiyor.

**Hangi tarayıcı kullanıldı? (koordinatör ek sorusu)** → **kurulu Google Chrome (channel `chrome`), indirilmiş Chromium DEĞİL.**
- aXet'in çalışan config'i `"channel": "chrome"` içeriyordu (DB'deki write çağrısı).
- Varsayılan `open`'ın süreç yolu (CIM): `ExecutablePath = C:\Program Files\Google\Chrome\Application\chrome.exe`.
- `%LOCALAPPDATA%\ms-playwright\` içinde yalnız `ffmpeg-1011`, `winldd-1007`, `daemon`, `b` var; **chromium-* dizini
  yok.**

## ⓑ-ek — aynı akış Edge ile — **ÇALIŞIYOR (yine `--no-sandbox` config şart)**

aXet koşumu (`z56-e-edge.out`, `z56-e-edge-calls.txt`): rc=0, 64 sn.
- `open --browser=msedge` (config'siz) → `Error: Session closed` (rc 1).
- Kontrol grubu: aynı komut benim kabuğumda `Browser 'edgectl' opened`.
- `--config=edge-nosandbox.json` (`{"browser":{"launchOptions":{"channel":"msedge","args":["--no-sandbox"]}}}`) →
  açıldı. `click "text=Tikla"` çalıştı. `ISARET-bb65d279` ve `/yok-bb65d279` sunucu loguyla eşleşiyor.
  Sunucu `job_kill` ile kapandı.

## ⓒ Açık Chrome'a CDP ile bağlanma — **ÇALIŞIYOR (Chrome aXet DIŞINDA, `--headless=new` ile başlatılınca)**

Komut: `npx playwright-cli -s=<ad> attach --cdp=http://127.0.0.1:9222` (`--help attach`'ten). Ayırma: `detach`
(Chrome kapanmıyor).

- **Kontrol grubu (ben):** görünür Chrome, geçici profil (`z56-lab\chrome-profil`, kullanıcının kendi profili
  kullanılmadı) → attach → goto → click → console/requests → detach. Hepsi rc=0, 13 sn. `ISARET-0ca30862`
  sunucu logunda var. Detach'ten sonra `/json/list` sayfayı hâlâ gösteriyor.
- aXet 1. koşum: bağlanılamadı (ECONNREFUSED). Chrome koşumdan önce kendiliğinden kapanmıştı (aşağıdaki sınıra bak).
  Bu koşum aynı zamanda aşağıdaki açık kalem (1)'i ortaya çıkardı.
- aXet 2. koşum: `attach` ve `goto` **çalıştı**; `click e3` iki kez `TimeoutError ... waiting for element to be
  visible, enabled and stable` ile düştü. **Kontrol grubu:** aynı Chrome'da benim kabuğumda da aynı hata;
  `eval document.visibilityState` → `"hidden"`. Sebep aXet değil: pencere arkada/örtülü kaldığı için sayfa gizliydi.
  JS ile tıklama (`eval "() => document.getElementById('btn').click()"`) çalıştı.
- aXet 3. koşum: görünür Chrome yine kendiliğinden kapanmıştı. Ön kontrolüm "0" gösterdiği halde koşumu başlattım
  (benim hatam). ECONNREFUSED.
- **aXet 4. koşum (geçerli ölçüm):** Chrome `--headless=new --remote-debugging-port=9222 --user-data-dir=<lab>\chrome-profil`
  ile benim tarafımda başlatıldı. rc=0, 60 sn. Araç dizisi: `attach --cdp=http://127.0.0.1:9222` → `goto` → `find` →
  `click e3` → `requests` → konsol logunu `view .playwright-cli/console-*.log` ile okudu → `detach`.
  `ISARET-80f03769` ve `/yok-80f03769`: sunucu logunda `"GET /yok-80f03769 HTTP/1.1" 404`. Koşumdan sonra
  CDP hâlâ ayakta.
- Dışarıda başlatılan Chrome aXet'in job'ında olmadığı için `--no-sandbox` gerekmedi.
- **Ölçülmedi:**
  - aXet'in CDP Chrome'u kendisinin başlatması. Job kısıtı ve KILL_ON_JOB_CLOSE yüzünden sorunlu olması beklenir,
    ölçülmedi.
  - `agent-browser` (yedek) denenmedi, çünkü playwright-cli attach çalıştı.
- **Sınır / ÖLÇÜLEMEDİ:** görünür (headed) CDP Chrome iki kez koşumlar arasında exit 0 ile kapandı
  (08:50–08:53 ve 09:01–09:03 aralıkları). Sebep ölçülemedi (kullanıcı penceresi kapatmış olabilir; doğrulanmadı).
  3. koşumda aXet başlamadan önce kapanmıştı, yani aXet'in kapattığına dair kanıt yok.

## ⓓ UI5 (CDN, tek sayfa, `sap.m.Button`) — **ÇALIŞIYOR**

Sayfa: `site/ui5.html`, OpenUI5 CDN (`sdk.openui5.org` → HTTP 200). Press handler'ı: `console.error('UI5-ISARET-'+rastgele)`
+ `fetch('/yok-ui5-'+rastgele)`.
- **Kontrol grubu (ben):** snapshot → `button "UI5 Tikla" [ref=e2]`. **Normal `click` press'i TETİKLEDİ**
  (`UI5-ISARET-8d9943be`). `eval "() => { sap.ui.getCore().byId('ui5btn').firePress(); return 'ok'; }"` de tetikledi
  (`UI5-ISARET-b764e346`). `getText()` → `"Basildi"`. İki 404 de sunucu logunda var.
- **aXet** (`z56-d-axet.out`, `z56-d-axet-calls.txt`): rc=0, 76 sn. Config yalnız `--no-sandbox` + channel chrome.
  Click sonrası `UI5-ISARET-6e756af7`, firePress sonrası `UI5-ISARET-9d247e7d`. Sunucu logunda iki `GET /yok-ui5-…
  404` de var: **eşleşiyor.** Reddedilen biçim: `click -e=e2` → `Unknown option: --e`. Doğrusu `click e2`.
- **Sınır:** yalnız `sap.m.Button` ölçüldü. `.click()`'in press'i tetiklemediği vaka (memory dersindeki) bu basit
  örnekte **yeniden üretilmedi**. Diğer kontroller (SmartField, sap.ui.table satırı, ikon butonu) ölçülmedi, bu yüzden
  firePress/eval yedeği reçetede kalmalı.
- UI5 async yüklendiği için ilk `open` snapshot'ında buton olmayabilir. aXet bir kez daha `snapshot` alıp buldu.

---

## aXet skill'ine yazılabilecek reçete taslağı

```bash
# 0) Önkoşul: proje içinde yerel kurulum (global DEĞİL). Tarayıcı İNDİRME yok (aXet install-browser'ı yasaklıyor);
#    kurulu Chrome/Edge kullanılır.
npm install --no-save @playwright/cli        # ya da package.json devDependency

# 1) aXet bash'i kısıtlı bir Windows job içinde koşuyor: varsayılan `open` "Session closed"/"Target crashed" ile düşer.
#    ZORUNLU config (Edge için channel: "msedge"):
cat > pw.json <<'EOF'
{"browser":{"launchOptions":{"channel":"chrome","args":["--no-sandbox"]}}}
EOF

# 2) Yerel sunucuyu bash'in ARKA PLAN özelliğiyle başlat (run_in_background:true). `&` kullanma.
#    Durdurmak için job_kill <shell_id>; log için job_output.
python -m http.server 8763 --bind 127.0.0.1 --directory <webapp> > server.log 2>&1   # ya da: npx ui5 serve / npm start

# 3) Tarayıcı akışı (her komut ayrı bash çağrısı olabilir; oturum aynı `run` içinde yaşar)
npx playwright-cli -s=t open --config=pw.json http://127.0.0.1:8763/
npx playwright-cli -s=t snapshot                  # ref'leri al (e1, e2 ...). UI5 async: buton yoksa tekrar snapshot
npx playwright-cli -s=t click e3                  # ref ile (DOĞRU); `click -e=e3` YANLIŞ
npx playwright-cli -s=t console error             # konsol hataları
npx playwright-cli -s=t requests                  # ağ istekleri (başarısızlar => [404] vb.)
npx playwright-cli -s=t screenshot --filename=shot.png   # görsel kontrol: sonra `view shot.png` (model görüyor, ⓐ)
# UI5 yedeği (click press'i tetiklemezse):
npx playwright-cli -s=t eval "() => { sap.ui.getCore().byId('<id>').firePress(); return 'ok'; }"
npx playwright-cli -s=t close
# 4) sunucuyu kapat: job_kill <shell_id>

# CDP (kullanıcının açık/login'li tarayıcısı): Chrome aXet DIŞINDA, ayrı profil + port ile başlatılır
#   chrome.exe --remote-debugging-port=9222 --user-data-dir=<geçici-profil> [--headless=new]
npx playwright-cli -s=c attach --cdp=http://127.0.0.1:9222
npx playwright-cli -s=c goto <url> ; ... ; npx playwright-cli -s=c detach   # detach Chrome'u kapatmaz
```

**Reçete sınırları:**
- Tarayıcı oturumu `axet-code run` bitince ölüyor (ölçüldü). Etkileşimli TUI'deki ömür ölçülmedi.
- CDP'de görünür pencere arkada kalırsa `click` "visible, enabled and stable" beklerken zaman aşımına düşer
  (sayfa `hidden`). Çare: `--headless=new` ya da pencereyi öne almak ya da `eval` ile JS tıklaması.
- `--no-sandbox` Chromium'un süreç izolasyonunu kapatır. Yalnız yerel/güvenilir sayfalarda kullanılmalı.
- playwright-cli `file:` URL'lerini engelliyor (`Access to "file:" protocol is blocked`), bu yüzden daima bir HTTP
  sunucusu gerekir.
- `.playwright-cli/` dizinine snapshot/konsol logları yazılıyor (sayfa metnini içerir). `.gitignore`'a eklenmeli.

## v0.5.3 reçete ölçümleri (normal kabuk)

v0.5.3 metinlerinde (`kd_ortam.py`, `tuzaklar.md` T23, `runtime-verification.md` §4.1/§4.6, `playwright.config.ts`)
"ölçüldü" diye geçen ama yukarıdaki bölümlerde karşılığı olmayan üç iddia bug gate'ten sonra **yeniden koşuldu**.
**Hepsi aXet.code'un İÇİNDE DEĞİL, normal kabukta** (Claude Code'un Git Bash'i, Windows 11, aXet job'ı dışında)
ölçüldü; aXet bash'indeki davranış için geçerli değildir. Ortam: node v22.19.0 · `@playwright/cli` 0.1.21 +
`playwright-core` 1.64.0-alpha-1789764292000 (lab) · `@playwright/test` 1.63.0 (smoke) · Chrome 153.0.8010.53 ·
Edge 153.0.4234.48 · `%LOCALAPPDATA%\ms-playwright\` içinde chromium dizini yok · `~/.playwright/` yok ·
`PLAYWRIGHT_*` ortam değişkeni yok. Sayfa: `python -m http.server 8767 --bind 127.0.0.1` (tek UI5 sayfası).
Ham çıktılar: `scratchpad/z56-bg/` (`cli/*.out`, `smoke-*.out`, ölçüm betiği `cli/olc.sh`).

**Yöntem (playwright-cli):** her durum için ayrı klasörde `.playwright/cli.config.json` yazıldı →
`playwright-cli -s=<oturum> open [--browser x] http://127.0.0.1:8767/index.html` → `open`'ın bildirdiği pid
**cliDaemon** sürecidir; onun `--type=` içermeyen çocuğu ana tarayıcı sürecidir. O sürecin `Win32_Process.CommandLine`'ı
okundu → `close`. Bilinmeyen bir işaret argümanı (`--z56-isaret-*`) config'e konup süreçte arandı: argümanın gerçekten
taşındığını gösteren kontrol.

| # | config `launchOptions` | `open` bayrağı | süreç (`ExecutablePath`) | `--no-sandbox` | işaret |
|---|---|---|---|---|---|
| a | `channel: chrome` | — | `…\Google\Chrome\Application\chrome.exe` | **False** | — |
| e | `channel: msedge` | — | `…\Microsoft\Edge\Application\msedge.exe` | **False** | — |
| b | `channel: chrome`, `args: ["--no-sandbox"]` (pozitif kontrol) | — | `chrome.exe` | **True** | — |
| c | `channel: msedge`, `args: ["--z56-isaret-c"]` | `--browser chrome` | `chrome.exe` | False | **True** |
| d | `channel: chrome`, `args: ["--z56-isaret-d"]` | `--browser msedge` | `msedge.exe` | False | **True** |
| f | `channel: chrome`, `args: ["--no-sandbox"]` | `--browser msedge` | `msedge.exe` | **True** | — |

Her satırda `open rc=0`, `close` → `Browser '<oturum>' closed`; sonunda `playwright-cli list` → `(no browsers)`.

1. **`open --browser chrome|msedge` config'teki `args`'ı korur — ÖLÇÜLDÜ (normal kabukta).** c/d: `--browser`
   kanalı ezdi (süreç yolu bayraktaki tarayıcı), config'teki işaret argümanı süreçte duruyor; f: `--no-sandbox` da
   `--browser msedge` altında süreçte duruyor. aXet içinde `--browser` + config birleşimi ayrıca ölçülmedi.
2. **Config'te `args` yokken playwright-cli'nin Chrome/Edge süreç komut satırında `--no-sandbox` yok — ÖLÇÜLDÜ
   (normal kabukta).** a/e: False; kontrol grubu b: aynı yöntem `--no-sandbox`'ı gördüğünde True yazıyor (algılama
   çalışıyor). Kaynak karşılığı (playwright-core 1.64.0-alpha-1789764292000, `lib/coreBundle.js`):
   `validateBrowserConfig` (satır 73724-73730) Windows'ta **her kanal için koşulsuz** `chromiumSandbox = true` atar;
   kanala bağlı ifade (`channel !== void 0 && channel !== "chromium" && channel !== "chrome-for-testing"`) yalnız
   `process.platform === "linux"` dalındadır. Chromium başlatıcısı `chromiumSandbox !== true` ise `--no-sandbox`
   ekler (satır 44089-44090).
3. **ui-smoke `--channel chrome|msedge` rc 0 + başlatma satırında `--no-sandbox`; kanalsız kontrol rc 1
   `Executable doesn't exist` — ÖLÇÜLDÜ (normal kabukta).** Komut:
   `DEBUG=pw:browser python run_ui_smoke.py --base-url http://127.0.0.1:8767 --no-auth [--channel chrome|msedge]`
   (koşucu ve `playwright.config.ts` repodakinin birebir kopyası, `diff` boş):
   - `--channel chrome`: `pw:browser <launching> C:\Program Files\Google\Chrome\Application\chrome.exe … --no-sandbox …` ·
     `1 passed (6.7s)` · `rc=0`
   - `--channel msedge`: `pw:browser <launching> C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe … --no-sandbox …` ·
     `1 passed (7.0s)` · `rc=0`
   - kanalsız: `Error: browserType.launch: Executable doesn't exist at C:\Users\<kullanıcı>\AppData\Local\ms-playwright\chromium_headless_shell-1243\chrome-headless-shell-win64\chrome-headless-shell.exe` ·
     `1 failed` · `rc=1` (tarayıcı indirilmedi).
   Kaynak karşılığı: test runner `chromiumSandbox` vermez → başlatıcı `--no-sandbox` ekler. Fark bu yüzden
   playwright-cli (Windows'ta `chromiumSandbox = true`) ile test runner arasındadır.

**Bilgi notu (kaynaktan, ÖLÇÜLMEDİ):** playwright-cli 0.1.21'in `open --help` çıktısında sandbox seçeneği yok (bu kısım
ölçüldü: yalnız `--browser --config --device --headed --idle-timeout --mobile --persistent --profile`). Kaynakta
sandbox'ı kapatmanın iki yolu daha görünüyor: config'te `browser.launchOptions.chromiumSandbox: false` (şemada
`"browser.launchOptions.chromiumSandbox": "boolean"`; `validateBrowserConfig` yalnız tanımsızsa atar) ve
`PLAYWRIGHT_MCP_SANDBOX` ortam değişkeni (`configFromEnv` → `configFromCLIOptions` → `launchOptions.chromiumSandbox`).
İkisi de ne aXet'te ne normal kabukta **ölçüldü**; reçete `args: ["--no-sandbox"]` ile kalır (aXet'te ölçülen tek yol o).

## Açık kalemler (kapsam dışı; düzeltilmedi)

1. **aXet: `fetch` aracının hatası "provider error" gibi ele alınıp BÜTÜN TUR yeniden oynatılıyor.** ⓒ 1. koşumda
   model `fetch http://127.0.0.1:9222/json/version` çağırdı, bağlantı reddedildi. Çıktı:
   `_Transient error (attempt 1/3): failed to fetch URL ... Retrying…_` ×3 →
   `Agent processing failed: failed to start agent processing stream: provider error after 4 attempts: failed to fetch URL`
   → rc=1. DB'de aynı help → attach → netstat → fetch dizisi 4 kez tekrarlanıyor (`z56-c-axet-calls.txt`).
   Bir araç hatası, sağlayıcı hatası sınıfına sızıyor. Kanıt: `scratchpad/z56-c-axet.out`.
2. **aXet: motor logunda `tool_call_count=0`**, oysa DB'de araç çağrısı var (ⓐ: `z56-a-log.txt:93` ↔ DB'deki
   `view` tool_call). Loga dayanan bir izleme araç kullanımını göremez.
3. **aXet bash'inde `netstat` engelli:** `command is not allowed for security reasons: "netstat"`. Bilgi olarak; port
   kontrolü için `curl`/`Test-NetConnection` gerekir (denenmedi).

## Temizlik

- Kapatılanlar: 8761–8767 sunucuları, iki CDP Chrome örneği, tüm playwright oturumları. Son kontrolde
  `127.0.0.1:876[0-8]|9222` LISTENING yok, `playwright-cli list` → `(no browsers)`.
- 8769'daki dinleyici PID 4'e (System) ait, benim değil.
- Kullanıcının Chrome profiline ve aXet repolarına dokunulmadı.
- Lab dışında kalan yan etki: `%LOCALAPPDATA%\ms-playwright\` altında `ffmpeg-1011`, `winldd-1007`, `daemon`,
  `cli-update-check.json` (aXet'in `install` çağrısı ve playwright-cli'nin kendisi oluşturdu).
