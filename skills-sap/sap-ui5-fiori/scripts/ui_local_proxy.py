#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_local_proxy.py — UI5 uygulamasını YERELDE canlı OData ile test etmek için SALT-OKUR sunucu (Z144).

Derlenmiş `dist/`'i (ya da `--kok` ile verilen klasörü) sunar; `/sap/*` isteklerini SAP'ye iletir, AMA yalnız okumayı:
  GET / HEAD                          → iletilir
  POST /sap/opu/odata(4)/…/$batch     → iletilir YALNIZ şu durumda (PARÇA BAZLI beyaz liste; emin olunamayan → 403):
      TEK `Content-Type: multipart/mixed; boundary=…` başlığı (iletilen de bu değerdir) · gövde sınırla bölünür,
      ≥1 parça, HER parça `Content-Type: application/http` (+ varsa `binary` aktarım), katlanmamış başlık, ilk satırı
      tam olarak `GET <hedef> HTTP/1.1`, gövdesiz · satır sonu yalnız CRLF · BOM / kontrol baytı / ASCII dışı istek
      satırı YOK · prolog/epilog serbest metin (istek sayılmaz) · yolda `..;` / `.;` segmenti YOK
  başka yolda $batch (ör. /sap/bc/soap/…), diğer her POST / PUT / MERGE / PATCH / DELETE → 403, SAP'ye GİTMEZ
  Host başlığı localhost:<port> / 127.0.0.1:<port> değilse → 403 (DNS rebinding), SAP'ye GİTMEZ
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
import re
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


# $batch yalnız OData servis kökünde kabul edilir (V2 `/sap/opu/odata/…`, V4 `/sap/opu/odata4/…`). Başka bir ICF
# servisinin `…/$batch` adlı yolu (ör. SOAP RFC) okuma DEĞİLDİR. Segment karakterleri dar tutulur: `%` kodlaması,
# boş segment ve `;` öncesi `..`/`.` olan segment (`..;`, `.;` — matris parametresiyle gizlenmiş üst dizin) reddedilir
# (fail-closed — hedef sistemin yol normalleştirmesine güvenilmez).
_R_BATCH_YOLU = re.compile(r"/sap/opu/odata4?(?:/[A-Za-z0-9_;=,.\-]+)+/\$batch")
# RFC 2046 sınır karakterleri (boşluk hariç — fail-closed), 1-70 karakter.
_R_SINIR = re.compile(r"[0-9A-Za-z'()+_,\-./:=?]{1,70}")
# Parçanın gövdesinin İLK satırı tam olarak bu olmalı: GET + tek boşluk + boşluksuz yazdırılabilir ASCII hedef + HTTP/1.1.
_R_GET_SATIRI = re.compile(rb"GET [\x21-\x7e]+ HTTP/1\.1")
# Başlık satırı (MIME parça başlığı ya da iç istek başlığı): token ad + `:` + yazdırılabilir ASCII değer.
_R_BASLIK = re.compile(rb"([!#$%&'*+\-.^_`|~0-9A-Za-z]+)[ \t]*:([\x20-\x7e\t]*)")
# `\t \r \n` dışındaki kontrol baytları ve DEL: satır/parça tanımayı bozabilir (`DELETE\x0b…`, `\x0cDELETE…`).
_R_KONTROL = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def tek_icerik_tipi(degerler) -> str | None:
    """`Content-Type` başlığının TÜM değerleri → tam 1 değer varsa o, yoksa None (0 ya da çift başlık = red).
    Doğrulanan değer SAP'ye İLETİLEN değerin kendisidir (tek kaynak — çift başlıkta ilk/son farkı kapanır)."""
    degerler = list(degerler or [])
    return degerler[0] if len(degerler) == 1 else None


def sinir_al(icerik_tipi: str) -> str | None:
    """`multipart/mixed; boundary=<sınır>` → sınır; biçim dışı (başka tip, ek parametre, sınırsız, geçersiz) → None."""
    parcalar = [p.strip() for p in (icerik_tipi or "").split(";")]
    if parcalar[0].lower() != "multipart/mixed" or len(parcalar) != 2:
        return None
    ad, esit, deger = parcalar[1].partition("=")
    if not esit or ad.strip().lower() != "boundary":
        return None
    deger = deger.strip()
    if len(deger) >= 2 and deger[0] == deger[-1] == '"':
        deger = deger[1:-1]
    return deger if _R_SINIR.fullmatch(deger) else None


def _basliklar(satirlar: list[bytes]) -> tuple[list[tuple[bytes, bytes]] | None, int, str | None]:
    """Boş satıra kadar başlıklar → ([(küçük ad, değer)], boş satırın indeksi, hata). Devam satırı / biçim dışı → hata."""
    alanlar = []
    for i, s in enumerate(satirlar):
        if s == b"":
            return alanlar, i, None
        if s[:1] in (b" ", b"\t"):
            return None, i, "başlıkta devam (katlanmış) satırı"
        m = _R_BASLIK.fullmatch(s)
        if not m:
            return None, i, "geçersiz başlık satırı (biçim dışı ya da ASCII dışı)"
        ad, deger = m.group(1).lower(), m.group(2).strip()
        if ad.startswith(b"x-http-method"):
            return None, i, "X-HTTP-Method başlığı (yöntem ezme)"
        if b"multipart" in deger.lower():
            return None, i, "iç multipart (changeset biçimi)"
        alanlar.append((ad, deger))
    return None, len(satirlar), "başlık/gövde ayırıcı boş satır yok"


def _parca_denetle(satirlar: list[bytes]) -> str | None:
    """Tek batch parçası salt-okuma GET mi? → None (uygun) ya da red nedeni."""
    alanlar, bos, hata = _basliklar(satirlar)
    if hata:
        return f"parça: {hata}"
    tipler = [d.lower() for a, d in alanlar if a == b"content-type"]
    if tipler != [b"application/http"]:
        return "parça: Content-Type tam olarak bir kez application/http değil"
    aktarim = [d.lower() for a, d in alanlar if a == b"content-transfer-encoding"]
    if aktarim not in ([], [b"binary"]):
        return "parça: Content-Transfer-Encoding binary değil"
    istek = satirlar[bos + 1:]
    if not istek or not _R_GET_SATIRI.fullmatch(istek[0]):
        return "parça: ilk satır tam olarak `GET <hedef> HTTP/1.1` değil"
    _ic, ic_bos, hata = _basliklar(istek[1:])
    if hata:
        return f"parça isteği: {hata}"
    if any(s.strip() for s in istek[1 + ic_bos + 1:]):
        return "parça: GET isteğinde gövde var"
    return None


def batch_govde_denetle(govde: bytes, sinir: str) -> str | None:
    """multipart/mixed `$batch` gövdesi YALNIZ GET parçaları mı? → None (uygun) ya da red nedeni. Saf fonksiyon.

    Satır sonu yalnız CRLF (tek `\\r` ya da tek `\\n` → red: sunucunun satır bölmesiyle ayrışma riski). Prolog/epilog
    serbest metindir ve istek sayılmaz; ama içlerinde sınıra benzeyen satır olamaz, kapanıştan sonra sınır olamaz."""
    if not govde:
        return "boş gövde"
    if b"\xef\xbb\xbf" in govde or govde[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "gövdede BOM"
    if _R_KONTROL.search(govde):
        return "gövdede kontrol baytı (\\t \\r \\n dışında < 0x20 ya da 0x7f)"
    if re.search(rb"\r(?!\n)", govde) or re.search(rb"(?<!\r)\n", govde):
        return "satır sonu CRLF değil (tek \\r ya da tek \\n)"
    ayrac = b"--" + sinir.encode("ascii")
    kapanis = ayrac + b"--"
    durum, mevcut, parcalar = "prolog", [], []
    for s in govde.split(b"\r\n"):
        if s.startswith(ayrac):
            if durum == "epilog":
                return "kapanış sınırından sonra sınır satırı"
            if s == kapanis:
                if durum != "parca":
                    return "parçasız kapanış"
                parcalar.append(mevcut)
                durum = "epilog"
            elif s == ayrac:
                if durum == "parca":
                    parcalar.append(mevcut)
                durum, mevcut = "parca", []
            else:
                return "sınıra benzeyen ama sınır olmayan satır (doğrulanamaz)"
        elif durum == "parca":
            mevcut.append(s)
    if durum != "epilog":
        return "kapanış sınırı yok"
    for p in parcalar:
        neden = _parca_denetle(p)
        if neden:
            return neden
    return None


def izin_ver(yontem: str, yol: str, govde: bytes = b"", icerik_tipi: str | None = None) -> tuple[bool, str]:
    """SAP'ye iletilecek istek SALT-OKUMA mı? → (izin, neden). Saf fonksiyon (testlenir).

    `$batch` için kural PARÇA BAZLI BEYAZ LİSTEdir (emin olunamayan → red): yol OData servis kökü; istek tipi
    `multipart/mixed; boundary=…` (tek parametre); gövde sınırla parçalara bölünür, ≥1 parça, HER parça
    `Content-Type: application/http` + (varsa) `binary` aktarım + katlanmamış başlıklar + ilk satırı tam olarak
    `GET <hedef> HTTP/1.1` + gövdesiz. `icerik_tipi=None` = çağıran başlığı bilmiyor (yalnız saf kullanım; `do_POST`
    daima doğrulanmış TEK değeri verir) → sınır gövdenin ilk satırından (`--<sınır>`) alınır, kurallar aynıdır.
    """
    yontem = yontem.upper()
    if yontem in ("GET", "HEAD"):
        return True, "okuma"
    if yontem != "POST":
        return False, f"{yontem} yazmadır"
    yol_kismi = urllib.parse.urlsplit(yol).path
    if (not _R_BATCH_YOLU.fullmatch(yol_kismi)
            or any(s.split(";")[0].strip(".") == "" for s in yol_kismi.split("/")[1:])):
        return False, "yalnız /sap/opu/odata(4)/…/$batch POST'u iletilir (function import / create = yazma olabilir)"
    g = govde or b""
    if icerik_tipi is None:
        ilk = g.split(b"\r\n", 1)[0]
        sinir = ilk[2:].decode("ascii", "replace") if ilk.startswith(b"--") else ""
        sinir = sinir if _R_SINIR.fullmatch(sinir) else None
    else:
        sinir = sinir_al(icerik_tipi)
    if not sinir:
        return False, (f"$batch istek tipi `multipart/mixed; boundary=…` değil ({icerik_tipi or 'yok'}) — "
                       "JSON batch / sınırsız / bilinmeyen biçim")
    neden = batch_govde_denetle(g, sinir)
    if neden:
        return False, f"$batch: {neden}"
    return True, "okuma batch'i (yalnız GET parçaları)"


def host_gecerli(host: str | None, port: int) -> bool:
    """Host başlığı bu yerel sunucunun kendisi mi? (DNS rebinding: yabancı adla gelen tarayıcı isteği SAP'ye gitmez.)

    Kabul: `localhost:<port>` / `127.0.0.1:<port>` (port 80 ise portsuz biçim de). Başlık yoksa → hayır. Saf fonksiyon.
    """
    h = (host or "").strip().lower()
    kabul = {f"localhost:{port}", f"127.0.0.1:{port}"}
    if port == 80:
        kabul |= {"localhost", "127.0.0.1"}
    return h in kabul


def isleyici_sinifi(kok: Path, taban: str, client: str, kimlik: tuple[str, str], ctx):
    auth = "Basic " + base64.b64encode(f"{kimlik[0]}:{kimlik[1]}".encode()).decode()

    class Isleyici(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(kok), **k)

        def log_message(self, fmt, *args):
            if self.path.startswith("/sap/"):
                print(f"{self.command} {self.path[:150]} → {args[1] if len(args) > 1 else ''}", flush=True)

        def _ilet(self, govde: bytes | None = None, icerik_tipi: str | None = None):
            ayrik = urllib.parse.urlsplit(self.path)
            q = urllib.parse.parse_qsl(ayrik.query, keep_blank_values=True)
            if client and not any(k == "sap-client" for k, _ in q):
                q.append(("sap-client", client))
            url = f"{taban}{ayrik.path}" + ("?" + urllib.parse.urlencode(q, safe="'$,()") if q else "")
            # Content-Type istemci başlıklarından KOPYALANMAZ: çift başlıkta sözlük SONUNCUYU tutuyordu, kapı İLKİNE
            # bakıyordu (ölçüldü: multipart/mixed + application/json → SAP'ye json gitti). İletilen = doğrulanan değer.
            h = {k: v for k, v in self.headers.items() if k.lower() in GECEN_ISTEK and k.lower() != "content-type"}
            if icerik_tipi is not None:
                h["Content-Type"] = icerik_tipi
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

        def _karar(self, govde: bytes = b"", icerik_tipleri: list | None = None):
            if not self.path.startswith("/sap/"):
                if self.command in ("GET", "HEAD"):
                    return super().do_GET() if self.command == "GET" else super().do_HEAD()
                return self._yanit(405, "yerel dosya sunucusu yalniz GET/HEAD")
            if not host_gecerli(self.headers.get("Host"), self.server.server_address[1]):
                print(f"REDDEDİLDİ {self.command} {self.path[:150]} — yabancı Host başlığı", flush=True)
                return self._yanit(403, "Salt-okur yerel test sunucusu: Host localhost/127.0.0.1 degil")
            icerik_tipi = None
            if self.command == "POST":
                icerik_tipi = tek_icerik_tipi(icerik_tipleri)
                if icerik_tipi is None:
                    neden = f"Content-Type başlığı tam 1 değil ({len(icerik_tipleri or [])} adet)"
                    print(f"REDDEDİLDİ {self.command} {self.path[:150]} — {neden}", flush=True)
                    return self._yanit(403, f"Salt-okur yerel test sunucusu yazma istegini reddetti: {neden}")
            izin, neden = izin_ver(self.command, self.path, govde, icerik_tipi)
            if not izin:
                print(f"REDDEDİLDİ {self.command} {self.path[:150]} — {neden}", flush=True)
                return self._yanit(403, f"Salt-okur yerel test sunucusu yazma istegini reddetti: {neden}")
            return self._ilet(govde if self.command == "POST" else None, icerik_tipi)

        def do_GET(self):  # noqa: N802
            self._karar()

        def do_HEAD(self):  # noqa: N802
            self._karar()

        def do_POST(self):  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            self._karar(self.rfile.read(n) if n else b"", self.headers.get_all("Content-Type") or [])

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
