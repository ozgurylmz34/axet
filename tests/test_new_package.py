# -*- coding: utf-8 -*-
"""new_package.py — paket klasörü, .rules.md regex doldurma, PAKETLER.md listesi."""
from __future__ import annotations

from _helpers import GeciciTest


class NewPackageTest(GeciciTest):
    def test_paket_kurulur(self):
        d = self.proje(sap=True, git_init=False)
        pkg = self.paket(d, "ZSD001_CLC")
        kural = (pkg / ".rules.md").read_text(encoding="utf-8")
        self.assertIn("`^ZSD001_[PR]_[A-Z0-9_]+$`", kural)
        self.assertIn("`^ZCL_SD001_[A-Z0-9_]+$`", kural)
        self.assertNotRegex(kural, r"\{[A-Z_]+\}")
        for k in ("cds", "classes", "programs", "ref_docs"):
            self.assertTrue((pkg / k).is_dir(), k)
        self.assertIn("ZSD001_CLC", (d / "SOURCE_CODES" / "PAKETLER.md").read_text(encoding="utf-8"))
        r = self.calistir("new_package.py", "--index", "--check", "--project-dir", str(d))
        self.assertEqual(r.returncode, 0, self.cikti(r))

    # --- negatif ---
    def test_sap_projesi_degilse_red(self):
        d = self.proje(git_init=False)
        r = self.calistir("new_package.py", "ZSD001", "--title", "x", "--project-dir", str(d))
        self.assertEqual(r.returncode, 2)
        self.assertFalse((d / "SOURCE_CODES").exists())

    def test_gecersiz_adlar_red(self):
        d = self.proje(sap=True, git_init=False)
        for ad in ("zsd001", "MM001", "ZSD-001"):
            r = self.calistir("new_package.py", ad, "--title", "x", "--project-dir", str(d))
            self.assertEqual(r.returncode, 2, f"{ad}: {self.cikti(r)}")
        self.assertFalse((d / "SOURCE_CODES" / "SD").exists())

    def test_ayni_paket_ikinci_kez_red(self):
        d = self.proje(sap=True, git_init=False)
        self.paket(d, "ZSD001")
        r = self.calistir("new_package.py", "ZSD001", "--title", "x", "--project-dir", str(d))
        self.assertEqual(r.returncode, 1)

    def test_bayat_liste_yakalanir(self):
        d = self.proje(sap=True, git_init=False)
        self.paket(d, "ZSD001")
        (d / "SOURCE_CODES" / "PAKETLER.md").write_text("# eski\n", encoding="utf-8")
        r = self.calistir("new_package.py", "--index", "--check", "--project-dir", str(d))
        self.assertEqual(r.returncode, 1, self.cikti(r))
