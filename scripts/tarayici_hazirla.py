#!/usr/bin/env python3
"""aXet.code tarayıcı testini KULLANICI KOMUT ÇALIŞTIRMADAN hazırlar (v0.5.4, Z60).

Kullanım:
  python scripts/tarayici_hazirla.py            hazırla (idempotent; ikinci koşu hiçbir şey değiştirmez)
  python scripts/tarayici_hazirla.py --kok <d>  başka bir template kökü için (ölçüm/test)

Kim çağırır: `install.py` (taze kurulum ve yeniden kurulum) ve `%guncelle` akışının son adımı (GUNCELLE.md adım 16).
Kullanıcıya soru SORMAZ ve çağıranı ASLA durdurmaz: her durumda çıkış 0; durumu ilk satır söyler:
  TARAYICI: HAZIR — …     duman testi geçti
  TARAYICI: ATLANDI — …   ön koşul yok (kurulu Chrome/Edge yok · node/npm yok · paylaşılan modül yok · kapalı)
  TARAYICI: EKSİK — …     denendi ama bitmedi (npm install başarısız · duman testi düştü)
Çıkış 2 yalnız kullanım hatasında.

Yaptığı (yalnız bunlar; iki onaylı yazma yeri):
  1. Kurulu Chrome'u (yoksa Edge'i) bulur — tarayıcı İNDİRMEZ (npm'e PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 verilir).
  2. `<kök>/.araclar/playwright-cli` içine `@playwright/cli@<sabit sürüm>` kurar (zaten o sürümse dokunmaz). Dizine
     `*` içeren bir `.gitignore` koyar: kök `.gitignore` eski olsa bile node_modules klonun git durumuna girmez.
  3. `~/.playwright/cli.config.json` (playwright-cli'nin GLOBAL config'i; proje dosyası yokken tek başına, varken
     altına birleşir) yoksa `{"channel": <bulunan>, "args": ["--no-sandbox"]}` yazar · zaten chrome/msedge'e sabit ve
     `--no-sandbox`'lıysa dokunmaz · kanal uygun ama yalnız `--no-sandbox` eksikse yalnız onu ekler · başka her
     içerikte EZMEZ (raporlar). Karar ve ekleme `kd_ortam.py`'nin fonksiyonlarıdır (paylaşılır, kopyalanmaz).
  4. Duman testi: geçici bir dizinde `open data:…` → `snapshot` (rastgele işaret sayfada görünmeli) → `close`.

Neden `--no-sandbox` (ölçüldü 2026-09-22, aXet.code 1.3.0, playwright-cli 0.1.21): aXet'in bash'inde config'siz
`open` "Target crashed"/"Session closed" ile düştü; global config'teki `--no-sandbox` ile açıldı ve süreç komut
satırında göründü (maintenance/degerlendirme/2026-09-22-z60-tarayici-hazirligi-olcumu.md). Süreç izolasyonunu kapatır:
yalnız yerel/güvenilir sayfa.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AXET_HOME = Path(__file__).resolve().parents[1]
KD_ORTAM_GORELI = Path("skills-sap") / "sap-ui5-user-guide" / "scripts" / "kd_ortam.py"
ARAC_GORELI = Path(".araclar") / "playwright-cli"
CLI_JS_GORELI = Path("node_modules") / "@playwright" / "cli" / "playwright-cli.js"
KAPAT_ORTAM = "AXET_TARAYICI_HAZIRLA"  # "0" → hiçbir şey yapmadan ATLANDI (testler ve istemeyen kullanıcı için)
NPM_ZAMAN = 600
DUMAN_ZAMAN = 120

KAPSAM = ("KAPSAM (SCOPE): tarayici_hazirla — bakılanlar: kurulu Chrome/Edge yürütülebilir dosyası (bilinen kurulum "
          "yerleri), node sürümü ve npm'in PATH'te olması, <kök>/.araclar/playwright-cli'deki @playwright/cli sürümü, "
          "~/.playwright/cli.config.json'un chrome/msedge kanalına sabit ve --no-sandbox'lı olması, PLAYWRIGHT_MCP_* "
          "ortam değişkenleri (yalnız uyarı), bu kabukta data: sayfasıyla open→snapshot→close. Bakılmayanlar: aXet "
          "bash'indeki davranış (yalnız bu betik aXet içinden koşuyorsa ölçülür), projelerdeki "
          "`.playwright/cli.config.json` (global dosyanın ÜSTÜNE birleşir; launchOptions sığ birleştiği için orada "
          "`args` yazılıysa global `--no-sandbox`'ı EZER), HTTP sunucusu, UI5 uygulaması, npm proxy ayarları.")


# --------------------------------------------------------------------------- yardımcılar

def kd_yukle(kok: Path):
    """Paylaşılan yapılandırma mantığı (`kd_ortam.py`). Yüklenemezse istisna."""
    yol = kok / KD_ORTAM_GORELI
    spec = importlib.util.spec_from_file_location("kd_ortam_paylasilan", yol)
    if spec is None or spec.loader is None or not yol.is_file():
        raise FileNotFoundError(str(yol))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for ad in ("config_durumu", "sandbox_ekle", "hedef_config", "_yaz", "global_ev", "chrome_yolu", "node_durumu",
               "_node_major", "ortam_uyarilari", "PLAYWRIGHT_CLI_SURUM", "KANALLAR", "NODE_ASGARI"):
        if not hasattr(mod, ad):
            raise AttributeError(f"{yol}: '{ad}' yok (eski sürüm?)")
    return mod


def arac_dizini(kok: Path) -> Path:
    return kok / ARAC_GORELI


def cli_js(kok: Path) -> Path:
    return arac_dizini(kok) / CLI_JS_GORELI


def pw_komutu(kok: Path) -> str:
    """aXet bash'inde çalışan biçim: `C:/…` (ileri bölülü Windows yolu). `/c/…` biçimi aXet bash'inde node'a
    `C:\\c\\…` olarak gitti → MODULE_NOT_FOUND (ölçüldü 2026-09-22)."""
    return 'node "%s"' % cli_js(kok).as_posix()


def kurulu_surum(kok: Path) -> str | None:
    paket = arac_dizini(kok) / "node_modules" / "@playwright" / "cli" / "package.json"
    try:
        return json.loads(paket.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None


def edge_yolu(env=None) -> str | None:
    env = os.environ if env is None else env
    if os.name == "nt":
        for on in (env.get("PROGRAMFILES(X86)"), env.get("PROGRAMFILES"), env.get("LOCALAPPDATA")):
            if on:
                aday = os.path.join(on, "Microsoft", "Edge", "Application", "msedge.exe")
                if os.path.isfile(aday):
                    return aday
        return None
    for aday in ("/opt/microsoft/msedge/msedge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
        if os.path.isfile(aday):
            return aday
    return shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")


def tarayici_sec(kd, env=None) -> tuple[str | None, str | None]:
    """Önce Chrome (kd_ortam'ın varsayılan kanalı), yoksa Edge."""
    yol = kd.chrome_yolu(env)
    if yol:
        return "chrome", yol
    yol = edge_yolu(env)
    return ("msedge", yol) if yol else (None, None)


def global_durum(kd, env=None) -> tuple[str, str, str | None, str | None]:
    """(durum, yol, ham, kanal). durum: 'uygun' | 'eksik-sandbox' | 'yok' | 'farkli' | 'bozuk' (kd_ortam.config_durumu)."""
    ev = kd.global_ev(env)
    durum, yol, ham = "yok", os.path.join(ev, ".playwright", "cli.config.json"), None
    for kanal in kd.KANALLAR:
        durum, yol, ham = kd.config_durumu(ev, kanal, True)
        if durum in ("uygun", "eksik-sandbox"):
            return durum, yol, ham, kanal
    return durum, yol, ham, None


def _son_satir(metin: str | None) -> str:
    satirlar = [s.strip() for s in (metin or "").splitlines() if s.strip()]
    return satirlar[-1][:200] if satirlar else "çıktı yok"


def _hata_satiri(metin: str | None) -> str:
    """playwright-cli hatasında anlamlı satır: 'Error:' ile başlayan ilk satır, yoksa son satır."""
    for s in (metin or "").splitlines():
        if s.strip().startswith("Error:"):
            return s.strip()[:200]
    return _son_satir(metin)


# --------------------------------------------------------------------------- adımlar

def npm_kur(kok: Path, npm: str, surum: str, env: dict, calistir=subprocess.run) -> tuple[bool, str]:
    dizin = arac_dizini(kok)
    dizin.mkdir(parents=True, exist_ok=True)
    gi = dizin.parent / ".gitignore"
    if not gi.exists():
        gi.write_text("# tarayici_hazirla.py: merkezi araç kurulumu, repoya girmez\n*\n", encoding="utf-8")
    npm_env = dict(env, PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1", NO_UPDATE_NOTIFIER="1")
    komut = [npm, "install", "--prefix", str(dizin), "--no-audit", "--no-fund", "--loglevel=error",
             "@playwright/cli@%s" % surum]
    try:
        r = calistir(komut, capture_output=True, text=True, encoding="utf-8", errors="replace", env=npm_env,
                     stdin=subprocess.DEVNULL, timeout=NPM_ZAMAN)
    except subprocess.TimeoutExpired:
        return False, "npm install %d sn'de bitmedi (ağ/proxy?)" % NPM_ZAMAN
    except OSError as exc:
        return False, "npm çalıştırılamadı: %s" % exc
    if r.returncode != 0:
        return False, "npm install başarısız (rc=%s): %s — ağ/proxy?" % (r.returncode, _son_satir(r.stderr or r.stdout))
    yeni = kurulu_surum(kok)
    if yeni != surum:
        return False, "npm install rc=0 ama kurulu sürüm %s (beklenen %s)" % (yeni or "YOK", surum)
    return True, "playwright-cli %s kuruldu" % surum


def config_hazirla(kd, kanal: str, env=None) -> tuple[str, str]:
    """(etiket, metin). etiket: 'yazildi' | 'eklendi' | 'uygun' | 'dokunulmadi' | 'hata'.
    'hata' = yazım başarısız (salt-okunur, yol dizin, izin): kd._yaz/sandbox_ekle hata metni döner (Z59); o zaman
    "yazıldı/eklendi" DENMEZ. İstisna fırlatılmaz — çağıran (install/%guncelle) durmaz."""
    durum, yol, ham, bulunan = global_durum(kd, env)
    if durum == "uygun":
        return "uygun", "global config zaten uygun (%s, kanal %s)" % (yol, bulunan)
    if durum == "eksik-sandbox":
        hata = kd.sandbox_ekle(yol, ham)
        if hata:
            return "hata", "global config yazılamadı: %s" % hata
        return "eklendi", "global config'e --no-sandbox eklendi (%s; diğer anahtarlara dokunulmadı)" % yol
    if durum == "yok":
        hata = kd._yaz(yol, kd.hedef_config(kanal, True))
        if hata:
            return "hata", "global config yazılamadı: %s" % hata
        return "yazildi", "global config yazıldı (%s, kanal %s · --no-sandbox)" % (yol, kanal)
    return "dokunulmadi", ("global config %s (%s) — EZİLMEDİ; aXet'te `open` için launchOptions'ta chrome/msedge kanalı "
                           "ve args'ta --no-sandbox gerekir" % ("JSON değil" if durum == "bozuk" else "farklı içerikli",
                                                                 yol))


def duman_testi(kok: Path, node: str, env: dict, calistir=subprocess.run) -> tuple[bool, str]:
    isaret = "AXET-HAZIRLIK-" + secrets.token_hex(4)
    oturum = "axet-hazirlik-%d" % os.getpid()
    cwd = tempfile.mkdtemp(prefix="axet-tarayici-")
    duman_env = dict(env, NO_UPDATE_NOTIFIER="1")
    temel = [node, str(cli_js(kok)), "-s=" + oturum]

    def kos(*args):
        return calistir(temel + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env=duman_env, cwd=cwd, stdin=subprocess.DEVNULL, timeout=DUMAN_ZAMAN)
    try:
        try:
            r = kos("open", "data:text/html,<h1>%s</h1>" % isaret)
            if r.returncode != 0:
                return False, "duman testi: open rc=%s — %s" % (r.returncode, _hata_satiri(r.stdout + (r.stderr or "")))
            r = kos("snapshot")
            if r.returncode != 0 or isaret not in (r.stdout or ""):
                return False, "duman testi: snapshot rc=%s, işaret %s — %s" % (
                    r.returncode, "YOK" if isaret not in (r.stdout or "") else "var",
                    _hata_satiri(r.stdout + (r.stderr or "")))
            return True, "duman testi geçti (open → snapshot'ta işaret → close)"
        finally:
            try:
                kos("close")
            except Exception:  # noqa: BLE001 — kapanış hatası sonucu değiştirmez
                pass
    except subprocess.TimeoutExpired:
        return False, "duman testi %d sn'de bitmedi" % DUMAN_ZAMAN
    except OSError as exc:
        return False, "duman testi çalıştırılamadı: %s" % exc
    finally:
        shutil.rmtree(cwd, ignore_errors=True)


# --------------------------------------------------------------------------- akış

def hazirla(kok: Path, env: dict | None = None, calistir=subprocess.run, which=shutil.which) -> tuple[str, list[str]]:
    """(durum, parçalar). durum: 'HAZIR' | 'ATLANDI' | 'EKSİK'. Yan etki yalnız iki onaylı yerde."""
    env = dict(os.environ) if env is None else env
    if env.get(KAPAT_ORTAM) == "0":
        return "ATLANDI", ["%s=0 (tarayıcı hazırlığı kapalı)" % KAPAT_ORTAM]
    try:
        kd = kd_yukle(kok)
    except Exception as exc:  # noqa: BLE001 — teşhis
        return "ATLANDI", ["paylaşılan yapılandırma modülü yüklenemedi (%s)" % exc]
    kanal, tarayici = tarayici_sec(kd, env)
    if not kanal:
        return "ATLANDI", ["kurulu Chrome/Edge yok (tarayıcı İNDİRİLMEZ; sistem kurulumu gerekir)"]
    parca = ["%s (%s)" % (kanal, tarayici)]
    node, surum_metni = kd.node_durumu()
    npm = which("npm")
    if not node or not npm:
        return "ATLANDI", parca + ["%s PATH'te yok" % ("node" if not node else "npm")]
    major = kd._node_major(surum_metni)
    if major is not None and major < kd.NODE_ASGARI:
        return "ATLANDI", parca + ["node %s < %d" % (surum_metni, kd.NODE_ASGARI)]
    surum = kd.PLAYWRIGHT_CLI_SURUM
    if kurulu_surum(kok) == surum:
        parca.append("playwright-cli %s zaten kurulu" % surum)
    else:
        ok, metin = npm_kur(kok, npm, surum, env, calistir)
        parca.append(metin)
        if not ok:
            return "EKSİK", parca
    etiket, metin = config_hazirla(kd, kanal, env)
    parca.append(metin)
    if etiket == "hata":  # --no-sandbox'sız aXet bash'inde `open` düşer (ölçüldü) → duman testi anlamsız
        return "EKSİK", parca
    parca += ["UYARI: " + u for u in kd.ortam_uyarilari(env)]
    ok, metin = duman_testi(kok, node, env, calistir)
    parca.append(metin)
    return ("HAZIR" if ok else "EKSİK"), parca


def durum_oku(kok: Path, env: dict | None = None) -> tuple[bool, str]:
    """doctor için SALT-OKUNUR özet (hiçbir şey kurmaz/yazmaz, duman testi koşmaz)."""
    env = dict(os.environ) if env is None else env
    try:
        kd = kd_yukle(kok)
    except Exception as exc:  # noqa: BLE001
        return False, "paylaşılan modül yüklenemedi (%s)" % exc
    eksik = []
    kanal, _ = tarayici_sec(kd, env)
    if not kanal:
        eksik.append("kurulu Chrome/Edge yok")
    surum = kurulu_surum(kok)
    if surum != kd.PLAYWRIGHT_CLI_SURUM:
        eksik.append("playwright-cli %s (beklenen %s, %s)" % (surum or "YOK", kd.PLAYWRIGHT_CLI_SURUM, arac_dizini(kok)))
    durum, yol, _, bulunan = global_durum(kd, env)
    if durum != "uygun":
        eksik.append("global config %s (%s)" % ({"yok": "YOK", "eksik-sandbox": "--no-sandbox eksik",
                                                  "bozuk": "JSON değil"}.get(durum, "farklı içerikli"), yol))
    if eksik:
        return False, "; ".join(eksik)
    return True, "kanal %s · playwright-cli %s · %s" % (bulunan, surum, pw_komutu(kok))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="aXet tarayıcı testini hazırlar (idempotent; çıkış daima 0)")
    ap.add_argument("--kok", help="template kökü (varsayılan: bu betiğin klonu)")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    kok = Path(a.kok).resolve() if a.kok else AXET_HOME
    try:
        durum, parcalar = hazirla(kok)
    except Exception as exc:  # noqa: BLE001 — çağıranı (install/guncelle) ASLA durdurma
        durum, parcalar = "EKSİK", ["beklenmeyen hata: %s: %s" % (type(exc).__name__, exc)]
    print("TARAYICI: %s — %s" % (durum, " · ".join(parcalar)))
    if durum == "HAZIR":
        print("KOMUT: %s -s=<oturum> open <url>   (global config geçerli; projede .playwright gerekmez)"
              % pw_komutu(kok))
    print(KAPSAM)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
