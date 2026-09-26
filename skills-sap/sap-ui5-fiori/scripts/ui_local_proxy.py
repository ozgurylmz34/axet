#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_local_proxy.py — UI5 uygulamasını YERELDE canlı OData ile test etmek için SALT-OKUR sunucu (Z144).

Derlenmiş `dist/`'i (ya da `--kok` ile verilen klasörü) sunar; `/sap/*` isteklerini SAP'ye iletir, AMA yalnız okumayı:
  GET / HEAD                          → iletilir
  POST …/$batch  (changeset YOK)      → iletilir (UI5 V2 model okumaları batch'ler)
  POST …/$batch  (changeset VAR)      → 403, SAP'ye GİTMEZ (changeset = yazma)
  diğer her POST / PUT / MERGE / PATCH / DELETE → 403, SAP'ye GİTMEZ
Reddedilen her istek konsola `REDDEDİLDİ` satırıyla yazılır. Amaç: değişikliği SAP'ye YAZMADAN, deploy ÖNCESİ,
gerçek veriyle kullanıcıya göstermek (kaydet/sil düğmeleri bu modda 403 alır — beklenen davranıştır).

Kullanım:
  python ui_local_proxy.py <app_klasoru> [--port 8484] [--kok <sunulacak klasör>] [--url URL --client NNN] [--ignore-cert]
Hedef: --url/--client verilmezse `<app>/ui5-deploy.yaml` target.url/client. Kimlik: env FIORI_TOOLS_USER /
FIORI_TOOLS_PASSWORD (basılmaz, dosyadan okunmaz). Yalnız 127.0.0.1'e bağlanır.
Durdurma: Ctrl+C (ya da PID ile — references/deploy-and-local-run.md §1).
Çıkış: 2 = başlatılamadı (klasör / hedef / kimlik yok).
"""
from __future__ import annotations

import argparse
import base64
import http.server
import socketserver
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bspnet as B  # noqa: E402

GECEN_ISTEK = ("accept", "accept-language", "content-type", "cookie", "x-csrf-token", "maxdataserviceversion",
               "dataserviceversion", "x-requested-with", "sap-contextid-accept")
ATLANAN_YANIT = {"transfer-encoding", "connection", "content-encoding", "content-length", "strict-transport-security"}
YAZMA_YONTEMLERI = ("PUT", "MERGE", "PATCH", "DELETE")


def izin_ver(yontem: str, yol: str, govde: bytes = b"") -> tuple[bool, str]:
    """SAP'ye iletilecek istek SALT-OKUMA mı? → (izin, neden). Saf fonksiyon (testlenir)."""
    yontem = yontem.upper()
    if yontem in ("GET", "HEAD"):
        return True, "okuma"
    if yontem == "POST":
        if not urllib.parse.urlsplit(yol).path.endswith("/$batch"):
            return False, "yalnız $batch POST'u iletilir (function import / create = yazma olabilir)"
        if b"changeset" in (govde or b"").lower():
            return False, "$batch içinde changeset (yazma) var"
        return True, "okuma batch'i"
    return False, f"{yontem} yazmadır"


def isleyici_sinifi(kok: Path, taban: str, client: str, kimlik: tuple[str, str], ctx):
    auth = "Basic " + base64.b64encode(f"{kimlik[0]}:{kimlik[1]}".encode()).decode()

    class Isleyici(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(kok), **k)

        def log_message(self, fmt, *args):
            if self.path.startswith("/sap/"):
                print(f"{self.command} {self.path[:150]} → {args[1] if len(args) > 1 else ''}", flush=True)

        def _ilet(self, govde: bytes | None = None):
            ayrik = urllib.parse.urlsplit(self.path)
            q = urllib.parse.parse_qsl(ayrik.query, keep_blank_values=True)
            if client and not any(k == "sap-client" for k, _ in q):
                q.append(("sap-client", client))
            url = f"{taban}{ayrik.path}" + ("?" + urllib.parse.urlencode(q, safe="'$,()") if q else "")
            h = {k: v for k, v in self.headers.items() if k.lower() in GECEN_ISTEK}
            h["Authorization"] = auth
            h["Accept-Encoding"] = "identity"
            req = urllib.request.Request(url, data=govde, headers=h, method=self.command)
            try:
                r = urllib.request.urlopen(req, context=ctx, timeout=120)
            except urllib.error.HTTPError as e:
                r = e
            except Exception as exc:  # noqa: BLE001 — SAP'ye ulaşılamadı
                return self._yanit(502, f"SAP'ye ulasilamadi: {type(exc).__name__}")
            veri = r.read()
            self.send_response(getattr(r, "status", None) or r.code)
            for k, v in r.headers.items():
                if k.lower() in ATLANAN_YANIT:
                    continue
                if k.lower() == "set-cookie":  # çerez localhost'a yazılsın
                    v = ";".join(p for p in v.split(";")
                                 if p.strip().lower().split("=")[0] not in ("domain", "secure", "samesite"))
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(veri)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(veri)

        def _yanit(self, kod: int, metin: str):
            self.send_response(kod)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            veri = metin.encode("utf-8")
            self.send_header("Content-Length", str(len(veri)))
            self.end_headers()
            self.wfile.write(veri)

        def _karar(self, govde: bytes = b""):
            if not self.path.startswith("/sap/"):
                if self.command in ("GET", "HEAD"):
                    return super().do_GET() if self.command == "GET" else super().do_HEAD()
                return self._yanit(405, "yerel dosya sunucusu yalniz GET/HEAD")
            izin, neden = izin_ver(self.command, self.path, govde)
            if not izin:
                print(f"REDDEDİLDİ {self.command} {self.path[:150]} — {neden}", flush=True)
                return self._yanit(403, f"Salt-okur yerel test sunucusu yazma istegini reddetti: {neden}")
            return self._ilet(govde if self.command == "POST" else None)

        def do_GET(self):  # noqa: N802
            self._karar()

        def do_HEAD(self):  # noqa: N802
            self._karar()

        def do_POST(self):  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            self._karar(self.rfile.read(n) if n else b"")

        def do_PUT(self):  # noqa: N802
            self._karar()

        def do_MERGE(self):  # noqa: N802
            self._karar()

        def do_PATCH(self):  # noqa: N802
            self._karar()

        def do_DELETE(self):  # noqa: N802
            self._karar()

    return Isleyici


class Sunucu(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Salt-okur yerel UI5 test sunucusu (yazma istekleri 403)")
    ap.add_argument("app")
    ap.add_argument("--port", type=int, default=8484)
    ap.add_argument("--kok", help="sunulacak klasör (varsayılan <app>/dist)")
    ap.add_argument("--url")
    ap.add_argument("--client")
    ap.add_argument("--ignore-cert", action="store_true")
    a = ap.parse_args()
    app = Path(a.app)
    kok = Path(a.kok) if a.kok else app / "dist"
    if not (kok / "index.html").is_file():
        print(f"[FAIL] {kok}/index.html yok — önce build (`npm run build`) ya da --kok ver (exit 2)")
        return 2
    ayar = B.deploy_ayari(app) or {}
    taban = (a.url or ayar.get("url") or "").rstrip("/")
    client = a.client if a.client is not None else ayar.get("client", "")
    if not taban:
        print("[FAIL] hedef yok — --url ver ya da ui5-deploy.yaml target.url doldur (exit 2)")
        return 2
    kimlik = B.env_kimlik()
    if not kimlik:
        print(f"[FAIL] env {B.ENV_KULLANICI}/{B.ENV_PAROLA} set değil (exit 2)")
        return 2
    ctx = ssl.create_default_context()
    if a.ignore_cert:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    print(f"YEREL-SUNUCU (SALT-OKUR) http://localhost:{a.port}/index.html · kök {kok} · yazma istekleri 403",
          flush=True)
    Sunucu(("127.0.0.1", a.port), isleyici_sinifi(kok.resolve(), taban, client, kimlik, ctx)).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
