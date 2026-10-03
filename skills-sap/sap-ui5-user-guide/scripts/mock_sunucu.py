# -*- coding: utf-8 -*-
"""Mock sunucusunu (fe-mockserver, `npm run start-mock`) aXet'in arka plan işinden BAĞIMSIZ başlatır / durdurur (Z181).

Neden: aXet sunucuyu kendi arka plan işi olarak başlatınca Windows'ta `npm → cmd → fiori → npx → ui5 serve` zinciri
oluşur; `job_kill` yalnız en üst süreci öldürür, alttaki `node` süreçleri aXet'in çıktı borusunu açık tuttuğu için
motor "iş bitsin" diye SONSUZA DEK bekler (ölçüldü 2026-10-03: log her 5 sn "BgJob kill still waiting…", Esc de
çözmedi; 2026-09-25: süreç yaşadı, port dolu kaldı). Bu araç sunucuyu ayrı süreç grubunda, çıktısı DOSYAYA yönlenmiş
başlatır ve HAZIR olunca döner ⇒ aXet'in tuttuğu boru yoktur; durdurma süreç AĞACINI ve kayıtlı alt süreçleri kapatır.

Kullanım (aXet'te ÖN PLANDA koş — `run_in_background` YOK):
    python mock_sunucu.py baslat [--app <uygulama>] [--port N] [--zaman-asimi 90]
    python mock_sunucu.py durum  [--app <uygulama>]
    python mock_sunucu.py durdur [--app <uygulama>]
    python mock_sunucu.py yenile [--app <uygulama>] [--port N]     durdur + baslat (mock veri değişince)

Durum dosyası ve log uygulamaya YAZILMAZ: `<TEMP>/axet-mock/<anahtar>.json|.log` (anahtar = uygulama yolu özeti).
Çıkış: 0 tamam · 1 durdurulamadı / port hâlâ dolu · 2 başlamadı / ölçüm yok (log kuyruğu basılır).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

PENCERE = os.name == "nt"
URL_DESENI = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[::1\]|0\.0\.0\.0):(\d{2,5})")
KAPSAM = ("KAPSAM (SCOPE): mock_sunucu — bakılanlar: süreç canlılığı (PID + oluşturma zamanı), portun dinlenmesi, "
          "`/index.html` HTTP durumu, durdurmada portun boşalması. Bakılmayanlar: UI5 bootstrap ve `tr.json` (mock-ortam "
          "§5 ölçümü ayrıca yapılır), OData yanıtlarının doğruluğu, başkasının başlattığı sunucular (yalnız bu aracın "
          "kayıtlı süreçleri kapatılır).")


def _cikti_utf8():
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def kayit_yollari(app: str) -> tuple[str, str]:
    anahtar = hashlib.sha1(os.path.normcase(os.path.abspath(app)).encode("utf-8")).hexdigest()[:12]
    dizin = os.path.join(tempfile.gettempdir(), "axet-mock")
    os.makedirs(dizin, exist_ok=True)
    return os.path.join(dizin, anahtar + ".json"), os.path.join(dizin, anahtar + ".log")


def kayit_oku(app: str):
    yol, _ = kayit_yollari(app)
    try:
        with open(yol, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def kayit_yaz(app: str, veri) -> None:
    yol, _ = kayit_yollari(app)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as fh:
        json.dump(veri, fh, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)


def kayit_sil(app: str) -> None:
    yol, _ = kayit_yollari(app)
    try:
        os.remove(yol)
    except OSError:
        pass


def port_dinleniyor(port: int) -> bool:
    for aile, adres in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(aile, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex((adres, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def http_durum(port: int, yol: str = "/index.html") -> int | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{yol}", timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:  # noqa: BLE001
        return None


# ───────────────────────── süreç tablosu (Windows: CIM · POSIX: ps) ─────────────────────────

def surec_tablosu() -> dict[int, dict]:
    """{pid: {"ebeveyn": ppid, "zaman": oluşturma, "komut": komut satırı}} — ölçülemezse {}."""
    try:
        if PENCERE:
            betik = ("Get-CimInstance Win32_Process | ForEach-Object { [pscustomobject]@{p=$_.ProcessId;"
                     "e=$_.ParentProcessId;z=[string]$_.CreationDate.Ticks;k=$_.CommandLine} } | ConvertTo-Json -Compress")
            o = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", betik],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                               stdin=subprocess.DEVNULL).stdout
            veri = json.loads(o or "[]")
            veri = veri if isinstance(veri, list) else [veri]
            return {int(x["p"]): {"ebeveyn": int(x["e"] or 0), "zaman": x.get("z") or "", "komut": x.get("k") or ""}
                    for x in veri}
        o = subprocess.run(["ps", "-eo", "pid=,ppid=,lstart=,args="], capture_output=True, text=True, timeout=30).stdout
        tablo = {}
        for satir in o.splitlines():
            parca = satir.split(None, 7)
            if len(parca) >= 7:
                tablo[int(parca[0])] = {"ebeveyn": int(parca[1]), "zaman": " ".join(parca[2:7]),
                                        "komut": parca[7] if len(parca) > 7 else ""}
        return tablo
    except Exception:  # noqa: BLE001
        return {}


def port_sahibi(port: int) -> int | None:
    """Portu DİNLEYEN sürecin PID'i (Windows `netstat -ano`; POSIX'te ölçülmez → None). Ağaç kopuksa (ara süreç
    kapanmış, sunucu yetim kalmış) kök ağacından bulunamayan sunucuyu bu yakalar."""
    if not PENCERE:
        return None
    try:
        o = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, errors="replace",
                           timeout=30, stdin=subprocess.DEVNULL).stdout
    except Exception:  # noqa: BLE001
        return None
    for satir in o.splitlines():
        parca = satir.split()
        if len(parca) >= 5 and parca[0].upper() == "TCP" and parca[1].endswith(f":{port}") and parca[3].upper() == "LISTENING":
            try:
                return int(parca[4])
            except ValueError:
                return None
    return None


def torunlar(kok: int, tablo: dict[int, dict]) -> list[int]:
    cocuklar: dict[int, list[int]] = {}
    for pid, b in tablo.items():
        cocuklar.setdefault(b["ebeveyn"], []).append(pid)
    sonuc, yigin = [], [kok]
    while yigin:
        p = yigin.pop()
        for c in cocuklar.get(p, []):
            if c not in sonuc and c != kok:
                sonuc.append(c)
                yigin.append(c)
    return sonuc


def canli(kayit_pid: int, zaman: str, tablo: dict[int, dict]) -> bool:
    """PID hâlâ AYNI süreç mi (PID yeniden kullanılmış olabilir → oluşturma zamanı da eşleşmeli)."""
    b = tablo.get(kayit_pid)
    return bool(b) and (not zaman or b["zaman"] == zaman)


# ───────────────────────── komutlar ─────────────────────────

def _baslat_komutu(port: int | None) -> list[str]:
    npm = "npm.cmd" if PENCERE else "npm"
    argv = [npm, "run", "start-mock"]
    if port:
        argv += ["--", "--port", str(port)]
    return argv


def _log_kuyrugu(log: str, n: int = 15) -> str:
    try:
        with open(log, encoding="utf-8", errors="replace") as fh:
            return "".join(fh.readlines()[-n:])
    except OSError:
        return "(log okunamadı)"


def baslat(app: str, port: int | None, zaman_asimi: float, komut: list[str] | None = None) -> int:
    app = os.path.abspath(app)
    onceki = kayit_oku(app)
    if onceki:
        tablo = surec_tablosu()
        if canli(onceki["pid"], onceki.get("zaman", ""), tablo) and port_dinleniyor(onceki["port"]):
            print(f"MOCK SUNUCU: ZATEN ÇALIŞIYOR · http://127.0.0.1:{onceki['port']}/index.html?sap-ui-language=tr "
                  f"· PID {onceki['pid']} · log {onceki['log']}")
            print(KAPSAM)
            return 0
        kayit_sil(app)
    if port and port_dinleniyor(port):
        print(f"[FAIL] port {port} zaten dolu (başka bir sunucu) — başka --port ver ya da onu kapat; başlatılmadı")
        return 2
    _, log = kayit_yollari(app)
    argv = komut or _baslat_komutu(port)
    bayrak = 0
    if PENCERE:
        bayrak = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    t0 = time.monotonic()
    with open(log, "w", encoding="utf-8") as fh:
        try:
            p = subprocess.Popen(argv, cwd=app, stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT,
                                 close_fds=True, creationflags=bayrak, start_new_session=not PENCERE)
        except OSError as exc:
            print(f"[FAIL] başlatılamadı ({type(exc).__name__}: {exc}) — komut: {' '.join(argv)}")
            return 2
    bulunan = None
    while time.monotonic() - t0 < zaman_asimi:
        if p.poll() is not None:
            # Kök kapandı ama başlattığı alt süreçler yaşıyor olabilir (Windows'ta ebeveyn PID'i kayıtlı kalır) —
            # yetim bırakılmaz; bu PID'ler kökten doğduğu için başkasının süreci değildir.
            artik = torunlar(p.pid, surec_tablosu())
            _oldur(artik, None)
            print(f"[FAIL] sunucu süreci kapandı (çıkış {p.returncode}; kapatılan alt süreç {len(artik)}) — log "
                  f"kuyruğu:\n{_log_kuyrugu(log)}")
            return 2
        if bulunan is None:
            m = URL_DESENI.search(_log_kuyrugu(log, 200))
            bulunan = int(m.group(1)) if m else (port if port and port_dinleniyor(port) else None)
        if bulunan and port_dinleniyor(bulunan) and http_durum(bulunan) is not None:
            break
        time.sleep(0.5)
    else:
        print(f"[FAIL] {int(zaman_asimi)} sn içinde hazır olmadı (port {'bulunamadı' if not bulunan else bulunan}) "
              f"— süreç ayakta bırakıldı, `durdur` ile kapat. Log kuyruğu:\n{_log_kuyrugu(log)}")
        kayit_yaz(app, {"pid": p.pid, "zaman": surec_tablosu().get(p.pid, {}).get("zaman", ""), "port": bulunan or 0,
                        "app": app, "log": log, "alt": []})
        return 2
    tablo = surec_tablosu()
    alt = [{"pid": c, "zaman": tablo[c]["zaman"]} for c in torunlar(p.pid, tablo)]
    sahip = port_sahibi(bulunan)
    if sahip and sahip != p.pid and sahip in tablo and all(a["pid"] != sahip for a in alt):
        alt.append({"pid": sahip, "zaman": tablo[sahip]["zaman"]})  # kopuk ağaç: portu tutan yetim sunucu
    kayit_yaz(app, {"pid": p.pid, "zaman": tablo.get(p.pid, {}).get("zaman", ""), "port": bulunan, "app": app,
                    "log": log, "alt": alt, "komut": argv})
    durum = http_durum(bulunan)
    print(f"MOCK SUNUCU: HAZIR · http://127.0.0.1:{bulunan}/index.html?sap-ui-language=tr · PID {p.pid} "
          f"(+{len(alt)} alt süreç) · {time.monotonic() - t0:.1f} sn · log {log}")
    if durum != 200:
        print(f"UYARI: /index.html → {durum} (200 bekleniyordu) — log'a bak")
    print(KAPSAM)
    return 0


def _oldur(pidler: list[int], kok: int | None) -> None:
    if PENCERE:
        if kok:
            subprocess.run(["taskkill", "/PID", str(kok), "/T", "/F"], capture_output=True, stdin=subprocess.DEVNULL)
        for pid in pidler:
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, stdin=subprocess.DEVNULL)
        return
    if kok:
        try:
            os.killpg(os.getpgid(kok), signal.SIGKILL)
        except OSError:
            pass
    for pid in pidler:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def durdur(app: str, bekle: float = 15) -> int:
    app = os.path.abspath(app)
    k = kayit_oku(app)
    if not k:
        print("MOCK SUNUCU: kayıt yok — bu araçla başlatılmış sunucu bulunamadı (başkasının sunucusu kapatılmaz)")
        print(KAPSAM)
        return 0
    tablo = surec_tablosu()
    if not tablo:
        print("[FAIL] süreç tablosu okunamadı — hiçbir süreç kapatılmadı (ÖLÇÜLEMEDİ)")
        return 2
    # Yalnız KAYITLI ve hâlâ AYNI olan süreçler (PID + oluşturma zamanı); ağaç kopmuşsa (ara `cmd` kapanmış) kayıtlı
    # alt süreçler ayrıca kapatılır — 2026-10-03 ölçümünde `ui5 serve`in ebeveyni kökün torunu DEĞİLDİ.
    kok = k["pid"] if canli(k["pid"], k.get("zaman", ""), tablo) else None
    alt = [a["pid"] for a in k.get("alt", []) if canli(a["pid"], a.get("zaman", ""), tablo)]
    if kok:
        alt += [c for c in torunlar(kok, tablo) if c not in alt]
    _oldur(alt, kok)
    t0 = time.monotonic()
    while time.monotonic() - t0 < bekle and k.get("port") and port_dinleniyor(k["port"]):
        time.sleep(0.5)
    if k.get("port") and port_dinleniyor(k["port"]):
        print(f"[FAIL] port {k['port']} hâlâ dinleniyor — kayıtlı süreçler kapatıldı ama portu başka bir süreç tutuyor "
              f"(`netstat -ano` ile PID'e bak; komut satırında bu uygulama yoksa o süreç senin değil)")
        return 1
    kayit_sil(app)
    print(f"MOCK SUNUCU: DURDU · kapatılan süreç {len(alt) + (1 if kok else 0)} · port {k.get('port')} boş")
    print(KAPSAM)
    return 0


def durum_goster(app: str) -> int:
    app = os.path.abspath(app)
    k = kayit_oku(app)
    if not k:
        print("MOCK SUNUCU: kayıt yok (çalışmıyor ya da bu araçla başlatılmadı)")
        return 0
    tablo = surec_tablosu()
    print(f"MOCK SUNUCU: {'ÇALIŞIYOR' if canli(k['pid'], k.get('zaman', ''), tablo) else 'süreç YOK'} · port "
          f"{k.get('port')} {'dinleniyor' if k.get('port') and port_dinleniyor(k['port']) else 'boş'} · PID {k['pid']} "
          f"· log {k.get('log')}")
    return 0


def main(argv=None) -> int:
    _cikti_utf8()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("komut", choices=["baslat", "durum", "durdur", "yenile"])
    ap.add_argument("--app", default=".", help="uygulama klasörü (package.json + ui5-mock.yaml; vars. bulunulan dizin)")
    ap.add_argument("--port", type=int, help="sabit port (vars. sunucunun seçtiği; log'dan okunur)")
    ap.add_argument("--zaman-asimi", type=float, default=90)
    ap.add_argument("--komut-json", help=argparse.SUPPRESS)  # testler: başlatılacak komut (JSON dizi)
    a = ap.parse_args(argv)
    if a.komut in ("baslat", "yenile") and not a.komut_json and not os.path.isfile(os.path.join(a.app, "package.json")):
        print(f"[FAIL] {os.path.abspath(a.app)} içinde package.json yok — --app uygulama klasörü olmalı")
        return 2
    komut = json.loads(a.komut_json) if a.komut_json else None
    if a.komut == "durum":
        return durum_goster(a.app)
    if a.komut == "durdur":
        return durdur(a.app)
    if a.komut == "yenile":
        rc = durdur(a.app)
        if rc:
            return rc
    return baslat(a.app, a.port, a.zaman_asimi, komut)


if __name__ == "__main__":
    sys.exit(main())
