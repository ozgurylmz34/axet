#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_pr.py karar mantigi testleri (gh CAGRILMAZ; yalnizca saf fonksiyon).

KAPSAM BEYANI: bu dosya yalnizca statusCheckRollup -> verdict donusumunu olcer.
gh cagrisinin kendisi, agin davranisi ve gercek birlestirme BURADA OLCULMEZ.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from merge_pr import kontrol_ozeti  # noqa: E402


class KontrolOzetiTest(unittest.TestCase):
    def test_checkrun_basarili(self):
        ok, bek, kotu = kontrol_ozeti([{"name": "testler", "status": "COMPLETED", "conclusion": "SUCCESS"}])
        self.assertEqual((ok, bek, kotu), (["testler"], [], []))

    def test_checkrun_basarisiz(self):
        ok, bek, kotu = kontrol_ozeti([{"name": "testler", "status": "COMPLETED", "conclusion": "FAILURE"}])
        self.assertEqual(ok, [])
        self.assertEqual(bek, [])
        self.assertEqual(len(kotu), 1)
        self.assertIn("testler", kotu[0])

    def test_checkrun_kosuyor_bekleyen_sayilir(self):
        ok, bek, kotu = kontrol_ozeti([{"name": "testler", "status": "IN_PROGRESS", "conclusion": None}])
        self.assertEqual((ok, bek, kotu), ([], ["testler"], []))

    def test_statuscontext_bicimi(self):
        ok, bek, kotu = kontrol_ozeti([
            {"context": "eski/ci", "state": "SUCCESS"},
            {"context": "eski/lint", "state": "FAILURE"},
            {"context": "eski/bekle", "state": "PENDING"},
        ])
        self.assertEqual(ok, ["eski/ci"])
        self.assertEqual(bek, ["eski/bekle"])
        self.assertEqual(len(kotu), 1)

    def test_taninmayan_bicim_fail_closed(self):
        """Taninmayan kontrol BASARILI sayilmaz — 'olculemedi' ile 'gecti' ayni sey degildir."""
        ok, bek, kotu = kontrol_ozeti([{"name": "garip", "foo": "bar"}])
        self.assertEqual(ok, [])
        self.assertEqual(len(kotu), 1)
        self.assertIn("taninmayan", kotu[0])

    def test_iptal_edilen_basarisiz_sayilir(self):
        ok, _bek, kotu = kontrol_ozeti([{"name": "testler", "status": "COMPLETED", "conclusion": "CANCELLED"}])
        self.assertEqual(ok, [])
        self.assertEqual(len(kotu), 1)

    def test_skipped_ve_neutral_basarili_sayilir(self):
        ok, bek, kotu = kontrol_ozeti([
            {"name": "a", "status": "COMPLETED", "conclusion": "SKIPPED"},
            {"name": "b", "status": "COMPLETED", "conclusion": "NEUTRAL"},
        ])
        self.assertEqual((sorted(ok), bek, kotu), (["a", "b"], [], []))

    def test_bos_liste_hicbir_sey_uretmez(self):
        """Bos rollup 'yesil' DEGILDIR; cagiran taraf bunu bosluk sayar (merge_pr.main)."""
        self.assertEqual(kontrol_ozeti([]), ([], [], []))
        self.assertEqual(kontrol_ozeti(None), ([], [], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
