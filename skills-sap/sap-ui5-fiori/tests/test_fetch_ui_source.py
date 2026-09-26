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


class TestZipSlip(unittest.TestCase):
    """Sunucudan gelen ad (zip adı / ADT id) hedef klasörün dışına yazdıramaz."""
    KOTU = ["../kacis.txt", "a/../../kacis.txt", "..\\kacis.txt", "/mutlak.txt", "\\mutlak.txt", "C:/surucu.txt",
            "C:surucu.txt", "d:\\surucu.txt", "a/b:akis", ".."]

    def setUp(self):
        self.ust = Path(tempfile.mkdtemp(prefix="zipslip_"))
        self.kok = self.ust / "hedef"

    def tearDown(self):
        shutil.rmtree(self.ust, ignore_errors=True)

    def test_klasore_yaz_kok_disi_ad_yazmaz(self):
        yakalanan = 0
        for kotu in self.KOTU:
            with self.assertRaises(K.GuvensizYolHatasi, msg=kotu):
                K.klasore_yaz(self.kok, {"iyi.txt": b"1", kotu: b"x"})
            yakalanan += 1
        yazilan = sorted(p.relative_to(self.ust).as_posix() for p in self.ust.rglob("*") if p.is_file())
        # Kontrol grubu: iç içe klasör ve adında nokta olan (segment değil) dosya yazılır.
        K.klasore_yaz(self.kok, {"a/b/c.txt": b"1", "x..y.js": b"2", "./nokta.txt": b"3"})
        iyi = sorted(p.relative_to(self.kok).as_posix() for p in self.kok.rglob("*") if p.is_file())
        ok = yakalanan == len(self.KOTU) and yazilan == [] and iyi == ["a/b/c.txt", "nokta.txt", "x..y.js"]
        H.kaydet("klasore_yaz: kök dışı ad → hata, hiç dosya yok · iç ad yazılır",
                 f"{len(self.KOTU)} red · 0 · 3", f"{yakalanan} red · {len(yazilan)} · {len(iyi)}", ok)
        self.assertTrue(ok, (yazilan, iyi))

    def test_canli_indir_guvensiz_ad_yedege_gecmez(self):
        cagri = []

        def get(url, kimlik, s):
            cagri.append(url)
            return H.odata_zip({"manifest.json": b"{}", "../../kacis.js": b"x"})

        with self.assertRaises(K.GuvensizYolHatasi) as c:
            K.canli_indir("https://h.invalid", "", BSP, ("u", "p"), get=get)
        ok = len(cagri) == 1 and isinstance(c.exception, K.IndirmeHatasi) and "kacis.js" in str(c.exception)
        H.kaydet("canli_indir: zip'te ../ adı → GuvensizYolHatasi, ADT'ye geçmez", "hata · 1 istek",
                 f"{type(c.exception).__name__} · {len(cagri)} istek", ok)
        self.assertTrue(ok, (cagri, str(c.exception)))

    def test_anlik_yaz_guvensiz_adda_eskisi_silinmez(self):
        app = self.ust / "app"
        K.anlik_yaz(app, {"a.js": b"eski"}, {"bsp": BSP})
        with self.assertRaises(K.GuvensizYolHatasi):
            K.anlik_yaz(app, {"a.js": b"yeni", "../../x.js": b"k"}, {"bsp": BSP})
        eski = (app / K.ANLIK_KLASOR / "dist" / "a.js").read_bytes()
        ok = eski == b"eski" and not (app / "x.js").exists() and not (self.ust / "x.js").exists()
        H.kaydet("anlik_yaz: güvensiz ad → eski anlık görüntü yerinde", "eski", eski.decode(), ok)
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

    # Standart UI5 V2 ODataModel okuma batch'i (yalnız GET parçaları, boundary `batch_…`) — kontrol grubu.
    V2_OKUMA = (b"--batch_a1b2-c3d4\r\nContent-Type: application/http\r\nContent-Transfer-Encoding: binary\r\n\r\n"
                b"GET Orders?$skip=0&$top=20 HTTP/1.1\r\nsap-cancel-on-close: true\r\nAccept: application/json\r\n"
                b"DataServiceVersion: 2.0\r\nMaxDataServiceVersion: 2.0\r\n\r\n\r\n"
                b"--batch_a1b2-c3d4\r\nContent-Type: application/http\r\nContent-Transfer-Encoding: binary\r\n\r\n"
                b"GET Orders/$count HTTP/1.1\r\nAccept: text/plain\r\n\r\n\r\n--batch_a1b2-c3d4--\r\n")
    MP = "multipart/mixed; boundary=batch_a1b2-c3d4"

    def test_batch_okuma_kontrol_grubu_gecer(self):
        vakalar = [
            ("POST", "/sap/opu/odata/sap/ZXX001_SRV/$batch", self.V2_OKUMA, self.MP),
            ("POST", "/sap/opu/odata/sap/ZXX001_SRV/$batch", self.V2_OKUMA, None),
            ("POST", "/sap/opu/odata/sap/ZXX001_SRV;o=LOCAL/$batch?sap-client=000", self.V2_OKUMA, self.MP),
            ("POST", "/sap/opu/odata4/sap/zxx001_ui/srvd/sap/zxx001_ui/0001/$batch", self.V2_OKUMA, self.MP),
        ]
        yanlis = [v[1] for v in vakalar if not P.izin_ver(*v)[0]]
        ok = not yanlis
        H.kaydet("proxy $batch kontrol grubu: V2/V4 GET-yalnız batch geçer", "4/4", f"{4 - len(yanlis)}/4", ok)
        self.assertTrue(ok, yanlis)

    def test_batch_yazma_atlatmalari_reddedilir(self):
        b = b"--batch_1\r\nContent-Type: application/http\r\nContent-Transfer-Encoding: binary\r\n\r\n"
        v2 = "/sap/opu/odata/sap/X/$batch"
        vakalar = {
            "a iç multipart/mixed (changeset kelimesiz)": (
                v2, b + b"Content-Type: multipart/mixed; boundary=abc\r\n\r\n"
                        b"--abc\r\n\r\nPOST Orders HTTP/1.1\r\n\r\n{}\r\n--abc--\r\n"),
            "b changeset'siz DELETE parçası": (v2, b + b"DELETE Orders(1) HTTP/1.1\r\n\r\n--batch_1--\r\n"),
            "c SOAP RFC yolu": ("/sap/bc/soap/rfc/$batch", b"<SOAP-ENV:Envelope/>"),
            "c' SOAP yolu GET gövdeli": ("/sap/bc/soap/rfc/$batch", self.V2_OKUMA),
            "küçük harf delete": (v2, b + b"delete Orders(1) HTTP/1.1\r\n\r\n"),
            "baştaki boşluklu POST": (v2, b + b"   POST Orders HTTP/1.1\r\n\r\n{}\r\n"),
            "sürümsüz MERGE satırı": (v2, b + b"MERGE Orders(1)\r\n\r\n"),
            "GET + DELETE karışık": (v2, self.V2_OKUMA + b + b"DELETE Orders(1) HTTP/1.1\r\n\r\n"),
            "iç multipart/mixed tek başına": (v2, b + b"GET X HTTP/1.1\r\ncontent-type:multipart/mixed;boundary=q\r\n"),
            "JSON batch gövdesi": (v2, b'{"requests":[{"method":"GET","url":"Orders"}]}'),
            "JSON dizi gövdesi (boşluklu)": (v2, b'  [{"method":"DELETE"}]'),
            "X-HTTP-Method ezmesi": (v2, b + b"GET Orders(1) HTTP/1.1\r\nX-HTTP-Method: DELETE\r\n\r\n"),
            "base64 parça": (v2, b.replace(b"binary", b"base64") + b"R0VUIA==\r\n"),
            "istek satırı yok": (v2, b"--batch_1\r\n\r\n--batch_1--"),
            "boş gövde": (v2, b""),
            "yol .. ile kaçış": ("/sap/opu/odata/../../bc/soap/rfc/$batch", self.V2_OKUMA),
            "yol % kodlu": ("/sap/opu/odata/sap/X%2F..%2F/$batch", self.V2_OKUMA),
            "odata dışı ICF yolu": ("/sap/bc/ui2/$batch", self.V2_OKUMA),
            "bilinmeyen yöntem (PURGE) satırı": (v2, b + b"PURGE Orders(1) HTTP/1.1\r\n\r\n"),
            "JSON içinde GET satırı": (v2, b'{"a":1,\n GET Orders HTTP/1.1\n"requests":[]}'),
        }
        yanlis = [ad for ad, (yol, g) in vakalar.items() if P.izin_ver("POST", yol, g)[0]]
        # İstek tipi JSON ya da multipart dışı → gövde okuma bile olsa red (do_POST Content-Type'ı iletir).
        for ad, tip in (("istek tipi application/json", "application/json"), ("istek tipi yok", ""),
                        ("istek tipi text/plain", "text/plain")):
            if P.izin_ver("POST", v2, self.V2_OKUMA, tip)[0]:
                yanlis.append(ad)
        n = len(vakalar) + 3
        ok = not yanlis
        H.kaydet("proxy $batch: yazma atlatmaları (a/b/c+JSON+…) 403", f"{n}/{n}", f"{n - len(yanlis)}/{n}", ok)
        self.assertTrue(ok, yanlis)

    def test_host_basligi(self):
        vakalar = [
            (("localhost:8484", 8484), True), (("127.0.0.1:8484", 8484), True), (("LOCALHOST:8484", 8484), True),
            (("saldirgan.example:8484", 8484), False), (("localhost:9999", 8484), False), (("localhost", 8484), False),
            ((None, 8484), False), (("", 8484), False), (("127.0.0.1.saldirgan.example:8484", 8484), False),
            (("localhost", 80), True),
        ]
        yanlis = [(g, b) for g, b in vakalar if P.host_gecerli(*g) != b]
        ok = not yanlis
        H.kaydet("proxy host_gecerli: yalnız localhost/127.0.0.1:<port>", "10/10", f"{10 - len(yanlis)}/10", ok)
        self.assertTrue(ok, yanlis)

    def test_uctan_uca_host_ve_icerik_tipi(self):
        """Kablolama: yabancı Host → 403 + SAP'ye 0 istek; do_POST istek Content-Type'ını izin_ver'e iletir."""
        H.proxy_bypass_surec_ici()
        kok = Path(tempfile.mkdtemp(prefix="ui5proxy_"))
        (kok / "index.html").write_bytes(b"<html/>")
        try:
            with H.SahteSunucu({"/sap/opu/odata/sap/X/Set": b'{"d":[]}'}) as sap:
                import ssl
                srv = P.Sunucu(("127.0.0.1", 0), P.isleyici_sinifi(kok, sap.url, "100", (H.KULLANICI, H.PAROLA),
                                                                     ssl.create_default_context()))
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                port = srv.server_address[1]
                taban = f"http://127.0.0.1:{port}"

                # SahteSunucu POST işlemez (501 + gövde okunmadan kapanış → proxy'de ara sıra 502: ölçüldü 1/8).
                # Deterministik olsun: gövdeyi okuyan, isteği kaydeden 202 yanıtçısı.
                def _post(h):
                    h.rfile.read(int(h.headers.get("Content-Length") or 0))
                    sap.istekler.append("POST " + h.path.split("?", 1)[0])
                    h.send_response(202)
                    h.send_header("Content-Length", "0")
                    h.end_headers()
                sap.httpd.RequestHandlerClass.do_POST = _post

                def kod(yol, host=None, yontem="GET", govde=None, tip=None):
                    h = {}
                    if host:
                        h["Host"] = host
                    if tip:
                        h["Content-Type"] = tip
                    req = urllib.request.Request(taban + yol, method=yontem, data=govde, headers=h)
                    try:
                        return urllib.request.urlopen(req, timeout=10).status
                    except urllib.error.HTTPError as e:
                        return e.code
                try:
                    yabanci = kod("/sap/opu/odata/sap/X/Set", host=f"saldirgan.example:{port}")
                    sonra_sap = len(sap.istekler)
                    dogru = kod("/sap/opu/odata/sap/X/Set", host=f"localhost:{port}")
                    # İletilen batch 202 döner (= SAP'ye GİTTİ); reddedilen 403 ve SAP'de iz bırakmaz.
                    json_tip = kod("/sap/opu/odata/sap/X/$batch", yontem="POST", govde=self.V2_OKUMA,
                                   tip="application/json")
                    mp_tip = kod("/sap/opu/odata/sap/X/$batch", yontem="POST", govde=self.V2_OKUMA, tip=self.MP)
                finally:
                    srv.shutdown()
                    srv.server_close()
                post_iz = [i for i in sap.istekler if i.startswith("POST ")]
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        gercek = (yabanci, sonra_sap, dogru, json_tip, mp_tip, post_iz)
        ok = gercek == (403, 0, 200, 403, 202, ["POST /sap/opu/odata/sap/X/$batch"])
        H.kaydet("proxy uçtan uca: yabancı Host 403/0 istek · JSON tip 403", "403/0/200/403/202 · 1 POST",
                 str(gercek[:5]) + f" · {len(post_iz)} POST", ok)
        self.assertTrue(ok, gercek)

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
