# -*- coding: utf-8 -*-
"""kaynak_paketi.py: ikili kaynaktan mekanik paket (docx/xlsx, OLE/altChunk, doğrulama) + iz denetimi.

Fikstürler testte üretilir (zipfile + elle yazılan küçük CFB); gerçek müşteri belgesi kullanılmaz. Geçici dizinler
sistem TEMP'inde (repo dışında) kurulur, paket hedefi daima açık verilir — kullanıcı dizinine dokunulmaz.
"""
import json
import os
import re
import shutil
import struct
import tempfile
import unittest
import zipfile
from unittest import mock

from _common import REPO, call_main, run_py, write_png

import kaynak_paketi as kp

# Ad alanı URI'leri parçalı yazılır: skill iz taraması (test_skill_structure) dosyalarda URL yasaklar.
_S = "http" + "://schemas.openxmlformats.org/"
NS = {
    "w": _S + "wordprocessingml/2006/main",
    "r": _S + "officeDocument/2006/relationships",
    "a": _S + "drawingml/2006/main",
    "wp": _S + "drawingml/2006/wordprocessingDrawing",
    "pic": _S + "drawingml/2006/picture",
    "mc": _S + "markup-compatibility/2006",
    "wps": "http" + "://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "m": _S + "officeDocument/2006/math",
    "dgm": _S + "drawingml/2006/diagram",
    "c": _S + "drawingml/2006/chart",
}
REL = _S + "officeDocument/2006/relationships/"
PKG_REL = _S + "package/2006/relationships"
CT = _S + "package/2006/content-types"

ENDOFCHAIN, FREESECT, FATSECT, NOSTREAM = 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD, 0xFFFFFFFF


# ── BÖLÜM: CFB / OLE yazıcı ──
def cfb_yaz(akislar):
    """Minimal CFB v3 (512 baytlık sektör): kök + düz akışlar. 4096'dan küçük akış mini akışa gider (okuyucunun
    iki yolu da sınansın). Yalnız tek FAT sektörüne sığan (≤ 128 sektör) dosya üretir."""
    ss, cutoff = 512, 4096
    mini, minifat, mini_bas = b"", [], {}
    for ad, d in akislar:
        if len(d) >= cutoff or not d:
            continue
        n = (len(d) + 63) // 64
        bas = len(mini) // 64
        mini_bas[ad] = bas
        mini += d + b"\x00" * (n * 64 - len(d))
        minifat += [bas + k + 1 for k in range(n - 1)] + [ENDOFCHAIN]

    def sektor_sayisi(b):
        return (len(b) + ss - 1) // ss

    n_dir = sektor_sayisi(b"\x00" * (128 * (1 + len(akislar))))
    minifat_b = struct.pack("<%dI" % len(minifat), *minifat) if minifat else b""
    n_mf, n_ms = sektor_sayisi(minifat_b), sektor_sayisi(mini)
    sira = 1
    dir_bas, sira = sira, sira + n_dir
    mf_bas, sira = (sira if n_mf else ENDOFCHAIN), sira + n_mf
    ms_bas, sira = (sira if n_ms else ENDOFCHAIN), sira + n_ms
    buyuk_bas = {}
    for ad, d in akislar:
        if len(d) >= cutoff:
            buyuk_bas[ad] = sira
            sira += sektor_sayisi(d)
    assert sira <= 128, "test yazıcısı tek FAT sektörüyle sınırlı"
    fat = [FREESECT] * 128
    fat[0] = FATSECT

    def zincirle(bas, n):
        for k in range(n):
            fat[bas + k] = bas + k + 1 if k < n - 1 else ENDOFCHAIN

    zincirle(dir_bas, n_dir)
    if n_mf:
        zincirle(mf_bas, n_mf)
    if n_ms:
        zincirle(ms_bas, n_ms)
    for ad, d in akislar:
        if ad in buyuk_bas:
            zincirle(buyuk_bas[ad], sektor_sayisi(d))

    def girdi(ad, tur, sol, sag, cocuk, bas, boy):
        ad_b = ad.encode("utf-16-le") + b"\x00\x00"
        e = ad_b.ljust(64, b"\x00") + struct.pack("<HBB", len(ad_b), tur, 1)
        e += struct.pack("<III", sol, sag, cocuk) + b"\x00" * 16 + b"\x00" * 4 + b"\x00" * 16
        return e + struct.pack("<IQ", bas, boy)

    dizin = girdi("Root Entry", 5, NOSTREAM, NOSTREAM, 1 if akislar else NOSTREAM, ms_bas, len(mini))
    for i, (ad, d) in enumerate(akislar, 1):
        bas = buyuk_bas.get(ad, mini_bas.get(ad, ENDOFCHAIN))
        dizin += girdi(ad, 2, NOSTREAM, i + 1 if i < len(akislar) else NOSTREAM, NOSTREAM, bas, len(d))
    bos = (b"\x00" * 64 + struct.pack("<HBB", 0, 0, 0) + struct.pack("<III", NOSTREAM, NOSTREAM, NOSTREAM)
           + b"\x00" * 36 + struct.pack("<IQ", 0, 0))
    while len(dizin) % ss:
        dizin += bos
    baslik = kp.CFB_IMZA + b"\x00" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\x00" * 6
    baslik += struct.pack("<IIIIIIIII", 0, 1, dir_bas, 0, cutoff, mf_bas, n_mf, ENDOFCHAIN, 0)
    baslik += struct.pack("<109I", 0, *([FREESECT] * 108))
    assert len(baslik) == 512

    def doldur(b):
        return b + b"\x00" * (sektor_sayisi(b) * ss - len(b))

    govde = struct.pack("<128I", *fat) + dizin + doldur(minifat_b) + doldur(mini)
    for ad, d in akislar:
        if ad in buyuk_bas:
            govde += doldur(d)
    return baslik + govde


def ole10native_yaz(etiket, icerik, unicode_kopya=True):
    """Packager akışı: boy · bayrak · etiket · kaynak yol · sabit · geçici yol · içerik [· UTF-16 kopyalar]."""
    kaynak_yol = "C:/temp/" + etiket
    gecici = (kaynak_yol + "\x00").encode("cp1254")
    govde = struct.pack("<H", 2) + etiket.encode("cp1254") + b"\x00" + kaynak_yol.encode("cp1254") + b"\x00"
    govde += struct.pack("<I", 0x00030000) + struct.pack("<I", len(gecici)) + gecici
    govde += struct.pack("<I", len(icerik)) + icerik
    if unicode_kopya:
        for s in (kaynak_yol, etiket, kaynak_yol):
            govde += struct.pack("<I", len(s)) + s.encode("utf-16-le")
    return struct.pack("<I", len(govde)) + govde

# ── BÖLÜM: docx / xlsx üreticileri ──
STILLER = (
    '<w:styles xmlns:w="%s">'
    '<w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Balk1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style>'
    '<w:style w:type="paragraph" w:styleId="OzelBaslik"><w:name w:val="Ozel"/><w:basedOn w:val="Balk1"/></w:style>'
    '</w:styles>' % NS["w"])
PROTOTIP_BUYUK = ("<html><body><h1>Ekran 6</h1>" + "<p>alan</p>" * 600 + "</body></html>").encode("utf-8")
PROTOTIP_KUCUK = "<html><body><h1>Ekran 1 — Giriş</h1></body></html>".encode("utf-8")
ALTCHUNK = "<html><body><p>altChunk içeriği</p></body></html>".encode("utf-8")


def p(metin, stil=None, numara=False, ek=""):
    ppr = ""
    if stil or numara:
        ppr = "<w:pPr>%s%s</w:pPr>" % ('<w:pStyle w:val="%s"/>' % stil if stil else "",
                                       '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' if numara else "")
    run = '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % metin if metin else ""
    return "<w:p>%s%s%s</w:p>" % (ppr, run, ek)


def satir(*hucreler):
    return "<w:tr>%s</w:tr>" % "".join("<w:tc>%s</w:tc>" % (h if h.startswith("<") else p(h)) for h in hucreler)


GORSEL = ('<w:r><w:drawing><wp:inline><a:graphic><a:graphicData><pic:pic><pic:blipFill><a:blip r:embed="rIdImg"/>'
          '</pic:blipFill></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
KUTU = ('<w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wps:txbx><w:txbxContent>%s</w:txbxContent>'
        '</wps:txbx></w:drawing></mc:Choice><mc:Fallback><w:pict><v:textbox><w:txbxContent>%s</w:txbxContent>'
        '</v:textbox></w:pict></mc:Fallback></mc:AlternateContent></w:r>') % (p("Kutu metni"), p("Kutu metni"))
OLE = '<w:r><w:object><v:shape/><o:OLEObject ProgID="Package" r:id="%s"/></w:object></w:r>'


def ornek_govde():
    ic_tablo = "<w:tbl>%s</w:tbl>" % satir("iç A", "iç B")
    tablo = "<w:tbl>%s</w:tbl>" % "".join([
        satir("No", "Test senaryosu", "Beklenen"),
        satir("TS-01", "Sipariş kaydı", "Belge oluşur"),
        satir("TS-02", "İptal", "Belge iptal"),
        satir("TS-03", "a|b ¶ c\\d", "x"),
        satir("", "", ""),
        satir("TS-04", ic_tablo + p("sonra"), "y"),
    ])
    return "".join([
        p("Giriş", stil="Balk1"),
        "<w:p><w:r><w:t xml:space=\"preserve\">Birinci paragraf </w:t></w:r><w:r><w:t>devam | çizgi</w:t></w:r></w:p>",
        p(""),
        p("Liste öğesi", numara=True),
        "<w:sdt><w:sdtPr/><w:sdtContent>%s</w:sdtContent></w:sdt>" % p("İçerik denetimi içindeki paragraf"),
        "<w:customXml w:element=\"x\">%s</w:customXml>" % p("Özel XML içindeki paragraf"),
        p("", ek=GORSEL),
        p("Ana metin", ek=KUTU),
        tablo,
        p("Prototip:", ek=OLE % "rIdOle1"),
        p("", ek=OLE % "rIdOle2"),
        p("", ek=OLE % "rIdOle3"),
        '<w:altChunk r:id="rIdAlt"/>',
        p("Standart yapıda değiştirilen nesneler (Repair)", stil="Heading2"),
        p("Türetilmiş başlık", stil="OzelBaslik"),
        "<w:sectPr/>",
    ])


def docx_yaz(yol, govde, rels=None, ekler=None, stiller=STILLER):
    xmlns = " ".join('xmlns:%s="%s"' % kv for kv in NS.items())
    belge = '<?xml version="1.0" encoding="UTF-8"?><w:document %s><w:body>%s</w:body></w:document>' % (xmlns, govde)
    rels = rels if rels is not None else [
        ("rIdImg", "image", "media/image1.png"), ("rIdOle1", "oleObject", "embeddings/oleObject1.bin"),
        ("rIdOle2", "oleObject", "embeddings/oleObject2.bin"), ("rIdOle3", "oleObject", "embeddings/oleObject3.bin"),
        ("rIdAlt", "aFChunk", "afchunk1.htm")]
    rels_xml = '<Relationships xmlns="%s">%s</Relationships>' % (PKG_REL, "".join(
        '<Relationship Id="%s" Type="%s%s" Target="%s"/>' % (i, REL, t, h) for i, t, h in rels))
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<Types xmlns="%s"/>' % CT)
        z.writestr("word/document.xml", belge)
        z.writestr("word/_rels/document.xml.rels", rels_xml)
        z.writestr("word/styles.xml", stiller)
        for ad, veri in (ekler or {}).items():
            z.writestr(ad, veri)


def ornek_ekler(gecici):
    png = os.path.join(gecici, "g.png")
    write_png(png)
    with open(png, "rb") as fh:
        png_b = fh.read()
    return {
        "word/media/image1.png": png_b,
        "word/media/image2.emf": b"EMF-ikon",
        "word/embeddings/oleObject1.bin": cfb_yaz([("\x01Ole10Native", ole10native_yaz("ekran6.html", PROTOTIP_BUYUK)),
                                                   ("\x01CompObj", b"\x01\x00\xfe\xff")]),
        "word/embeddings/oleObject2.bin": cfb_yaz([("\x01Ole10Native",
                                                    ole10native_yaz("giris.html", PROTOTIP_KUCUK, False))]),
        "word/embeddings/oleObject3.bin": cfb_yaz([("Gizemli", b"\x00" * 100)]),
        "word/embeddings/Microsoft_Excel_Worksheet.xlsx": _kucuk_zip(),
        "word/afchunk1.htm": ALTCHUNK,
    }


def _kucuk_zip():
    import io
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", "<workbook/>")
    return b.getvalue()

DENKLEM = ('<w:p><w:r><w:t xml:space="preserve">Tutar formülü: </w:t></w:r><m:oMathPara><m:oMath><m:r>'
           '<m:t>Tutar=Miktar×BirimFiyat−İskonto</m:t></m:r></m:oMath></m:oMathPara></w:p>')
SMARTART = ('<w:p><w:r><w:drawing><wp:inline><a:graphic><a:graphicData><dgm:relIds r:dm="rIdDm" r:lo="rIdLo"/>'
            '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
GRAFIK = ('<w:p><w:r><w:drawing><wp:inline><a:graphic><a:graphicData><c:chart r:id="rIdCh"/>'
          '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
DIYAGRAM_VERI = ('<dgm:dataModel xmlns:dgm="%s" xmlns:a="%s"><dgm:ptLst>'
                 '<dgm:pt><dgm:t><a:p><a:r><a:t>Adım 1: Satış temsilcisi </a:t></a:r><a:r><a:t>talep açar</a:t></a:r>'
                 '</a:p></dgm:t></dgm:pt>'
                 '<dgm:pt><dgm:t><a:p><a:r><a:t>Adım 2: Bölge müdürü 50.000 TL üstünü onaylar</a:t></a:r></a:p>'
                 '</dgm:t></dgm:pt><dgm:pt><dgm:prSet phldrT="[Metin]"/></dgm:pt></dgm:ptLst></dgm:dataModel>'
                 % (NS["dgm"], NS["a"]))
GRAFIK_VERI = ('<c:chartSpace xmlns:c="%s" xmlns:a="%s"><c:chart><c:title><c:tx><c:rich><a:p><a:r>'
               '<a:t>Bölge bazında iade oranı</a:t></a:r></a:p></c:rich></c:tx></c:title><c:plotArea><c:barChart>'
               '<c:ser><c:tx><c:strRef><c:strCache><c:pt idx="0"><c:v>İade %%</c:v></c:pt></c:strCache></c:strRef>'
               '</c:tx><c:cat><c:strRef><c:strCache><c:pt idx="0"><c:v>Marmara</c:v></c:pt></c:strCache></c:strRef>'
               '</c:cat><c:val><c:numRef><c:numCache><c:pt idx="0"><c:v>0.12</c:v></c:pt></c:numCache></c:numRef>'
               '</c:val></c:ser></c:barChart></c:plotArea></c:chart></c:chartSpace>' % (NS["c"], NS["a"]))
NESNE_RELS = [("rIdDm", "diagramData", "diagrams/data1.xml"), ("rIdCh", "chart", "charts/chart1.xml")]
NESNE_EKLER = {"word/diagrams/data1.xml": DIYAGRAM_VERI, "word/charts/chart1.xml": GRAFIK_VERI,
               # Word'ün önbellek çizimi: aynı metni yineler, SAYILMAZ (yalnız data*.xml SmartArt'ın kaynağıdır)
               "word/diagrams/drawing1.xml": DIYAGRAM_VERI}


def nesneli_govde():
    return p("Süreç", stil="Balk1") + DENKLEM + SMARTART + GRAFIK + p("Son") + "<w:sectPr/>"


# ── BÖLÜM: cikar testleri ──
class _Gecici(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="kaynak_paketi_")
        self.addCleanup(shutil.rmtree, self.d, True)
        # Çalışma dizini geçici dizine alınır: hedef verilmeyen bir çağrı repoya ya da kullanıcı dizinine yazamaz.
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.d)
        self.kaynak = os.path.join(self.d, "istek.docx")
        docx_yaz(self.kaynak, ornek_govde(), ekler=ornek_ekler(self.d))
        self.kok = os.path.join(self.d, "proje", ".axet-code", "tmp")

    def cikar(self, kaynak=None, *ek):
        return call_main(kp.main, ["cikar", kaynak or self.kaynak, "--hedef-kok", self.kok, "--id", "p1", *ek])

    def paket(self, *yol):
        return os.path.join(self.kok, "p1", *yol)

    def oku(self, *yol):
        with open(self.paket(*yol), encoding="utf-8") as fh:
            return fh.read()


class KaynakPaketiDocxTest(_Gecici):
    def test_docx_paket_dogrulama_pass_ve_sayimlar(self):
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        self.assertIn("KAPSAM (SCOPE)", out)
        self.assertIn("DOĞRULAMA: PASS", out)
        meta = json.loads(self.oku("paket.json"))
        self.assertEqual({"km": 14, "baslik": 3, "tablo": 1, "tablo_satiri": 5, "gorsel": 2, "gomulu": 5},
                         {k: meta["sayim"]["kaynak"][k] for k in ("km", "baslik", "tablo", "tablo_satiri", "gorsel",
                                                                   "gomulu")})
        self.assertEqual(meta["sayim"]["kaynak"], {k: meta["sayim"]["paket"][k] for k in meta["sayim"]["kaynak"]})
        self.assertIn("DOĞRULAMA: **PASS**", self.oku("INDEX.md"))

    def test_metin_mekanik_sira_ve_isaretler(self):
        self.cikar()
        metin = self.oku("metin.md")
        sira = ["Giriş", "Birinci paragraf devam | çizgi", "Liste öğesi", "İçerik denetimi içindeki paragraf",
                "Özel XML içindeki paragraf", "KG-01 görsel", "Ana metin Kutu metni", "TS-01 | Sipariş kaydı",
                "Prototip:", "KN-05 gömülü (altChunk)", "Standart yapıda değiştirilen nesneler (Repair)"]
        konum = [metin.find(s) for s in sira]
        self.assertNotIn(-1, konum, list(zip(sira, konum)))
        self.assertEqual(sorted(konum), konum, "kaynak sırası korunmalı")
        self.assertEqual(1, metin.count("Kutu metni"), "mc:Fallback içindeki yinelenen metin alınmamalı")
        self.assertIn("## [KM-0013] Standart yapıda", metin)
        self.assertIn("# [KM-0014] Türetilmiş başlık", metin, "basedOn zinciriyle başlık seviyesi")
        self.assertIn(r"| TS-03 | a\|b \¶ c\\d | x |", metin, "hücredeki | ¶ ters bölü kaçırılır")
        self.assertIn("iç A ¶ iç B ¶ sonra", metin)
        self.assertNotIn("⟦T01.S05⟧", metin, "boş satır kaynak maddesi değildir")

    def test_ole_paket_nesnesi_asil_dosya_buyuk_ve_mini_akis(self):
        self.cikar()
        with open(self.paket("gomulu", "KN-02_ekran6.html"), "rb") as fh:
            self.assertEqual(PROTOTIP_BUYUK, fh.read(), "4096+ bayt: normal sektör zinciri")
        with open(self.paket("gomulu", "KN-03_giris.html"), "rb") as fh:
            self.assertEqual(PROTOTIP_KUCUK, fh.read(), "küçük akış: mini akış + UTF-16 kopyasız ad")
        index = self.oku("INDEX.md")
        self.assertIn("OLE paket nesnesi (asıl dosya çıkarıldı)", index)
        self.assertIn("| KN-04 | `word/embeddings/oleObject3.bin` | `gomulu/KN-04_oleObject3.bin` | TANINMADI", index)
        self.assertIn("TANINMAYAN gömülü nesne: KN-04", index)
        with open(self.paket("gomulu", "KN-05_afchunk1.htm"), "rb") as fh:
            self.assertEqual(ALTCHUNK, fh.read())
        self.assertTrue(os.path.isfile(self.paket("gomulu", "KN-01_Microsoft_Excel_Worksheet.xlsx")))
        self.assertTrue(os.path.isfile(self.paket("media", "KG-01_image1.png")))

    def test_cikarim_satir_dusururse_dogrulama_fail(self):
        """Koruma: çıkarım bir tablo satırını kaybederse (modelin kısaltması gibi) bağımsız sayım bunu yakalar."""
        asil = kp._satirlar

        def eksik(el):
            return list(asil(el))[:-1]
        with mock.patch.object(kp, "_satirlar", eksik):
            rc, out, err = self.cikar()
        self.assertEqual(1, rc, out + err)
        self.assertIn("DOĞRULAMA: FAIL", out)
        self.assertIn("tablo satırı (metinli): kaynak 5 ≠ paket 4", out)
        self.assertIn("DOĞRULAMA: **FAIL**", self.oku("INDEX.md"))

    def test_cikarim_paragraf_kaybederse_fail(self):
        """Koruma: çıkarım (ya da elle düzenleme) bir paragrafı kaybederse madde sayısı ve sıra ayrılır.
        Kontrol grubu: iç içe bilinmeyen kapsayıcı (customXml > smartTag) kayıpsız gezilir → PASS."""
        govde = ornek_govde().replace('<w:customXml w:element="x">', '<w:customXml w:element="x"><w:smartTag>') \
            .replace("</w:customXml>", "</w:smartTag></w:customXml>")
        docx_yaz(self.kaynak, govde, ekler=ornek_ekler(self.d))
        rc, out, _ = self.cikar()
        self.assertEqual(0, rc, out)
        orijinal = kp.docx_cikar

        def kapsayicisiz(z, *a):
            c = orijinal(z, *a)
            c.satirlar = [s for s in c.satirlar if "Özel XML" not in s]
            return c
        with mock.patch.object(kp, "docx_cikar", kapsayicisiz):
            rc, out, _ = self.cikar()
        self.assertEqual(1, rc, out)
        self.assertIn("kaynak maddesi (KM: başlık + paragraf + tablo satırı + metinli nesne): kaynak 14 ≠ paket 13",
                      out)

    def test_eski_artik_dosya_fail_verir(self):
        os.makedirs(self.paket("media"), exist_ok=True)
        with open(self.paket("media", "eski.png"), "wb") as fh:
            fh.write(b"x")
        rc, out, _ = self.cikar()
        self.assertEqual(1, rc, out)
        self.assertIn("görsel (KG): kaynak 2 ≠ paket 3", out)

    def test_yeniden_kosum_ayni_klasor_pass(self):
        self.assertEqual(0, self.cikar()[0])
        with open(self.paket("metin.md"), encoding="utf-8") as fh:
            ilk = fh.read()
        self.assertEqual(0, self.cikar()[0])
        self.assertEqual(ilk, self.oku("metin.md"))

    def test_varsayilan_hedef_calisma_dizini_ve_icerik_ozeti(self):
        proje = os.path.join(self.d, "proje")
        os.makedirs(proje)
        r = run_py("kaynak_paketi.py", "cikar", self.kaynak, cwd=proje)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        kok = os.path.join(proje, ".axet-code", "tmp")
        klasorler = os.listdir(kok)
        self.assertEqual(1, len(klasorler))
        self.assertRegex(klasorler[0], r"^istek-[0-9a-f]{8}$")
        self.assertNotIn("DIŞINDA", r.stdout)

    def test_desteklenmeyen_ve_bozuk_girdi(self):
        pdf = os.path.join(self.d, "istek.pdf")
        with open(pdf, "wb") as fh:
            fh.write(b"%PDF-1.4")
        rc, out, _ = self.cikar(pdf)
        self.assertEqual(3, rc)
        self.assertIn("DESTEKLENMİYOR", out)
        self.assertIn("yeniden yazarak paket ÜRETME", out)
        self.assertFalse(os.path.exists(self.paket()), "desteklenmeyen girdide paket klasörü açılmaz")
        bozuk = os.path.join(self.d, "bozuk.docx")
        with open(bozuk, "wb") as fh:
            fh.write(b"zip degil")
        rc, _out, err = self.cikar(bozuk)
        self.assertEqual(2, rc)
        self.assertIn("ÖLÇÜLEMEDİ", err)


class KaynakPaketiXlsxTest(_Gecici):
    def test_xlsx_satirlar_ve_sayfalar(self):
        xl = kp.xlsx_okuyucu()
        self.assertIsNotNone(xl, "office-excel/xlsx_lite klonda olmalı")
        yol = os.path.join(self.d, "liste.xlsx")
        xl.write_xlsx(yol, [("Testler", [["No", "Senaryo"], ["TS-01", "Kayıt"], ["", ""], ["TS-02", 3.0]]),
                            ("Notlar", [["Tek satır"]])])
        rc, out, err = self.cikar(yol)
        self.assertEqual(0, rc, out + err)
        metin = self.oku("metin.md")
        self.assertIn("## Sayfa SY01: Testler", metin)
        self.assertIn("[KM-0003] ⟦SY01.S0004⟧ | TS-02 | 3 |", metin)
        self.assertIn("[KM-0004] ⟦SY02.S0001⟧ | Tek satır |", metin)
        meta = json.loads(self.oku("paket.json"))
        self.assertEqual(4, meta["km_toplam"])
        self.assertEqual(2, meta["sayim"]["kaynak"]["sayfa"])

    def _xlsx(self, ekler=None):
        xl = kp.xlsx_okuyucu()
        yol = os.path.join(self.d, "liste.xlsx")
        xl.write_xlsx(yol, [("Gereksinim", [["No", "Kural", "Tutar", "Aktif"],
                                            ["R-01", "Kredi limiti aşılırsa sipariş bloke edilir", 1500.5, True],
                                            [None, None, "C3 metni", None]])])
        if ekler:
            with zipfile.ZipFile(yol, "a", zipfile.ZIP_DEFLATED) as z:
                for ad, veri in ekler.items():
                    z.writestr(ad, veri)
        return yol

    def test_xlsx_metin_hucresi_karakteri_sayilir_kontrol_pass(self):
        """Kontrol grubu: sayı/mantıksal hücre biçimlense de (1500.5 / True) yalnız metin hücreleri sayılır → PASS."""
        rc, out, err = self.cikar(self._xlsx())
        self.assertEqual(0, rc, out + err)
        meta = json.loads(self.oku("paket.json"))
        self.assertEqual(meta["sayim"]["kaynak"]["karakter"], meta["sayim"]["paket"]["karakter"])
        self.assertEqual(len("NoKuralTutarAktifR-01Kredilimitiaşılırsasiparişblokeedilir") + len("C3metni"),
                         meta["sayim"]["kaynak"]["karakter"])

    def test_xlsx_hucre_metni_kisalirsa_fail(self):
        """F2 koruması: okuyucu metin hücresini kısaltırsa (modelin özetlemesi gibi) karakter sayımı FAIL verir."""
        yol = self._xlsx()
        xl = kp.xlsx_okuyucu()
        asil = xl.read_rows

        def kisaltan(y, sno):
            ad, satirlar = asil(y, sno)
            return ad, [[(v[:5] if isinstance(v, str) else v) for v in s] for s in satirlar]
        with mock.patch.object(xl, "read_rows", kisaltan):
            rc, out, _ = self.cikar(yol)
        self.assertEqual(1, rc, out)
        self.assertIn("metin karakteri (boşluksuz; xlsx'te yalnız metin hücreleri): kaynak", out)

    def test_xlsx_cizim_metin_kutusu_ve_grafik(self):
        cizim = ('<xdr:wsDr xmlns:xdr="%sdrawingml/2006/spreadsheetDrawing" xmlns:a="%s"><xdr:twoCellAnchor>'
                 '<xdr:sp><xdr:txBody><a:p><a:r><a:t>Not: onay iki aşamalı</a:t></a:r></a:p></xdr:txBody></xdr:sp>'
                 '</xdr:twoCellAnchor><xdr:twoCellAnchor><xdr:sp><xdr:txBody><a:p/></xdr:txBody></xdr:sp>'
                 '</xdr:twoCellAnchor></xdr:wsDr>') % (_S, NS["a"])
        rc, out, err = self.cikar(self._xlsx({"xl/drawings/drawing1.xml": cizim, "xl/charts/chart1.xml": GRAFIK_VERI}))
        self.assertEqual(0, rc, out + err)
        metin = self.oku("metin.md")
        self.assertIn("⟦K01 metin kutusu: xl/drawings/drawing1.xml⟧ | Not: onay iki aşamalı |", metin)
        self.assertIn("⟦G01 grafik: xl/charts/chart1.xml⟧ | Bölge bazında iade oranı | İade % | Marmara | 0.12 |", metin)
        sayim = json.loads(self.oku("paket.json"))["sayim"]["kaynak"]
        self.assertEqual((1, 1), (sayim["metin_kutusu"], sayim["grafik"]), "metinsiz kutu sayılmaz")

    def test_xlsx_okuyucu_yoksa_desteklenmiyor(self):
        yol = os.path.join(self.d, "liste.xlsx")
        kp.xlsx_okuyucu().write_xlsx(yol, [("S", [["a"]])])
        with mock.patch.object(kp, "xlsx_okuyucu", return_value=None):
            rc, out, _ = self.cikar(yol)
        self.assertEqual(3, rc)
        self.assertIn("DESTEKLENMİYOR", out)

class NesneMetniTest(_Gecici):
    """F1: denklem, SmartArt ve grafik metni pakete girer; bağımsız sayım bunları AYRI sayar."""

    def setUp(self):
        super().setUp()
        docx_yaz(self.kaynak, nesneli_govde(), rels=NESNE_RELS, ekler=NESNE_EKLER)

    def test_denklem_smartart_grafik_metni_pakette(self):
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        metin = self.oku("metin.md")
        self.assertIn("[KM-0002] Tutar formülü: ⟦denklem⟧ Tutar=Miktar×BirimFiyat−İskonto", metin)
        self.assertIn("⟦D01 SmartArt: word/diagrams/data1.xml⟧ | Adım 1: Satış temsilcisi talep açar | "
                      "Adım 2: Bölge müdürü 50.000 TL üstünü onaylar |", metin)
        self.assertIn("⟦G01 grafik: word/charts/chart1.xml⟧ | Bölge bazında iade oranı | İade % | Marmara | 0.12 |", metin)
        self.assertLess(metin.index("Tutar formülü"), metin.index("D01 SmartArt"), "nesne konumunda yazılır")
        self.assertLess(metin.index("D01 SmartArt"), metin.index("[KM-0005] Son"))
        meta = json.loads(self.oku("paket.json"))
        k = meta["sayim"]["kaynak"]
        self.assertEqual((1, 1, 1, 5), (k["denklem"], k["diyagram"], k["grafik"], k["km"]))
        self.assertEqual(k, {a: meta["sayim"]["paket"][a] for a in k})
        self.assertIn("D01 SmartArt `word/diagrams/data1.xml`", self.oku("INDEX.md"))

    def test_smartart_dusurulurse_fail(self):
        """Koruma: çıkarım nesnenin metnini düşürürse parça hesabı (evren süpürmesi, ayrı kod) FAIL verir."""
        with mock.patch.object(kp, "nesne_hucreleri", return_value=[]):
            rc, out, _ = self.cikar()
        self.assertEqual(1, rc, out)
        self.assertRegex(out, r"parça word/diagrams/data1\.xml: kaynak metni [1-9]\d* ≠ pakette 0")
        self.assertRegex(out, r"parça word/charts/chart1\.xml: kaynak metni [1-9]\d* ≠ pakette 0")
        self.assertIn("metin yok", self.oku("metin.md"))

    def test_denklem_dusurulurse_fail(self):
        with mock.patch.object(kp, "_denklem_metni", return_value=""):
            rc, out, _ = self.cikar()
        self.assertEqual(1, rc, out)
        self.assertIn("denklem: kaynak 1 ≠ paket 0", out)

    def test_govdede_konumu_olmayan_nesne_sonda_yazilir(self):
        govde = p("Süreç") + "<w:sectPr/>"   # grafik gövdeden bağlı değil (ör. üstbilgiden)
        docx_yaz(self.kaynak, govde, rels=[], ekler={"word/charts/chart1.xml": GRAFIK_VERI})
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        metin = self.oku("metin.md")
        self.assertIn("## Gövdede konumu bulunamayan metin nesneleri", metin)
        self.assertIn("[KM-0002] ⟦G01 grafik: word/charts/chart1.xml⟧", metin)

    def test_okunamayan_nesne_parcasi_isaretlenir_ve_fail(self):
        bozuk = DIYAGRAM_VERI.replace("</dgm:dataModel>", "")
        docx_yaz(self.kaynak, nesneli_govde(), rels=NESNE_RELS,
                 ekler=dict(NESNE_EKLER, **{"word/diagrams/data1.xml": bozuk}))
        rc, out, _ = self.cikar()
        self.assertEqual(1, rc, out)
        self.assertIn("⟦D01 SmartArt: word/diagrams/data1.xml⟧ metin alınmadı (parça okunamadı)", self.oku("metin.md"))

    def test_metin_kutusu_icinde_tablo_pass(self):
        """F8: metin kutusundaki tablo bulunduğu paragrafın satırına düzleşir; sayım tanımı aynı → PASS."""
        ic = "<w:tbl>%s%s</w:tbl>" % (satir("Alan", "Kural"), satir("KUNNR", "zorunlu"))
        kutu = "<w:r><w:drawing><wps:txbx><w:txbxContent>%s</w:txbxContent></wps:txbx></w:drawing></w:r>" % (
            ic + p("kutu sonu"))
        docx_yaz(self.kaynak, p("Ana", ek=kutu) + "<w:sectPr/>", rels=[])
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        self.assertIn("[KM-0001] Ana Alan Kural KUNNR zorunlu kutu sonu", self.oku("metin.md"))
        self.assertEqual(0, json.loads(self.oku("paket.json"))["sayim"]["kaynak"]["tablo"])


class SaglamlikTest(_Gecici):
    """F3/F4/F9: bozuk ya da kötü niyetli girdi paketi düşürmez, sonsuz/aşırı iş yaptırmaz, dışarı yazdıramaz."""

    def _ole_docx(self, ole_bin):
        docx_yaz(self.kaynak, p("Metin") + p("", ek=OLE % "rIdOle1") + "<w:sectPr/>",
                 rels=[("rIdOle1", "oleObject", "embeddings/oleObject1.bin")],
                 ekler={"word/embeddings/oleObject1.bin": ole_bin})

    def test_kesik_cfb_cfbhata_ve_paket_taninmadi_ile_gecer(self):
        iyi = cfb_yaz([("\x01Ole10Native", ole10native_yaz("a.html", b"<html>x</html>"))])
        with self.assertRaises(kp.CfbHata):
            kp.cfb_akislari(iyi[:512 + 100])
        self._ole_docx(iyi[:512 + 100])
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        self.assertIn("TANINMADI — OLE okunamadı (kısa sektör", self.oku("INDEX.md"))

    def test_kesik_akis_kisa_icerik_verilmez(self):
        akis = ole10native_yaz("b.html", PROTOTIP_BUYUK)
        buyuk = cfb_yaz([("\x01Ole10Native", akis)])
        son = len(akis) % 512 or 512   # akışın son sektöründeki veri baytı (dosyanın son sektörü bu akışınki)
        self.assertGreater(son, 1)
        with self.assertRaises(kp.CfbHata) as cm:
            kp.cfb_akislari(buyuk[:len(buyuk) - 512 + son // 2])  # son sektör yarım: akışın sonu kesik
        self.assertIn("kısa", str(cm.exception))

    def test_gomulu_cozumde_beklenmeyen_hata_ham_kopya(self):
        self._ole_docx(cfb_yaz([("Gizemli", b"x" * 10)]))
        with mock.patch.object(kp, "cfb_akislari", side_effect=RuntimeError("deneme")):
            rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        self.assertIn("TANINMADI — çözümlenemedi (RuntimeError: deneme); ham kopya", self.oku("INDEX.md"))

    def test_dongulu_difat_sinirli_is(self):
        bas = kp.CFB_IMZA + b"\x00" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\x00" * 6
        bas += struct.pack("<IIIIIIIII", 0, 0xFFFFFFFF, 0, 0, 4096, ENDOFCHAIN, 0, 0, 1000)
        bas += struct.pack("<109I", *([0] * 109))
        data = bas + struct.pack("<128I", *([0] * 128))   # tek DIFAT sektörü kendine işaret ediyor
        say = {"n": 0}
        asil = struct.unpack_from

        def sayan(*a, **k):
            say["n"] += 1
            return asil(*a, **k)
        with mock.patch.object(kp.struct, "unpack_from", sayan):
            with self.assertRaises(kp.CfbHata):
                kp.cfb_akislari(data)
        self.assertLessEqual(say["n"], 10, "DIFAT/FAT boyu dosyadaki sektör sayısıyla sınırlı olmalı")

    def test_dongulu_difat_ziyaret_kumesiyle_kesilir(self):
        """Sektör sayısı sınırı döngüyü tek başına kesmez (çevrim boyu < sınır ise küme büyümez): ziyaret kümesi şart."""
        bas = kp.CFB_IMZA + b"\x00" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\x00" * 6
        bas += struct.pack("<IIIIIIIII", 0, 0xFFFFFFFF, 0, 0, 4096, ENDOFCHAIN, 0, 0, 1000)
        bas += struct.pack("<109I", *([FREESECT] * 109))
        data = bas + struct.pack("<128I", *([FREESECT] * 127 + [0])) + b"\x00" * (512 * 3)  # 4 sektör, DIFAT 0 → 0
        say = {"n": 0}
        asil = struct.unpack_from

        def sinirli(*a, **k):
            say["n"] += 1
            if say["n"] > 200:
                raise AssertionError("DIFAT döngüsü kesilmedi (200 okuma)")
            return asil(*a, **k)
        with mock.patch.object(kp.struct, "unpack_from", sinirli):
            with self.assertRaises(kp.CfbHata) as cm:
                kp.cfb_akislari(data)
        self.assertEqual("DIFAT zinciri döngülü", str(cm.exception))

    def test_ic_ayristirma_hatasi_cfbhata_olur(self):
        """F3: iç okuyucunun struct/indeks hatası çağırana sızmaz, CfbHata'ya çevrilir (gömülü çözüm onu yakalar)."""
        for hata in (struct.error("unpack requires a buffer"), IndexError("x"), UnicodeDecodeError("utf-16", b"", 0, 1, "y")):
            with mock.patch.object(kp, "_cfb_akislari", side_effect=hata):
                with self.assertRaises(kp.CfbHata) as cm:
                    kp.cfb_akislari(b"")
            self.assertIn("bozuk CFB (%s" % type(hata).__name__, str(cm.exception))

    def test_ole10native_yol_gecisli_ad_paket_disina_yazmaz(self):
        adlar = ["..\\..\\..\\kotu.html", "C:\\Windows\\Temp\\kotu2.html", "/etc/kotu3.html", "..", "CON",
                 "a/../../b.html"]
        for i, ad in enumerate(adlar):
            self._ole_docx(cfb_yaz([("\x01Ole10Native", ole10native_yaz(ad, b"X"))]))
            rc, out, err = call_main(kp.main, ["cikar", self.kaynak, "--hedef-kok", self.kok, "--id", "y%d" % i])
            self.assertEqual(0, rc, out + err)
            gomulu = os.path.join(self.kok, "y%d" % i, "gomulu")
            dosyalar = os.listdir(gomulu)
            self.assertEqual(1, len(dosyalar), (ad, dosyalar))
            self.assertTrue(dosyalar[0].startswith("KN-01_"), (ad, dosyalar))
            self.assertNotRegex(dosyalar[0], r"[\\/:]", ad)
            self.assertEqual(os.path.realpath(gomulu), os.path.dirname(os.path.realpath(os.path.join(gomulu,
                                                                                                      dosyalar[0]))))
        self.assertEqual(["g.png", "istek.docx", "proje"], sorted(os.listdir(self.d)), "paket dışına dosya yazılmadı")
        self.assertEqual(["tmp"], os.listdir(os.path.join(self.d, "proje", ".axet-code")))

    def test_boyut_siniri_olculemedi(self):
        """Ö1: sınırı aşan METİN parçası ve toplam → çıkış 2, paket yazılmaz; sınırı aşan görsel atlanır, çıkarım sürer
        (yer tutucu dosya + INDEX'te ÖLÇÜLEMEDİ — boyut)."""
        docx_yaz(self.kaynak, p("x" * 5000) + "<w:sectPr/>", rels=[])
        with mock.patch.object(kp, "MAX_UYE", 4000):
            rc, _out, err = self.cikar()
        self.assertEqual(2, rc)
        self.assertIn("boyut sınırı: word/document.xml açılınca 4000 bayttan fazla (sınır 4000)", err)
        self.assertFalse(os.path.exists(self.paket()), "sınırı aşan girdide paket yazılmaz")
        with mock.patch.object(kp, "MAX_TOPLAM", 4500):
            rc, _out, err = self.cikar()
        self.assertEqual(2, rc)
        self.assertIn("boyut sınırı: açılmış toplam", err)
        docx_yaz(self.kaynak, p("x") + "<w:sectPr/>", rels=[], ekler={"word/media/b.bin": b"\x00" * 5000})
        with mock.patch.object(kp, "MAX_UYE", 4000):
            rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        self.assertEqual(["KG-01_b.bin.OLCULEMEDI.txt"], os.listdir(self.paket("media")))
        self.assertIn("ÖLÇÜLEMEDİ — boyut", self.oku("media", "KG-01_b.bin.OLCULEMEDI.txt"))
        self.assertIn("ÖLÇÜLEMEDİ — boyut: word/media/b.bin", self.oku("INDEX.md"))
        self.assertIn("| KG-01 | `word/media/b.bin` | `media/KG-01_b.bin.OLCULEMEDI.txt` | ÖLÇÜLEMEDİ — boyut",
                      self.oku("INDEX.md"))

    def test_beklenmeyen_hata_fail_degil_olculemedi(self):
        with mock.patch.object(kp, "docx_cikar", side_effect=RuntimeError("deneme")):
            rc, _out, err = self.cikar()
        self.assertEqual(2, rc, "yakalanmayan hata Python'un çıkış 1'i olup FAIL ile karışmasın")
        self.assertIn("beklenmeyen hata (RuntimeError: deneme)", err)


# ── BÖLÜM: evren süpürmesi / geri düşüş testleri (F10) ──
CX = "http" + "://schemas.microsoft.com/office/drawing/2014/chartex"
WP14 = "http" + "://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
CDR = _S + "drawingml/2006/chartDrawing"
CHARTEX = ('<cx:chartSpace xmlns:cx="%s"><cx:chartData><cx:data id="0"><cx:strDim type="cat"><cx:lvl ptCount="2">'
           '<cx:pt idx="0">Ege</cx:pt><cx:pt idx="1">Akdeniz</cx:pt></cx:lvl></cx:strDim><cx:numDim type="val">'
           '<cx:lvl ptCount="2"><cx:pt idx="0">5</cx:pt><cx:pt idx="1">7</cx:pt></cx:lvl></cx:numDim></cx:data>'
           '</cx:chartData></cx:chartSpace>' % CX)
KONUM = ('<wp:positionH><mc:AlternateContent><mc:Choice Requires="wp14"><wp14:pctPosHOffset xmlns:wp14="%s">91000'
         '</wp14:pctPosHOffset></mc:Choice><mc:Fallback><wp:posOffset>7077075</wp:posOffset></mc:Fallback>'
         '</mc:AlternateContent></wp:positionH>' % WP14)


def kutu(choice, fallback, konum=""):
    """Metin kutusu: Choice (DrawingML) + Fallback (VML). choice None → Choice'suz AlternateContent."""
    ch = ('<mc:Choice Requires="wps"><w:drawing><wp:anchor>%s<wps:txbx><w:txbxContent>%s</w:txbxContent></wps:txbx>'
          '</wp:anchor></w:drawing></mc:Choice>' % (konum, p(choice))) if choice is not None else ""
    return ('<w:r><mc:AlternateContent>%s<mc:Fallback><w:pict><v:textbox><w:txbxContent>%s</w:txbxContent>'
            '</v:textbox></w:pict></mc:Fallback></mc:AlternateContent></w:r>' % (ch, p(fallback)))


class EvrenGeriDususTest(_Gecici):
    def docx(self, govde, ekler=None, rels=None):
        docx_yaz(self.kaynak, govde + "<w:sectPr/>", rels=rels or [], ekler=ekler)
        rc, out, err = self.cikar()
        return rc, out + err, self.oku("metin.md") if os.path.exists(self.paket("metin.md")) else ""

    def test_bilinmeyen_parca_geri_dususte_pass(self):
        """F10: parça listesinde olmayan bir XML parçasının metni pakete girer (geri düşüş) ve doğrulama PASS."""
        rc, out, metin = self.docx(p("Gövde"), ekler={
            "word/foo/bar1.xml": '<x:kok xmlns:x="urn:ornek"><x:a>Bilinmeyen parça metni</x:a></x:kok>'})
        self.assertEqual(0, rc, out)
        self.assertIn("[KM-0002] ⟦P01 parça: word/foo/bar1.xml⟧ | Bilinmeyen parça metni |", metin)
        index = self.oku("INDEX.md")
        self.assertIn("Geri düşüşe giden parçalar", index)
        self.assertIn("P01 `word/foo/bar1.xml`", index)
        self.assertIn("| `word/foo/bar1.xml` | geri düşüş | 20 | 0 | 0 | 20 |", index)
        meta = json.loads(self.oku("paket.json"))
        self.assertEqual(["word/foo/bar1.xml"], [g["parca"] for g in meta["geri_dusus"]])
        self.assertEqual(2, meta["km_toplam"])

    def test_ust_altbilgi_dipnot_yorum_geri_dususte(self):
        """Eskiden 'metin.md'ye alınmadı' notuyla dışarıda kalan parçalar artık metin olarak pakette."""
        w = 'xmlns:w="%s"' % NS["w"]
        rc, out, metin = self.docx(p("Gövde"), ekler={
            "word/header1.xml": "<w:hdr %s>%s</w:hdr>" % (w, p("Üst bilgi metni")),
            "word/footer1.xml": "<w:ftr %s>%s</w:ftr>" % (w, p("Alt bilgi metni")),
            "word/footnotes.xml": '<w:footnotes %s><w:footnote w:id="1">%s</w:footnote></w:footnotes>'
                                  % (w, p("Dipnot metni")),
            "word/comments.xml": '<w:comments %s><w:comment w:id="0">%s</w:comment></w:comments>'
                                 % (w, p("Yorum metni"))})
        self.assertEqual(0, rc, out)
        for parca, metin_ in (("word/comments.xml", "Yorum metni"), ("word/footer1.xml", "Alt bilgi metni"),
                              ("word/footnotes.xml", "Dipnot metni"), ("word/header1.xml", "Üst bilgi metni")):
            self.assertRegex(metin, r"\[KM-\d{4}\] ⟦P\d\d parça: %s⟧ \| %s \|" % (parca, metin_))
        self.assertNotIn("ALINMADI", self.oku("INDEX.md"))
        self.assertNotIn("alınmadı", self.oku("INDEX.md"))

    def test_chartex_kategorileri_docx_ve_xlsx(self):
        """n1: ChartEx kategori metni (cx:pt) grafik satırında; docx ve xlsx."""
        rc, out, metin = self.docx(p("Grafik"), ekler={"word/charts/chartEx1.xml": CHARTEX})
        self.assertEqual(0, rc, out)
        self.assertIn("⟦G01 grafik: word/charts/chartEx1.xml⟧ | Ege | Akdeniz | 5 | 7 |", metin)
        xl = kp.xlsx_okuyucu()
        yol = os.path.join(self.d, "grafik.xlsx")
        xl.write_xlsx(yol, [("Veri", [["Bölge"], ["Ege"]])])
        with zipfile.ZipFile(yol, "a") as z:
            z.writestr("xl/charts/chartEx1.xml", CHARTEX)
        rc, out, err = self.cikar(yol)
        self.assertEqual(0, rc, out + err)
        self.assertIn("⟦G01 grafik: xl/charts/chartEx1.xml⟧ | Ege | Akdeniz | 5 | 7 |", self.oku("metin.md"))

    def test_grafik_ustu_metin_kutusu_geri_dususte(self):
        """n7: grafiğin üstüne çizilen metin kutusu (userShapes → word/drawings/drawingN.xml) pakette, PASS."""
        us = ('<c:userShapes xmlns:c="%s" xmlns:cdr="%s" xmlns:a="%s"><cdr:relSizeAnchor><cdr:sp><cdr:txBody><a:p>'
              '<a:r><a:t>Not: Marmara Q3 verisi eksik</a:t></a:r></a:p></cdr:txBody></cdr:sp></cdr:relSizeAnchor>'
              '</c:userShapes>') % (NS["c"], CDR, NS["a"])
        rc, out, metin = self.docx(p("Grafik:") + GRAFIK, rels=[("rIdCh", "chart", "charts/chart1.xml")],
                                   ekler={"word/charts/chart1.xml": GRAFIK_VERI, "word/drawings/drawing1.xml": us})
        self.assertEqual(0, rc, out)
        self.assertIn("⟦P01 parça: word/drawings/drawing1.xml⟧ | Not: Marmara Q3 verisi eksik |", metin)

    def test_fallback_yalniz_choice_esitse_yok_sayilir(self):
        """Kural ②: Fallback yalnız karakteri eşit bir Choice varsa yok sayılır. Konum değeri (yok sayılan sınıf)
        yalnız Choice'ta durur ve eşitliği bozmaz; iç içe konum AlternateContent'i dış Choice'u yarıda kesmez."""
        govde = (p("Önce") + p("", ek=kutu("Aynı metin", "Aynı metin", KONUM)) + p("", ek=kutu("A", "Başka metin"))
                 + p("", ek=kutu(None, "Yalnız eski gösterim")))
        rc, out, metin = self.docx(govde)
        self.assertEqual(0, rc, out)
        self.assertEqual(1, metin.count("Aynı metin"), metin)
        self.assertRegex(metin, r"⟦P01 parça: word/document\.xml⟧ \| Başka metin \|")
        self.assertRegex(metin, r"⟦P01 parça: word/document\.xml⟧ \| Yalnız eski gösterim \|")
        # Dış Fallback "Aynı metin" (9) düşer. İç konum bloğunun net metni 0 olduğundan o Fallback düşmez; konum
        # değerleri (91000 + 7077075 = 12) kendi sınıfında sayılır.
        self.assertIn("yinelenen gösterim (mc:Fallback, Choice ile eşit) 9", out)
        self.assertIn("konum/ölçü değeri 12", out)

    def test_alan_kodu_yok_sayilir_alan_sonucu_alinir(self):
        """Kural ②: alan kodu sınıfı yalnız instrText; alan SONUCU (w:t) yapılandırılmış satırda."""
        alan = ('<w:p><w:r><w:t xml:space="preserve">Sayfa </w:t></w:r><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar '
                'w:fldCharType="separate"/></w:r><w:r><w:t>7</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
                '</w:p>')
        rc, out, metin = self.docx(alan)
        self.assertEqual(0, rc, out)
        self.assertIn("[KM-0001] Sayfa 7", metin)
        self.assertNotIn("PAGE", metin)
        self.assertIn("alan kodu (instrText) 4", out)

    def test_yok_sayilan_her_sinif_karakteriyle_basilir(self):
        """Koşul ①: her yok sayılan sınıf DOĞRULAMA satırında ve INDEX'te karakter sayısıyla (sıfır da) görünür."""
        rc, out, err = self.cikar()
        self.assertEqual(0, rc, out + err)
        dogrulama = [s for s in out.splitlines() if s.startswith("DOĞRULAMA:")][0]
        index = self.oku("INDEX.md")
        for sinif in kp.YOK_SINIFLAR:
            self.assertRegex(dogrulama, re.escape(sinif) + r" \d+")
            self.assertRegex(index, re.escape(sinif) + r" \d+")
        self.assertIn("yinelenen gösterim (mc:Fallback, Choice ile eşit) 9", dogrulama)  # KUTU: "Kutu metni"
        self.assertEqual(set(kp.YOK_SINIFLAR), set(json.loads(self.oku("paket.json"))["yok_sayilan"]))

    def test_definedname_yalniz_workbookta_yok_sayilir(self):
        """definedName yalnız xl/workbook.xml'de formül/başvuru sınıfıdır; başka parçada geri düşüşe gider."""
        xl = kp.xlsx_okuyucu()
        yol = os.path.join(self.d, "liste.xlsx")
        xl.write_xlsx(yol, [("Testler", [["No"], ["TS-01"]])])
        with zipfile.ZipFile(yol) as z:
            self.assertIn("definedName", z.read("xl/workbook.xml").decode("utf-8"), "fikstür ön koşulu")
        rc, out, err = self.cikar(yol)
        self.assertEqual(0, rc, out + err)
        self.assertRegex(out, r"formül / veri başvurusu \(f, definedName\) [1-9]\d*")
        self.assertNotIn("parça: xl/workbook.xml", self.oku("metin.md"))
        rc, out, metin = self.docx(p("Gövde"), ekler={
            "word/foo/ad.xml": '<x:kok xmlns:x="urn:ornek"><x:definedName>Gizli ad metni</x:definedName></x:kok>'})
        self.assertEqual(0, rc, out)
        self.assertIn("⟦P01 parça: word/foo/ad.xml⟧ | Gizli ad metni |", metin)
        self.assertIn("formül / veri başvurusu (f, definedName) 0", out)


def cfb_paylasimli(d=1, k=9):
    """Döngüsüz, geçerli zincirli CFB; tek kusur: 4*d-1 akış AYNI k sektörlük veri zincirini gösterir (gerçek CFB'de
    olmaz; paylaşım çıktıyı akış sayısıyla çarpar)."""
    toplam = d + k
    f = 1
    while (f + toplam + 127) // 128 > f:
        f += 1
    fat = [FREESECT] * (f * 128)
    for i in range(f):
        fat[i] = FATSECT
    dir0 = f
    for i in range(d):
        fat[dir0 + i] = dir0 + i + 1 if i < d - 1 else ENDOFCHAIN
    v0 = f + d
    for i in range(k):
        fat[v0 + i] = v0 + i + 1 if i < k - 1 else ENDOFCHAIN

    def girdi(ad, tur, bas, boy):
        a = ad.encode("utf-16-le") + b"\0\0"
        e = a.ljust(64, b"\0") + struct.pack("<HBB", len(a), tur, 1) + struct.pack("<III", NOSTREAM, NOSTREAM, NOSTREAM)
        return e + b"\0" * 36 + struct.pack("<IQ", bas, boy)
    dz = girdi("Root Entry", 5, ENDOFCHAIN, 0)
    for i in range(4 * d - 1):
        dz += girdi("s%d" % i, 2, v0, k * 512)
    bas = kp.CFB_IMZA + b"\0" * 16 + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + b"\0" * 6
    bas += struct.pack("<IIIIIIIII", 0, f, dir0, 0, 4096, ENDOFCHAIN, 0, ENDOFCHAIN, 0)
    bas += struct.pack("<109I", *(list(range(f)) + [FREESECT] * (109 - f)))
    return bas + struct.pack("<%dI" % len(fat), *fat) + dz + b"A" * (k * 512)


class BoyutVeCfbTest(_Gecici):
    def test_zip_basligi_boyu_kucuk_beyan_ederse_olculemedi(self):
        """F11: başlık açılmış boyu küçük beyan eder; üye gerçekten açılarak okunur → CRC/boy uyuşmazlığı ÖLÇÜLEMEDİ
        (çıkış 2), beyana güvenip devam edilmez."""
        docx_yaz(self.kaynak, p("x") + "<w:sectPr/>", rels=[], ekler={"word/media/b.bin": b"\x00" * 50000})
        with open(self.kaynak, "rb") as fh:
            b = bytearray(fh.read())
        yamalanan = 0
        for imza, ofs in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
            i = 0
            while True:
                i = b.find(imza, i)
                if i < 0:
                    break
                if struct.unpack_from("<I", b, i + ofs)[0] == 50000:
                    b[i + ofs:i + ofs + 4] = struct.pack("<I", 1000)
                    yamalanan += 1
                i += 4
        self.assertEqual(2, yamalanan, "fikstür ön koşulu: yerel + merkezi başlık")
        with open(self.kaynak, "wb") as fh:
            fh.write(bytes(b))
        rc, _out, err = self.cikar()
        self.assertEqual(2, rc, err)
        self.assertIn("zip üyesi açılamadı: word/media/b.bin", err)
        self.assertFalse(os.path.exists(self.paket()), "okunamayan girdide paket yazılmaz")

    def test_akisli_sayim_sinirda_keser(self):
        """F11: sayım üyeyi parça parça açar ve sınırı geçince durur (tamamını belleğe almadan)."""
        okunan = []
        gercek = zipfile.ZipExtFile.read

        def say(self_, n=-1):
            veri = gercek(self_, n)
            okunan.append(len(veri))
            return veri
        docx_yaz(self.kaynak, p("x" * 9000) + "<w:sectPr/>", rels=[])
        with mock.patch.object(kp, "MAX_UYE", 4000), mock.patch.object(kp, "OKUMA_PARCASI", 1000), \
                mock.patch.object(zipfile.ZipExtFile, "read", say):
            rc, _out, err = self.cikar()
        self.assertEqual(2, rc, err)
        self.assertTrue(okunan and max(okunan) <= 1000, okunan[:5])

    def test_cfb_paylasilan_sektor_cfbhata(self):
        """F12: bir sektörü iki akışın paylaşması CfbHata (çıktı akış sayısıyla çarpılmaz); kontrol grubu: normal CFB
        okunur."""
        with self.assertRaisesRegex(kp.CfbHata, "birden çok yerde kullanılıyor"):
            kp.cfb_akislari(cfb_paylasimli(1, 9))  # 9 sektör = 4608 bayt ≥ mini akış eşiği: düz FAT yolu
        self.assertEqual(b"veri", kp.cfb_akislari(cfb_yaz([("Akis", b"veri")]))["Akis"])


# ── BÖLÜM: iz testleri ──
IZ_TABLOSU = """# İz tablosu — FS-SD-001

| Kaynak | Belge kimliği | Not |
|---|---|---|
| KM-0001..KM-0003 | BİLGİ | giriş |
| KM-0004–KM-0006 | FR-001 | |
| KM-0007 | BİLGİ | tablo başlık satırı |
| KM-0008, KM-0009 | TC-01, TC-02 | |
| KM-0010..KM-0011 | KR-001 | |
| KM-0012 | SCR-001 | |
| KM-0013 | KAPSAM-DIŞI | standart nesne değişikliği istenmiyor |
| KM-0014 | FR-002 | |
| KG-01..KG-02 | BİLGİ | logo ve ikon |
| KN-01..KN-05 | SCR-001 | |
"""
BELGE = "FR-001 kayıt. FR-002 iptal. FR-003 öneri. KR-001 kural. TC-01, TC-02 test. SCR-001 ekran.\n"


class IzDenetimiTest(_Gecici):
    def setUp(self):
        super().setUp()
        self.assertEqual(0, self.cikar()[0])
        self.belge = os.path.join(self.d, "FS-SD-001.md")
        with open(self.belge, "w", encoding="utf-8") as fh:
            fh.write(BELGE)

    def iz(self, tablo_metni, *ek):
        tablo = self.paket("iz-FS-SD-001.md")
        with open(tablo, "w", encoding="utf-8") as fh:
            fh.write(tablo_metni)
        return call_main(kp.main, ["iz", self.paket(), "--tablo", tablo, "--belge", self.belge, *ek])

    def test_tam_tablo_pass_ve_kaynaksiz_gereksinim_uyarisi(self):
        rc, out, err = self.iz(IZ_TABLOSU)
        self.assertEqual(0, rc, out + err)
        self.assertIn("KAPSAM (SCOPE)", out)
        self.assertIn("kapsanan: 21/21", out)
        self.assertIn("UYARI kaynaksız gereksinim", out)
        self.assertIn("FR-003", out)
        self.assertIn("İNCELEYİCİNİN ELLE OKUYACAĞI (BİLGİ / KAPSAM-DIŞI işaretli satırlar — madde metni metin.md'de): 4",
                      out)
        self.assertIn("SONUÇ: PASS", out)

    def test_eksik_madde_fail(self):
        rc, out, _ = self.iz(IZ_TABLOSU.replace("| KM-0014 | FR-002 | |\n", ""))
        self.assertEqual(1, rc, out)
        self.assertIn("EKSİK — tabloda olmayan kaynak maddesi: 1", out)
        self.assertIn("  - KM-0014", out)

    def test_hayalet_madde_fail(self):
        rc, out, _ = self.iz(IZ_TABLOSU + "| KM-0099 | FR-001 | |\n")
        self.assertEqual(1, rc, out)
        self.assertIn("HAYALET — pakette olmayan madde: 1", out)

    def test_bos_ve_taninmayan_esleme_fail(self):
        rc, out, _ = self.iz(IZ_TABLOSU.replace("| KM-0014 | FR-002 | |", "| KM-0014 |  | |"))
        self.assertEqual(1, rc, out)
        self.assertIn("BOŞ EŞLEME: 1", out)
        rc, out, _ = self.iz(IZ_TABLOSU.replace("| KM-0014 | FR-002 | |", "| KM-0014 | bkz. yukarı | |"))
        self.assertEqual(1, rc, out)
        self.assertIn("TANINMAYAN EŞLEME — ne belge kimliği ne BİLGİ/KAPSAM-DIŞI: 1", out)

    def test_belgede_olmayan_kimlik_fail(self):
        rc, out, _ = self.iz(IZ_TABLOSU.replace("| KM-0014 | FR-002 | |", "| KM-0014 | FR-009 | |"))
        self.assertEqual(1, rc, out)
        self.assertIn("BELGEDE YOK — eşlenen kimlik belgede geçmiyor: 1", out)
        self.assertIn("FR-009", out)

    def test_kapsam_disi_gerekcesiz_fail(self):
        rc, out, _ = self.iz(IZ_TABLOSU.replace("| KAPSAM-DIŞI | standart nesne değişikliği istenmiyor |",
                                                "| kapsam dışı | |"))
        self.assertEqual(1, rc, out)
        self.assertIn("KAPSAM-DIŞI GEREKÇESİZ — not sütunu boş: 1", out)

    def test_metin_elle_degisirse_fail(self):
        metin = self.oku("metin.md").replace("[KM-0014] Türetilmiş başlık", "Türetilmiş başlık")
        with open(self.paket("metin.md"), "w", encoding="utf-8") as fh:
            fh.write(metin)
        rc, out, _ = self.iz(IZ_TABLOSU)
        self.assertEqual(1, rc, out)
        self.assertIn("paket.json ile (14) uyuşmuyor", out)

    def test_kaynak_sha256_tablo_ile_eslesir(self):
        sha = json.loads(self.oku("paket.json"))["kaynak"]["sha256"]
        rc, out, _ = self.iz("Kaynak: istek.docx · sha256 %s\n\n%s" % (sha[:16], IZ_TABLOSU))
        self.assertEqual(0, rc, out)
        self.assertIn("UYARI tabloda kaynak sha256'sı yok — iz hangi kaynağa ait olduğunu söylemiyor: 0", out)
        rc, out, _ = self.iz("Kaynak: istek.docx · sha256 %s\n\n%s" % ("0" * 16, IZ_TABLOSU))
        self.assertEqual(1, rc, out)
        self.assertIn("BAŞKA KAYNAĞIN TABLOSU — tablodaki sha256 paketin kaynağıyla uyuşmuyor: 1", out)
        rc, out, _ = self.iz(IZ_TABLOSU)
        self.assertEqual(0, rc, out)
        self.assertIn("UYARI tabloda kaynak sha256'sı yok — iz hangi kaynağa ait olduğunu söylemiyor: 1", out)

    def test_bos_paket_uyarisi(self):
        bos = os.path.join(self.d, "bos.docx")
        docx_yaz(bos, "<w:sectPr/>", rels=[])
        self.assertEqual(0, call_main(kp.main, ["cikar", bos, "--hedef-kok", self.kok, "--id", "bos"])[0])
        tablo = os.path.join(self.d, "iz-bos.md")
        with open(tablo, "w", encoding="utf-8") as fh:
            fh.write("| Kaynak | Belge kimliği | Not |\n|---|---|---|\n")
        rc, out, _ = call_main(kp.main, ["iz", os.path.join(self.kok, "bos"), "--tablo", tablo, "--belge", self.belge])
        self.assertEqual(0, rc, out)
        self.assertIn("UYARI boş paket: 1", out)
        self.assertIn("paket 0 kaynak maddesi taşıyor", out)

    def test_tablo_okunamazsa_olculemedi(self):
        rc, _out, err = call_main(kp.main, ["iz", self.paket(), "--tablo", os.path.join(self.d, "yok.md"),
                                            "--belge", self.belge])
        self.assertEqual(2, rc)
        self.assertIn("ÖLÇÜLEMEDİ", err)

    def test_km_semasi_tablo_ile_eslesir(self):
        """F13: tablo başka bir numaralandırma şemasıyla eşlenmişse FAIL; şema yoksa UYARI; aynıysa PASS."""
        meta = json.loads(self.oku("paket.json"))
        self.assertEqual(kp.KM_SEMASI, meta["km_semasi"])
        bas = "Kaynak: istek.docx · sha256 %s · km şeması %%d\n\n" % meta["kaynak"]["sha256"][:16]
        rc, out, _ = self.iz(bas % kp.KM_SEMASI + IZ_TABLOSU)
        self.assertEqual(0, rc, out)
        self.assertIn("UYARI tabloda km şeması yok: 0", out)
        self.assertIn("NUMARALANDIRMA ŞEMASI FARKLI — paketi yeniden çıkar, tabloyu yeniden eşle: 0", out)
        rc, out, _ = self.iz(bas % (kp.KM_SEMASI - 1) + IZ_TABLOSU)
        self.assertEqual(1, rc, out)
        self.assertIn("NUMARALANDIRMA ŞEMASI FARKLI — paketi yeniden çıkar, tabloyu yeniden eşle: 1", out)
        rc, out, _ = self.iz(IZ_TABLOSU)
        self.assertEqual(0, rc, out)
        self.assertIn("UYARI tabloda km şeması yok: 1", out)

    def test_eski_paket_semasiz_sema_1_sayilir(self):
        """F13: km_semasi alanı olmayan (eski betikle çıkarılmış) paket şema 1 sayılır; güncel şemayla eşlenmiş
        tablo onunla FAIL verir."""
        meta = json.loads(self.oku("paket.json"))
        del meta["km_semasi"]
        with open(self.paket("paket.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False)
        rc, out, _ = self.iz("km şeması %d\n\n%s" % (kp.KM_SEMASI, IZ_TABLOSU))
        self.assertEqual(1, rc, out)
        self.assertIn("paket: km şeması 1", out)

# ── BÖLÜM: kural metni testleri ──
def _metin(*yol):
    with open(os.path.join(REPO, *yol), encoding="utf-8") as fh:
        return fh.read()


class KaynakKuraliMetinTest(unittest.TestCase):
    """Akış bağlantıları: kural metni yerinde mi (davranış canlı motorda ayrıca ölçülür; bu test yalnız varlık)."""

    def test_inceleme_brifi_ikili_yol_vermez_paket_verir(self):
        t = _metin("skills-sap", "sap-fs-ts-docs", "references", "doc-checklist.md")
        brif = t[t.index("## §E"):]
        self.assertIn("İkili kaynak brife YOL olarak verilmez", brif)
        self.assertIn("KAYNAK PAKETİ: <proje içi .axet-code/tmp/<id>/INDEX.md", brif)
        self.assertIn("İZ TABLOSU:", brif)
        self.assertIn("İZ TABLOSUNA DAYALI İNCELEME'de belgeyi baştan sona okuma", brif)
        self.assertIn("| AX-DOC-CR-06 |", t)
        self.assertIn("CR `AX-DOC-CR-07`", t)

    def test_yazim_ve_alim_akisi_paketi_kullanir(self):
        for yol in (("skills-sap", "sap-fs-ts-docs", "SKILL.md"),
                    ("skills-sap", "sap-fs-ts-docs", "references", "fs-authoring.md"),
                    ("skills-sap", "sap-fs-ts-docs", "references", "traceability.md"),
                    ("skills-sap", "sap-intake-triage", "SKILL.md")):
            self.assertIn("kaynak_paketi.py", _metin(*yol), "/".join(yol))
        self.assertIn("## 2-B. Kaynak paketi", _metin("skills-sap", "sap-fs-ts-docs", "references", "traceability.md"))
        self.assertIn("kaynak paketinin proje içi yolunu ver",
                      _metin("skills-sap", "sap-code-review", "references", "reviewer-brief.md"))
        self.assertIn("- Kaynak: <istek metni | kaynak paketi",
                      _metin("skills-sap", "sap-intake-triage", "templates", "intake-artifact.md"))

    def test_uzun_icerik_bolum_bolum_kurali(self):
        cekirdek = _metin("core", "00-temel.md")
        self.assertIn("**Uzun içeriği tek araç çağrısında üretme:**", cekirdek)
        self.assertIn("150 eşiği ölçülmüş sınır değil", cekirdek, "ölçülmeyen eşik ölçülmüş gibi yazılmaz")
        self.assertIn("504 Gateway Timeout", cekirdek)
        for ad in ("fs-authoring.md", "ts-authoring.md", "kd-authoring.md", "../SKILL.md"):
            t = " ".join(_metin("skills-sap", "sap-fs-ts-docs", "references", *ad.split("/")).split())
            # Ö3: eşik belgenin değil TEK ÇAĞRININ içeriğidir (çekirdek: "araç çağrısı ... 150 satırı aşacaksa").
            self.assertRegex(t, r"çağrı(sı)?nın içeriği 150 satırı aşacaksa önce iskelet", ad + ": çekirdekteki koşul")
            self.assertIn("150 satırı aşan tek bölüm de bölünür", t, ad)
            self.assertNotRegex(t, r"(belge|Kılavuz|Dosya ya da parça) 150 satırı aşacaksa", ad)
            self.assertRegex(t, r"ayrı (bir )?`edit` çağrısıyla", ad)
            self.assertIn("çekirdek §10", t, ad)

    def test_ikili_okuma_iddiasi_olcumle_sinirli(self):
        """F5: 'alt ajan okuyamaz (ölçüldü)' genellemesi yazılmaz; ölçülen tek oturum ve ölçülmeyenler söylenir."""
        for yol in (("skills-sap", "sap-fs-ts-docs", "SKILL.md"),
                    ("skills-sap", "sap-fs-ts-docs", "references", "doc-checklist.md"),
                    ("skills-sap", "sap-code-review", "references", "reviewer-brief.md")):
            t = " ".join(_metin(*yol).split())
            self.assertNotRegex(t, r"okuyamaz[ ,(]*ölçüldü", "/".join(yol))
            self.assertIn("`view` ikili `.docx`'i açmadı", t, "/".join(yol))
            self.assertIn("tek oturum", t, "/".join(yol))
            self.assertIn("`.xlsx`/`.pdf` denenmedi", t, "/".join(yol))

    def test_iz_tablosu_git_te_izlenen_yerde(self):
        """F6: iz tablosu git dışı .axet-code/tmp'de değil, FS'in SAP paketinde ref_docs/ altında."""
        trace = _metin("skills-sap", "sap-fs-ts-docs", "references", "traceability.md")
        self.assertIn("--tablo <source_root>/<MODÜL>/<PAKET>/ref_docs/iz-<belge no>.md", trace)
        self.assertIn("`Kaynak: <dosya adı> · sha256 <ilk 16 hane> · km şeması <n>`", trace)
        # F13: kimlikler aynı kaynaktan yalnız AYNI BETİK SÜRÜMÜYLE yeniden üretilir; kaynak ikili dosyanın yeri yazılı.
        t = " ".join(trace.split())
        self.assertIn("**aynı betik sürümüyle** (aynı `km şeması`)", t)
        self.assertIn("**kaynak ikili dosya** da saklanır — iz tablosunun yanında, `ref_docs/` altında", t)
        self.assertNotIn("aynı kaynaktan `cikar` aynı kimliklerle", t)
        self.assertNotIn("paket klasöründe `iz-", trace)
        self.assertIn("ref_docs/iz-<belge no>.md", _metin("skills-sap", "sap-fs-ts-docs", "references",
                                                          "doc-checklist.md"))
        self.assertIn("ref_docs/iz-<FS no>.md", _metin("skills-sap", "sap-intake-triage", "templates",
                                                       "intake-artifact.md"))
        self.assertIn("ref_docs/iz-<belge no>.md", kp.SCOPE_CIKAR + _metin(
            "skills-sap", "sap-fs-ts-docs", "scripts", "kaynak_paketi.py"))


if __name__ == "__main__":
    unittest.main()
