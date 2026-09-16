# -*- coding: utf-8 -*-
"""behavior_manifest.py — proje modu (hash manifest) ve template modu (git)."""
from __future__ import annotations

import json

from _helpers import AXET_HOME, GeciciTest  # önce: scripts/ yolunu ekler
import behavior_manifest as bm


class ProjeManifestTest(GeciciTest):
    def setUp(self) -> None:
        super().setUp()
        self.d = self.proje(git_init=False)

    def bm(self, *args: str):
        return self.calistir("behavior_manifest.py", *args, "--project-dir", str(self.d))

    def onayla(self) -> None:
        r = self.bm("generate")
        self.assertEqual(r.returncode, 0, self.cikti(r))

    def test_yok_sonra_onay_sonra_es(self):
        r = self.bm("check")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(bm.proje_denetle(self.d)[0], "yok")
        self.onayla()
        r = self.bm("check")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        kayit = json.loads((self.d / bm.MANIFEST).read_text(encoding="utf-8"))["dosyalar"]
        for rel in ("AGENTS.md", ".axet-code.json", ".axetcode-denylist", ".githooks/pre-commit", "validators-local/README.md"):
            self.assertIn(rel, kayit)

    def test_satir_sonu_farki_sapma_degil(self):
        self.onayla()
        f = self.d / "AGENTS.md"
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertEqual(self.bm("check").returncode, 0)

    def test_hafiza_yuzey_disi(self):
        self.onayla()
        self.yaz(self.d / ".axet-code" / "memory" / "MEMORY.md", "değişti\n")
        self.assertEqual(self.bm("check").returncode, 0)

    # --- negatif ---
    def test_tek_karakter_degisikligi_yakalanir(self):
        self.onayla()
        f = self.d / "AGENTS.md"
        f.write_text(f.read_text(encoding="utf-8") + "x", encoding="utf-8")
        r = self.bm("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DEĞİŞMİŞ (onaysız): AGENTS.md", r.stdout)

    def test_yeni_ve_silinen_dosya(self):
        self.onayla()
        self.yaz(self.d / "validators-local" / "yeni.py", "print(1)\n")
        (self.d / ".axetcode-denylist").unlink()
        r = self.bm("check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("KAYITSIZ yeni davranış dosyası: validators-local/yeni.py", r.stdout)
        self.assertIn("diskte YOK: .axetcode-denylist", r.stdout)

    def test_secici_onay_digerini_beklemede_birakir(self):
        self.onayla()
        f = self.d / "AGENTS.md"
        f.write_text(f.read_text(encoding="utf-8") + "x", encoding="utf-8")
        self.yaz(self.d / ".githooks" / "ek", "x\n")
        r = self.bm("generate", "--only", "AGENTS.md")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("BEKLEMEDE 1", r.stdout)
        r = self.bm("check")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("AGENTS.md", r.stdout.split("KAPSAM")[0])
        self.assertIn(".githooks/ek", r.stdout)

    def test_only_bilinmeyen_yol_reddedilir(self):
        self.onayla()
        once = (self.d / bm.MANIFEST).read_text(encoding="utf-8")
        r = self.bm("generate", "--only", "yok/boyle.md")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual((self.d / bm.MANIFEST).read_text(encoding="utf-8"), once)

    def test_only_manifest_yokken_reddedilir(self):
        r = self.bm("generate", "--only", "AGENTS.md")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.d / bm.MANIFEST).exists())

    def test_bozuk_manifest(self):
        self.yaz(self.d / bm.MANIFEST, "{bozuk")
        r = self.bm("check")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(bm.proje_denetle(self.d)[0], "bozuk")
        self.yaz(self.d / bm.MANIFEST, json.dumps({"dosyalar": ["liste"]}))
        self.assertEqual(bm.proje_denetle(self.d)[0], "bozuk")

    def test_template_modunda_generate_reddedilir(self):
        r = self.calistir("behavior_manifest.py", "generate", "--project-dir", str(AXET_HOME))
        self.assertEqual(r.returncode, 2, self.cikti(r))


class TemplateYuzeyTest(GeciciTest):
    def setUp(self) -> None:
        super().setUp()
        import os
        self._eski_env = dict(os.environ)
        os.environ.update({k: v for k, v in self.env.items() if k.startswith("GIT_")})
        self.k = self.tmp / "klon"
        for rel in ("core/00-temel.md", "skills/a/SKILL.md", "config/permissions.json", "memory/MEMORY.md",
                    "skills-sap/b/tests/test_x.py", "scripts/doctor.py"):
            self.yaz(self.k / rel, "ilk\n")
        self.git(self.k, "init", "-q", "-b", "main")
        self.git(self.k, "add", "-A")
        self.git(self.k, "commit", "-q", "-m", "ilk")

    def tearDown(self) -> None:
        import os
        os.environ.clear()
        os.environ.update(self._eski_env)
        super().tearDown()

    def test_temiz(self):
        durum, satirlar = bm.template_denetle(self.k)
        self.assertEqual(durum, "es", satirlar)
        self.assertTrue(any("upstream tanımlı değil" in s for s in satirlar))

    def test_commitsiz_ve_kayitsiz_degisiklik(self):
        self.yaz(self.k / "core/00-temel.md", "değişti\n")
        self.yaz(self.k / "skills/yeni/SKILL.md", "x\n")
        durum, satirlar = bm.template_denetle(self.k)
        self.assertEqual(durum, "sapma")
        metin = "\n".join(satirlar)
        self.assertIn("commit edilmemiş değişiklik [M]: core/00-temel.md", metin)
        self.assertIn("KAYITSIZ yeni dosya (commit'siz): skills/yeni/SKILL.md", metin)

    def test_yuzey_disi_degisiklik_sayilmaz(self):
        for rel in ("memory/MEMORY.md", "skills-sap/b/tests/test_x.py", "scripts/doctor.py"):
            self.yaz(self.k / rel, "değişti\n")
        self.assertEqual(bm.template_denetle(self.k)[0], "es")

    def test_git_degilse_olculemedi(self):
        d = self.tmp / "gitsiz"
        d.mkdir()
        self.assertEqual(bm.template_denetle(d)[0], "olculemedi")
