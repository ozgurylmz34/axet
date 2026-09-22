# Z60 — tarayıcı testinin kullanıcı komut çalıştırmadan hazır olması: CANLI ÖLÇÜM RAPORU

Tarih: 2026-09-22 · Ölçen: alt-ajan · Kullanıcı ilkesi (onaylı 2026-09-22): "kullanıcının ayrı komut çalıştırması
gerekmemeli". Onaylı yazma yerleri: aXet merkezi klonu (template kökü) ve `~/.playwright/cli.config.json`.
Ortam: `axet-code version 1.3.0` · `@playwright/cli 0.1.21` (+ `playwright-core 1.64.0-alpha-1789764292000`) ·
Node 22.19.0 · npm 10.9.3 · Chrome (kurulu, `C:\Program Files\Google\Chrome\Application\chrome.exe`) · Windows 11.
LAB: `scratchpad/z60/` (ham çıktılar aşağıda dosya adıyla). Gerçek kullanıcı klasöründeki `~/.playwright/` ölçüm
boyunca YOKTU ve dokunulmadı (`ls ~/.playwright` → `No such file or directory`, ölçüm öncesi ve sonrası).

## Kanıt yöntemi

- Z56 ile aynı: araç çağrısının kanıtı **oturum veritabanı** `<cwd>/.axet-code/axet-code.db` → `messages.parts`
  (`z56-dbdump.py`). Model beyanı kanıt sayılmadı; her iddia DB'deki `tool_call` + `tool_result` satırına dayanır.
- **Süreç kanıtı (modelden bağımsız):** koşum sırasında benim kabuğumda 0,7 sn aralıkla `Win32_Process` taraması
  (`izle.ps1`): `chrome.exe`/`msedge.exe`, `--type=` içermeyen (ana süreç), komut satırında `remote-debugging-pipe`
  (playwright'ın başlattığı tarayıcı) → `ExecutablePath` + komut satırında `--no-sandbox` var mı.
- **Ev dizini değiştirildi, gerçek `~` değil:** aXet'e `PWTEST_CLI_GLOBAL_CONFIG=<lab>\ev-*` verildi (aXet bash'i ortamı
  devralıyor, Z56 `axet-env.txt`). Bu değişkenin gerçekten okunduğu kaynakta: `playwright-core/lib/coreBundle.js`
  `resolveCLIConfigForCLI` → `path.join(env.PWTEST_CLI_GLOBAL_CONFIG ?? os.homedir(), ".playwright",
  "cli.config.json")` (satır 73688); ölçümde: aynı komut ev-bos ile düştü, ev-dolu ile açıldı ve `--no-sandbox` süreçte
  göründü (aşağıda) — başka hiçbir fark yoktu.
- `USERPROFILE` yerine `PWTEST_CLI_GLOBAL_CONFIG` seçilmesinin sebebi ölçüldü: normal kabukta
  `USERPROFILE=<lab>\ev-dolu node -e "console.log(require('os').homedir())"` → `<lab>\ev-dolu` (node homedir =
  USERPROFILE) ve bu ortamla `open`'ın başlatma satırında `--no-sandbox` VAR (config okundu), ama Chrome'un kendisi
  `DevTools remote debugging requires a non-default data directory` ile kapandı (`izle-userprofile.txt`) —
  USERPROFILE'ı değiştirmek tarayıcıyı da etkiler, ölçümü kirletir.

## ⓐ Merkezi kurulum + TAM YOL ile çağrı — **ÇALIŞIYOR (Windows biçimli yolla)**

Kurulum: `npm install --prefix <lab>\kok\.araclar\playwright-cli --no-audit --no-fund @playwright/cli@0.1.21` →
`added 3 packages in 10s`. `%LOCALAPPDATA%\ms-playwright\` listesi kurulum öncesi/sonrası aynı (tarayıcı indirilmedi).
aXet: `axet-code run -q -d -c <lab>\proje "<istem>" </dev/null`, `cwd = <lab>\proje` (içinde `.playwright/` YOK).

| # | Çağrı biçimi | Sonuç (DB tool_result) |
|---|---|---|
| a0 | `node "/c/Users/…/playwright-cli.js" -s=z60k open …` (POSIX yol) | 3 komut da rc 1, `MODULE_NOT_FOUND` — node yolu `C:\c\Users\…` olarak aldı (`axetdb-kontrol-posixyol`) |
| a1 | `node "C:/Users/…/playwright-cli.js" -s=z60b open "data:text/html,<h1>Z60-OLUMLU</h1>"` | `### Browser \`z60b\` opened with pid 2904.` |
| a2 | `… -s=z60b snapshot` | `- heading "Z60-OLUMLU" [level=1] [ref=e2]` |
| a3 | `… -s=z60b close` | `Browser 'z60b' closed` |

(a1–a3 ev-dolu ile, `axetdb-b`, koşum rc 0, 58 sn.) ⇒ merkezi kurulum başka bir proje klasöründen **tam yolla**
çalışıyor; yol **`C:/…` biçiminde** verilmeli. `/c/…` biçimi aXet bash'inde ÇALIŞMIYOR (ölçüldü). Belgelerdeki `PW=`
ve betiğin bastığı `KOMUT:` satırı bu yüzden `as_posix()` (`C:/…`) biçimindedir.

## ⓑ Proje config'i yokken global `~/.playwright/cli.config.json` okunuyor mu — **EVET**

Global dosya (ev-dolu): `{"browser":{"browserName":"chromium","launchOptions":{"channel":"chrome","args":["--no-sandbox"]}}}`

| | Kontrol grubu (ev-bos: global dosya YOK) | Deney (ev-dolu) |
|---|---|---|
| `open` | rc 1 · `### Browser \`z60k\` opened with pid 19644.` + `Error: Target crashed` (`axetdb-kontrol`) | rc 0 · `opened with pid 2904` |
| `snapshot` | rc 1 · `Error: Target crashed` + `Assertion error` | rc 0 · başlık görünüyor |
| `close` | `Browser 'z60k' is not open.` | `Browser 'z60b' closed` |
| Süreç komut satırı | tarama kalıbı yanlıştı (`ud-z60k`; isolated oturumda kullanıcı dizini `playwright_chromiumdev_profile-*` olur) → **ÖLÇÜLMEDİ**; Z56 normal kabuk ölçümü: args yokken `--no-sandbox` YOK | `izle-b.txt`: `exe=C:\Program Files\Google\Chrome\Application\chrome.exe nosandbox=True` (user-data-dir `…\proje\.axet-code\tmp\playwright_chromiumdev_profile-lZxNg4`) |

⇒ Proje klasöründe `.playwright/` yokken global dosya okunuyor, `--no-sandbox` tarayıcı sürecine taşınıyor ve aXet
bash'inde tarayıcı açılıyor. Global dosya yokken aynı komut düşüyor (Z56'daki `Session closed`/`Target crashed`
ailesi; bu koşumda `Target crashed`).

## ⓒ Kurulum betiği aXet'in İÇİNDEN (uçtan uca, `%guncelle` adım 16'nın koşacağı biçim) — **HAZIR**

Taze lab kökü (`kok3`: yalnız `scripts/tarayici_hazirla.py` + `skills-sap/.../kd_ortam.py`), boş ev (`ev3`).
aXet'e tek komut: `python "C:/…/kok3/scripts/tarayici_hazirla.py"`. Koşum rc 0, 38 sn. DB tool_result:
`TARAYICI: HAZIR — chrome (C:\Program Files\Google\Chrome\Application\chrome.exe) · playwright-cli 0.1.21 kuruldu ·
global config yazıldı (…\ev3\.playwright\cli.config.json, kanal chrome · --no-sandbox) · duman testi geçti (open →
snapshot'ta işaret → close)`. Süreç taraması (`izle-betik-axet.txt`): `chrome.exe nosandbox=True`. Yazılan dosya
birebir yukarıdaki global biçim; `kok3/.araclar/` içinde `.gitignore` (`*`) + `playwright-cli`. Yani npm kurulumu,
config yazımı ve duman testi aXet'in kısıtlı job'ı içinde de tamamlandı.

Normal kabukta (aXet dışında) aynı betik: 1. koşu `kuruldu · global config yazıldı · duman testi geçti` (27 sn);
2. koşu `zaten kurulu · zaten uygun · duman testi geçti` (16 sn) ve `find -newer` ile **hiçbir dosya değişmedi**;
`%LOCALAPPDATA%\ms-playwright\` listesi değişmedi (tarayıcı indirilmedi; npm'e `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`).

## Kaynaktan (ÖLÇÜLMEDİ) — proje dosyası ile global dosyanın birleşimi

`mergeConfig` (`coreBundle.js`) `launchOptions`'ı **sığ** birleştirir (`{...global.launchOptions, ...proje.launchOptions}`):
proje dosyasında `args` yazılıysa global `args` (dolayısıyla `--no-sandbox`) **tamamen ezilir**; proje dosyasında
yalnız `channel` varsa global `args` kalır. aXet'te bu birleşim ölçülmedi; belgeler bu yüzden "proje dosyasında
`args` varsa `--no-sandbox` orada da olmalı" der.

## Sınırlar / ÖLÇÜLMEDİ

- Kontrol grubunun süreç komut satırı (tarama kalıbı hatası; yukarıda).
- Edge'in merkezi kurulum + global config ile aXet'te açılması (Z56'da proje config'iyle ölçülmüştü).
- Gerçek `USERPROFILE` altındaki `~/.playwright` ile aXet koşumu (gerçek dosyaya dokunmama kuralı); eşdeğerlik kaynak +
  normal kabuk `USERPROFILE` ölçümüne dayanır.
- Etkileşimli TUI; proxy'li/ağsız makinede npm davranışı (birim testte sahte süreçle); aXet bash aracının uzun npm
  kurulumunda zaman aşımı (ölçülen kurulum 10–30 sn).
- `%guncelle` akışının tamamı içinde adım 16 (akışın kendisi koşulmadı; betik aXet içinden tek başına koşuldu).

## Temizlik

Tüm playwright oturumları `close` ile kapandı; lab dizinleri `scratchpad/z60/` altında kaldı. Gerçek `~/.playwright`
oluşturulmadı. `%LOCALAPPDATA%\ms-playwright\` değişmedi (`msp-once.txt` ile karşılaştırıldı).
