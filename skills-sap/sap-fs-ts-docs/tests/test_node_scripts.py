# -*- coding: utf-8 -*-
"""Node script'leri: sözdizimi, yapılandırma doğrulaması (tarayıcısız), kullanım hataları; isteğe bağlı uçtan uca PDF."""
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from _common import BROWSER_TESTS, TEMPLATES, node_path, run_node, run_py, sample


@unittest.skipUnless(node_path(), "node bulunamadı")
class NodeScriptsTest(unittest.TestCase):
    def test_syntax(self):
        for js in ("html_to_pdf.js", "capture_kd_screens.js"):
            r = subprocess.run([node_path(), "--check", os.path.join(os.path.dirname(__file__), "..", "scripts", js)],
                               capture_output=True, text=True)
            self.assertEqual(0, r.returncode, js + r.stderr)

    def test_capture_dry_run_ok(self):
        r = run_node("capture_kd_screens.js", sample("capture", "config_ok.json"), "--dry-run")
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("7 adım, 2 çekim", r.stdout)
        self.assertIn("KAPSAM (SCOPE)", r.stdout)

    def test_capture_bad_config_exit_2(self):
        r = run_node("capture_kd_screens.js", sample("capture", "config_bad.json"), "--dry-run")
        self.assertEqual(2, r.returncode)
        for part in (".png uzantılı", "bilinmeyen do=teleport", "data_file yok", "aynı çekim adı"):
            self.assertIn(part, r.stderr)

    def test_capture_usage_exit_2(self):
        self.assertEqual(2, run_node("capture_kd_screens.js").returncode)

    def test_html_to_pdf_usage_and_missing_input(self):
        self.assertEqual(2, run_node("html_to_pdf.js").returncode)
        r = run_node("html_to_pdf.js", sample("html", "yok.html"), "yok.pdf")
        self.assertEqual(2, r.returncode)
        self.assertIn("girdi yok", r.stderr)

    def test_html_to_pdf_bilinmeyen_bayrak_yol_sanilmaz(self):
        """Z201: bilinmeyen bayrak sessizce yok sayılmaz / dosya yolu sanılmaz — tarayıcı açılmadan çıkış 2."""
        r = run_node("html_to_pdf.js", sample("html", "yok.html"), "yok.pdf", "--sayfano")
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("bilinmeyen bayrak: --sayfano", r.stderr)
        r2 = run_node("html_to_pdf.js", sample("html", "yok.html"), "--sayfa-no")   # bayrak konum sayısına girmez
        self.assertEqual(2, r2.returncode)
        self.assertIn("kullanım:", r2.stderr)

    def test_html_to_pdf_check_reports_state(self):
        r = run_node("html_to_pdf.js", "--check")
        self.assertIn(r.returncode, (0, 2))
        self.assertTrue("playwright-core:" in r.stdout or "npm install playwright-core" in r.stderr)

    def test_playwright_missing_message(self):
        env = dict(os.environ, APPDATA=os.devnull, USERPROFILE=os.devnull, HOME=os.devnull, npm_config_prefix="",
                   NODE_PATH="", PLAYWRIGHT_CORE_PATH="")
        with tempfile.TemporaryDirectory() as tmp:
            html = os.path.join(tmp, "a.html")
            with open(html, "w", encoding="utf-8") as fh:
                fh.write("<html></html>")
            r = subprocess.run([node_path(), os.path.join(os.path.dirname(__file__), "..", "scripts", "html_to_pdf.js"),
                                html, os.path.join(tmp, "a.pdf")], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, cwd=tmp)
        if r.returncode == 0:
            self.skipTest("playwright-core bu ortamda başka yoldan çözüldü; eksik bağımlılık simüle edilemedi")
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("npm install playwright-core", r.stderr)


@unittest.skipUnless(BROWSER_TESTS, "tarayıcı testi kapalı (SAP_FS_TS_DOCS_BROWSER_TESTS=1 ile açılır)")
@unittest.skipUnless(importlib.util.find_spec("markdown"), "python markdown kurulu değil")
class BrowserPdfTest(unittest.TestCase):
    def test_kd_template_pdf_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = os.path.join(tmp, "KD-XX-001_Sablon.html")
            pdf = os.path.join(tmp, "KD-XX-001_Sablon.pdf")
            r = run_py("build_doc_pdf.py", os.path.join(TEMPLATES, "KD-template.md"), html, "--pdf-out", pdf, timeout=300)
            self.assertEqual(0, r.returncode, r.stdout + r.stderr)
            v = run_py("verify_doc_html.py", html, "--pdf", pdf, "--min-pdf-links", "14")
            # Şablon ham derlenir → `[GÖRSEL: …]` yer tutucuları BULGU'dur (Z172, çıkış 1). Bu testin ölçtüğü PDF
            # bağlantılarıdır: yer tutucu dışında bulgu olmamalı.
            self.assertIn(v.returncode, (0, 1), v.stdout + v.stderr)
            bulgular = [ln for ln in v.stdout.splitlines() if ln.startswith("BULGU:")]
            self.assertEqual([], [b for b in bulgular if not b.startswith("BULGU: YER TUTUCU")], v.stdout)
            self.assertIn("bağlantı ek açıklaması 14", v.stdout)


def _pdf_olcer():
    """PDF'i ÜRETEN araçtan bağımsız okuyucu: PyMuPDF (metin + yer imi) ya da pdftotext (yalnız metin)."""
    if importlib.util.find_spec("pymupdf"):
        import pymupdf

        def oku(yol):
            with pymupdf.open(yol) as d:   # açık kalırsa Windows'ta geçici klasör silinemez
                return [p.get_text() for p in d], len(d.get_toc())
        return oku
    if shutil.which("pdftotext"):
        def oku(yol):
            r = subprocess.run(["pdftotext", "-enc", "UTF-8", yol, "-"], capture_output=True)
            return r.stdout.decode("utf-8").split("\f")[:-1], None
        return oku
    return None


@unittest.skipUnless(BROWSER_TESTS, "tarayıcı testi kapalı (SAP_FS_TS_DOCS_BROWSER_TESTS=1 ile açılır)")
@unittest.skipUnless(importlib.util.find_spec("markdown"), "python markdown kurulu değil")
class SayfaNoYerImiTest(unittest.TestCase):
    """Z201 kapanış ölçütü, gerçek giriş noktasından (build_doc_pdf.py --pdf): bayraksız PDF eski yapıda (sayfa sayısı
    + metin bayraklıyla altbilgi dışında aynı) · --sayfa-no ile her sayfada 'Sayfa i / N' · yer imi sayısı = başlık."""

    def setUp(self):
        self.oku = _pdf_olcer()
        if not self.oku:
            self.skipTest("PDF okuyucu yok (python -m pip install pymupdf ya da pdftotext)")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _uret(self, ad, *bayrak):
        html = os.path.join(self.tmp.name, ad + ".html")
        pdf = os.path.join(self.tmp.name, ad + ".pdf")
        r = run_py("build_doc_pdf.py", os.path.join(TEMPLATES, "FS-template.md"), html, "--pdf-out", pdf, *bayrak,
                   timeout=300)
        return r, html, pdf

    def test_sayfa_no_ve_yer_imi_uctan_uca(self):
        r0, _, pdf0 = self._uret("bayraksiz")
        self.assertEqual(0, r0.returncode, r0.stdout + r0.stderr)
        r1, html1, pdf1 = self._uret("bayrakli", "--sayfa-no", "--yer-imi")
        self.assertEqual(0, r1.returncode, r1.stdout + r1.stderr)
        sayfa0, _ = self.oku(pdf0)
        sayfa1, yer_imi = self.oku(pdf1)
        n = len(sayfa0)
        self.assertGreater(n, 1)
        self.assertEqual(n, len(sayfa1), "altbilgi gövdeyi daraltmamalı: sayfa sayısı aynı kalmalı")
        self.assertFalse(any("Sayfa 1 / " in s for s in sayfa0), "bayraksız PDF'te altbilgi olmamalı")
        for i, s in enumerate(sayfa1, 1):
            self.assertIn("Sayfa %d / %d" % (i, n), s)
        norm = lambda s: re.sub(r"\s+", " ", re.sub(r"Sayfa \d+ / \d+", "", s)).strip()
        self.assertEqual([norm(s) for s in sayfa0], [norm(s) for s in sayfa1], "gövde metni altbilgi dışında aynı olmalı")
        with open(html1, encoding="utf-8") as fh:
            baslik = len(re.findall(r"<h[1-6][\s>]", fh.read()))
        self.assertIn("YER-IMI PDF: %d yer imi / %d baslik" % (baslik, baslik), r1.stdout)
        if yer_imi is None:
            self.skipTest("bağımsız yer imi sayımı için PyMuPDF gerekli (araç satırı yukarıda doğrulandı)")
        self.assertEqual(baslik, yer_imi)

    def test_sayfa_no_dar_alt_boslukta_durdu_pdf_yazilmaz(self):
        d = self.tmp.name
        dar = os.path.join(d, "dar.html")
        with open(dar, "w", encoding="utf-8") as fh:
            fh.write("<html><head><style>@page { margin: 10mm 10mm 3mm 10mm; }</style></head><body><h1>X</h1></body></html>")
        r = run_node("html_to_pdf.js", dar, os.path.join(d, "dar.pdf"), "--sayfa-no")
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("[DURDU] --sayfa-no: etkin alt bosluk 3.0mm", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(d, "dar.pdf")))
        # kontrol: aynı belge bayraksız üretilir (DURDU yalnız bayrağın kendi koşulu)
        self.assertEqual(0, run_node("html_to_pdf.js", dar, os.path.join(d, "dar2.pdf")).returncode)

    def test_sayfa_no_okunamayan_stil_sayfasi_durdu(self):
        d = self.tmp.name
        with open(os.path.join(d, "dis.css"), "w", encoding="utf-8") as fh:
            fh.write("@page { margin-bottom: 3mm; }")
        dis = os.path.join(d, "dis.html")
        with open(dis, "w", encoding="utf-8") as fh:
            fh.write('<html><head><link rel="stylesheet" href="dis.css"></head><body><h1>X</h1></body></html>')
        r = run_node("html_to_pdf.js", dis, os.path.join(d, "dis.pdf"), "--sayfa-no")
        self.assertEqual(2, r.returncode, r.stdout + r.stderr)
        self.assertIn("stil sayfasi okunamadi", r.stderr)
        # kontrol: aynı kural <style> içinde → ölçülür (DURDU okunamama yüzünden, margin yüzünden değil sınıfı ayrı)
        ic = os.path.join(d, "ic.html")
        with open(ic, "w", encoding="utf-8") as fh:
            fh.write("<html><head><style>@page { margin-bottom: 20mm; }</style></head><body><h1>X</h1></body></html>")
        r2 = run_node("html_to_pdf.js", ic, os.path.join(d, "ic.pdf"), "--sayfa-no")
        self.assertEqual(0, r2.returncode, r2.stdout + r2.stderr)
        self.assertIn("etkin alt bosluk 20.0mm (css-@page)", r2.stdout)


if __name__ == "__main__":
    unittest.main()
