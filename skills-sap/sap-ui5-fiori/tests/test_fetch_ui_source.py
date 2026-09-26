#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z144: fetch_ui_source.py + _bspkaynak.py + ui_local_proxy.py — kaynağı yerelde olmayan UI5 uygulamasını SAP'den
salt-okuma indirme, kaynağı geri kurma, eşlik/drift ölçümü, tip-kapsamlı $metadata ve salt-okur yerel sunucu.

Ağ yalnız 127.0.0.1 sahte sunucusudur; npm/build KOŞULMAZ (`eslik --no-build`).
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import _helpers as H

sys.path.insert(0, str(H.SCRIPTS))


def _modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, H.SCRIPTS / dosya)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


K = _modul("_bspkaynak_t", "_bspkaynak.py")
P = _modul("ui_local_proxy_t", "ui_local_proxy.py")
D = _modul("deploy_ui_fk_t", "deploy_ui.py")

BSP = "ZXX001_ORDER"
# Canlıda ölçülen BSP biçiminin küçük modeli: derlenmiş dist (küçültülmüş + -dbg + map + preload), CRLF saklanmış metin.
CANLI = {
    "manifest.json": b'{\r\n  "sap.app": {"id": "zxx001.order"}\r\n}\r\n',
    "index.html": b"<html>\r\n</html>\r\n",
    "Component.js": b"sap.ui.define([],function(){return 1});",
    "Component-dbg.js": b"sap.ui.define([], function () {\r\n  return 1;\r\n});\r\n",
    "Component.js.map": b'{"version":3,"sources":["Component-dbg.js"]}',
    "controller/List.controller.js": b"sap.ui.define([],function(){})",
    "controller/List-dbg.controller.js": b"sap.ui.define([], function () {\r\n});\r\n",
    "controller/List.controller.js.map": b'{"version":3,"sources":["List-dbg.controller.js"]}',
    "Component-preload.js": H.PRELOAD,
    "Component-preload.js.map": b"{}",
    "i18n/i18n.properties": b"a=b\r\n",
    "img/logo.png": b"\x89PNG\r\n\x1a\n\x00\r\n",
}


def _atom(girdiler: list[tuple[str, bool]]) -> bytes:
    """ADT filestore Atom listesi: (id, klasör mü). id'ler canlıdaki gibi URL-kodlu."""
    parca = ['<feed xmlns="http://www.w3.org/2005/Atom">']
    for ad, klasor in girdiler:
        kod = ad.replace("/", "%2f")
        parca.append(f'<entry><id>{kod}</id><title>{ad}</title><category term="{"folder" if klasor else "file"}"/></entry>')
    parca.append("</feed>")
    return "".join(parca).encode()


class TestKaynakKur(unittest.TestCase):
    def test_dbg_geri_kurma(self):
        webapp, atilan, uyari = K.kaynak_kur(CANLI)
        ok = (webapp["Component.js"] == b"sap.ui.define([], function () {\n  return 1;\n});\n"
              and webapp["controller/List.controller.js"] == b"sap.ui.define([], function () {\n});\n"
              and "Component-dbg.js" not in webapp and "Component-preload.js" not in webapp
              and not any(r.endswith(".map") for r in webapp)
              and webapp["i18n/i18n.properties"] == b"a=b\n"
              and webapp["img/logo.png"] == CANLI["img/logo.png"]  # ikili dosyaya dokunulmaz
              and set(atilan) == {"Component.js", "Component.js.map", "controller/List.controller.js",
                                  "controller/List.controller.js.map", "Component-preload.js",
                                  "Component-preload.js.map"}
              and uyari == [] and K.uygulama_kimligi(webapp) == "zxx001.order")
        H.kaydet("kaynak_kur: -dbg → asıl ad, build ürünü atılır, metin LF", "8 kaynak, 6 atılan, 0 uyarı",
                 f"{len(webapp)} kaynak, {len(atilan)} atılan, {len(uyari)} uyarı", ok)
        self.assertTrue(ok, (sorted(webapp), atilan, uyari))

    def test_ts_ve_dbgsiz_uyari(self):
        dist = {"manifest.json": b"{}", "a.js": b"x", "b.js": b"y", "b-dbg.js": b"yy",
                "b.js.map": b'{"sources":["b.ts"]}'}
        _, _, uyari = K.kaynak_kur(dist)
        ok = len(uyari) == 2 and "TypeScript" in uyari[1] and "a.js" in uyari[0]
        H.kaydet("kaynak_kur: TS map + -dbg'siz js → uyarı", "2 uyarı", f"{len(uyari)}", ok)
        self.assertTrue(ok, uyari)


class TestKiyas(unittest.TestCase):
    def test_kovalar(self):
        a = {"x": b"1\r\n", "y": b"2", "z": b"3"}
        b = {"x": b"1\n", "y": b"22", "w": b"4"}
        k = K.kume_karsilastir(a, b)
        ok = (k["esit"] == ["x"] and k["farkli"] == ["y"] and k["yalniz_a"] == ["z"] and k["yalniz_b"] == ["w"]
              and not K.kume_esit_mi(k))
        H.kaydet("kume_karsilastir: eşit (CRLF≡LF)/farklı/yalnız-1/yalnız-2", "1/1/1/1", K.ozet(k), ok)
        self.assertTrue(ok, k)

    def test_preload_satir_sonu_ayri_kova(self):
        crlf = H.PRELOAD.replace(rb"\n<App", rb"\r\n<App")
        k = K.kume_karsilastir({"Component-preload.js": crlf}, {"Component-preload.js": H.PRELOAD},
                               D.preload_karsilastir)
        ok = k["satir_sonu"] == ["Component-preload.js"] and not K.kume_esit_mi(k)
        H.kaydet("kume_karsilastir: preload kaçışlı \\r\\n → ayrı kova, eşit DEĞİL", "satir_sonu 1", K.ozet(k), ok)
        self.assertTrue(ok, k)

    def test_deploy_haric_regex(self):
        ok = K._deploy_haric("test/x.js", ["/test/"]) and not K._deploy_haric("view/a.xml", ["/test/"])
        H.kaydet("deploy exclude regex: /test/ eşleşir, view/ eşleşmez", "True/False", str(ok), ok)
        self.assertTrue(ok)


class TestIndirmeYollari(unittest.TestCase):
    def test_odata_birincil(self):
        cagri = []

        def get(url, kimlik, s):
            cagri.append(url)
            return H.odata_zip(CANLI)

        d, bilgi, yol = K.canli_indir("https://h.invalid", "100", BSP, ("u", "p"), get=get)
        ok = (yol == "odata" and d == CANLI and bilgi["Package"] == "ZXX001" and len(cagri) == 1
              and "DownloadFiles='RUNTIME'" in cagri[0] and "sap-client=100" in cagri[0])
        H.kaydet("canli_indir: OData zip birincil yol, tek istek", "odata 1 istek", f"{yol} {len(cagri)}", ok)
        self.assertTrue(ok, cagri)

    def test_adt_yedek_klasor_ve_url_kodlu_id(self):
        agac = {
            BSP: _atom([(f"{BSP}/manifest.json", False), (f"{BSP}/i18n", True)]),
            f"{BSP}/manifest.json": b"{}",
            f"{BSP}/i18n": _atom([(f"{BSP}/i18n/i18n.properties", False)]),
            f"{BSP}/i18n/i18n.properties": b"a=b",
        }

        def get(url, kimlik, s):
            if "ABAP_REPOSITORY_SRV" in url:
                raise urllib.error.HTTPError(url, 404, "yok", {}, None)
            oge = urllib.request.unquote(url.split("/objects/", 1)[1].split("/content", 1)[0])
            return agac[oge]

        d, _, yol = K.canli_indir("https://h.invalid", "", BSP, ("u", "p"), get=get)
        ok = yol == "adt" and d == {"manifest.json": b"{}", "i18n/i18n.properties": b"a=b"}
        H.kaydet("canli_indir: OData 404 → ADT filestore (özyinelemeli, id çözülür)", "adt 2 dosya", f"{yol} {sorted(d)}", ok)
        self.assertTrue(ok, d)

    def test_iki_yol_duserse_hata(self):
        def get(url, kimlik, s):
            raise urllib.error.HTTPError(url, 403, "yasak", {}, None)

        with self.assertRaises(K.IndirmeHatasi) as c:
            K.canli_indir("https://h.invalid", "", BSP, ("u", "p"), get=get)
        ok = "OData" in str(c.exception) and "ADT" in str(c.exception)
        H.kaydet("canli_indir: iki yol da 403 → IndirmeHatasi (ölçüm yok)", "hata", str(c.exception)[:40], ok)
        self.assertTrue(ok)


class TestMetadataTipKapsamli(unittest.TestCase):
    META = (b'<edmx:Edmx xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx"><edmx:DataServices>'
            b'<Schema xmlns="http://schemas.microsoft.com/ado/2008/09/edm" xmlns:sap="http://www.sap.com/Protocols/SAPData">'
            b'<EntityType Name="SiparisType"><Property Name="Vbeln" Type="Edm.String" sap:label="Belge"/></EntityType>'
            b'<EntityType Name="SAP__Signature"><Property Name="Reason" Type="Edm.String"/></EntityType>'
            b"</Schema></edmx:DataServices></edmx:Edmx>")

    def test_alan_tipe_baglanir(self):
        t = K.metadata_tipleri(self.META)
        ok = ("Reason" in t["SAP__Signature"] and "Reason" not in t["SiparisType"]
              and t["SiparisType"]["Vbeln"]["label"] == "Belge")
        H.kaydet("metadata_tipleri: başka tipteki aynı adlı alan ana tipe SAYILMAZ", "tip-kapsamlı", str(ok), ok)
        self.assertTrue(ok, t)


class TestCliIndirEslik(unittest.TestCase):
    def setUp(self):
        self.kok = Path(tempfile.mkdtemp(prefix="ui5fetch_"))

    def tearDown(self):
        shutil.rmtree(self.kok, ignore_errors=True)

    def test_indir_iskelet_ve_ustune_yazmaz(self):
        with H.SahteSunucu({H.odata_yol(BSP): H.odata_zip(CANLI)}) as srv:
            app = self.kok / "order_app"
            rc, out = H.kos("fetch_ui_source.py", "indir", BSP, "--out", app, "--url", srv.url, "--client", "100",
                            kimlik=True)
            rc2, out2 = H.kos("fetch_ui_source.py", "indir", BSP, "--out", app, "--url", srv.url, "--client", "100",
                              kimlik=True)
        ayar = D.B.deploy_ayari(app) or {}
        bilgi = json.loads((app / ".canli" / "bilgi.json").read_text(encoding="utf-8"))
        ok = (rc == 0 and (app / "webapp" / "Component.js").is_file() and ayar.get("name") == BSP
              and ayar.get("package") == "ZXX001" and ayar.get("url") == srv.url and not ayar.get("transport")
              and not ayar.get("resources_excludes") and len(bilgi["dosyalar"]) == len(CANLI)
              and "dist/" in (app / ".gitignore").read_text(encoding="utf-8")
              and ".canli/" in (app / ".gitignore").read_text(encoding="utf-8")
              and rc2 == 1 and "YAZILMAZ" in out2 and H.PAROLA not in out)
        H.kaydet("fetch indir: webapp + iskelet + .canli; ikinci kez → üstüne yazmaz", "rc=0 / rc=1",
                 f"rc={rc} / rc={rc2}", ok)
        self.assertTrue(ok, out + out2)

    def test_kimliksiz_olcum_yok(self):
        rc, out = H.kos("fetch_ui_source.py", "indir", BSP, "--out", self.kok / "a", "--url", "http://127.0.0.1:9")
        ok = rc == 2 and "set değil" in out and not (self.kok / "a").exists()
        H.kaydet("fetch indir: env kimlik yok → ölçüm yok, klasör yok", "rc=2", f"rc={rc}", ok)
        self.assertTrue(ok, out)

    def test_eslik_esit_farkli_anliksiz(self):
        app = self.kok / "app"
        K.anlik_yaz(app, CANLI, {"bsp": BSP})
        K.klasore_yaz(app / "dist", {r: v.replace(b"\r\n", b"\n") for r, v in CANLI.items()})
        rc1, out1 = H.kos("fetch_ui_source.py", "eslik", app, "--no-build")
        (app / "dist" / "i18n" / "i18n.properties").write_bytes(b"a=c\n")
        rc2, out2 = H.kos("fetch_ui_source.py", "eslik", app, "--no-build")
        rc3, out3 = H.kos("fetch_ui_source.py", "eslik", self.kok / "yok", "--no-build")
        ok = rc1 == 0 and "EŞLİK:" in out1 and rc2 == 1 and "i18n/i18n.properties" in out2 and rc3 == 2
        H.kaydet("fetch eslik: eşit=0 · farklı=1 · anlık görüntü yok=2", "0/1/2", f"{rc1}/{rc2}/{rc3}", ok)
        self.assertTrue(ok, out1 + out2 + out3)


class TestSaltOkurProxy(unittest.TestCase):
    def test_izin_tablosu(self):
        vakalar = [
            (("GET", "/sap/opu/odata/sap/X/Set"), True),
            (("HEAD", "/sap/opu/odata/sap/X/"), True),
            (("POST", "/sap/opu/odata/sap/X/$batch", b"--batch\r\nGET Set HTTP/1.1\r\n"), True),
            (("POST", "/sap/opu/odata/sap/X/$batch", b"--batch\r\nContent-Type: multipart/mixed; boundary=ChangeSet_1"), False),
            (("POST", "/sap/opu/odata/sap/X/Set", b"{}"), False),
            (("POST", "/sap/opu/odata/sap/X/Onayla?Id='1'", b""), False),
            (("PUT", "/sap/opu/odata/sap/X/Set('1')"), False),
            (("MERGE", "/sap/opu/odata/sap/X/Set('1')"), False),
            (("PATCH", "/sap/opu/odata/sap/X/Set('1')"), False),
            (("DELETE", "/sap/opu/odata/sap/X/Set('1')"), False),
        ]
        yanlis = [(g, b) for g, b in vakalar if P.izin_ver(*g)[0] != b]
        ok = not yanlis
        H.kaydet("proxy izin_ver: okuma geçer, 7 yazma biçimi 403", "10/10", f"{len(vakalar) - len(yanlis)}/10", ok)
        self.assertTrue(ok, yanlis)

    def test_uctan_uca_yazma_sapye_gitmez(self):
        H.proxy_bypass_surec_ici()
        kok = Path(tempfile.mkdtemp(prefix="ui5proxy_"))
        (kok / "index.html").write_bytes(b"<html/>")
        try:
            with H.SahteSunucu({"/sap/opu/odata/sap/X/Set": b'{"d":[]}'}) as sap:
                import ssl
                srv = P.Sunucu(("127.0.0.1", 0), P.isleyici_sinifi(kok, sap.url, "100", (H.KULLANICI, H.PAROLA),
                                                                     ssl.create_default_context()))
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                taban = f"http://127.0.0.1:{srv.server_address[1]}"
                try:
                    kodlar = {}
                    for yontem, yol in (("GET", "/sap/opu/odata/sap/X/Set"), ("DELETE", "/sap/opu/odata/sap/X/Set"),
                                        ("POST", "/sap/opu/odata/sap/X/Set"), ("GET", "/index.html")):
                        req = urllib.request.Request(taban + yol, method=yontem, data=b"{}" if yontem == "POST" else None)
                        try:
                            kodlar[(yontem, yol)] = urllib.request.urlopen(req, timeout=10).status
                        except urllib.error.HTTPError as e:
                            kodlar[(yontem, yol)] = e.code
                finally:
                    srv.shutdown()
                    srv.server_close()
                sap_istek = list(sap.istekler)
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        degerler = list(kodlar.values())
        ok = degerler == [200, 403, 403, 200] and sap_istek == ["/sap/opu/odata/sap/X/Set?sap-client=100"]
        H.kaydet("proxy uçtan uca: GET iletilir (auth'lu), DELETE/POST 403 + SAP'ye 0 istek", "200/403/403/200 · 1",
                 f"{degerler} · {len(sap_istek)}", ok)
        self.assertTrue(ok, (kodlar, sap_istek))


if __name__ == "__main__":
    unittest.main()
