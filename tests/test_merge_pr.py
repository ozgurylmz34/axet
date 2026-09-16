#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge_pr.py karar mantigi testleri (gh CAGRILMAZ; yalnizca saf fonksiyon).

KAPSAM BEYANI: bu dosya yalnizca SAF donusumleri olcer —
  * statusCheckRollup -> verdict (kontrol_ozeti)
  * REST iki ucu     -> statusCheckRollup (rest_rollup)
  * REST mergeable   -> gh sozlugu (rest_mergeable)
BURADA OLCULMEYEN: gh cagrisinin kendisi · agin davranisi · token alinmasi ·
gercek birlestirme (PUT .../merge) · 409/405 dallari · backend secimi (main).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from merge_pr import kontrol_ozeti, rest_mergeable, rest_rollup  # noqa: E402


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


class RestRollupTest(unittest.TestCase):
    """REST ucu -> statusCheckRollup donusumu (ag CAGRILMAZ; saf fonksiyon)."""

    def test_check_run_alanlari_tasinir_ve_kontrol_ozeti_okur(self):
        r = rest_rollup([{"name": "Testler", "status": "completed", "conclusion": "success"}], [])
        self.assertEqual(r, [{"name": "Testler", "status": "completed", "conclusion": "success"}])
        self.assertEqual(kontrol_ozeti(r), (["Testler"], [], []))

    def test_kosan_check_run_bekleyen_sayilir(self):
        r = rest_rollup([{"name": "Testler", "status": "in_progress", "conclusion": None}], [])
        self.assertEqual(kontrol_ozeti(r), ([], ["Testler"], []))

    def test_legacy_status_context_bicimine_cevrilir(self):
        r = rest_rollup([], [{"context": "ci/eski", "state": "success"}])
        self.assertEqual(kontrol_ozeti(r), (["ci/eski"], [], []))

    def test_bos_legacy_statuses_HICBIR_SEY_uretmez(self):
        """OLCULMUS TUZAK (2026-09-16): legacy /commits/<sha>/status ucu, repoda hic
        legacy status yokken TOPLU alanda "pending" doner. rest_rollup o toplu alani
        OKUMAZ; yalnizca `statuses` dizisini cevirir. Bu test o ayrimi civiler:
        toplu alan sizsaydi asagidaki rollup'ta bir "bekleyen" belirir ve yalniz
        check-run kullanan repo HICBIR ZAMAN birlestirilemezdi."""
        r = rest_rollup([{"name": "Testler", "status": "completed", "conclusion": "success"}], [])
        self.assertEqual(len(r), 1, "toplu legacy 'state' rollup'a sizdi")
        self.assertEqual(kontrol_ozeti(r), (["Testler"], [], []))

    def test_none_girdiler_bos_rollup(self):
        self.assertEqual(rest_rollup(None, None), [])


class RestMergeableTest(unittest.TestCase):
    def test_true_mergeable(self):
        self.assertEqual(rest_mergeable({"mergeable": True, "mergeable_state": "clean"}), "MERGEABLE")

    def test_false_conflicting(self):
        self.assertEqual(rest_mergeable({"mergeable": False, "mergeable_state": "dirty"}), "CONFLICTING")

    def test_dirty_state_tek_basina_conflicting(self):
        self.assertEqual(rest_mergeable({"mergeable": None, "mergeable_state": "dirty"}), "CONFLICTING")

    def test_none_UNKNOWN_dir_mergeable_degil(self):
        """None 'birlestirilebilir' DEGIL, 'henuz olculmedi' demektir (asenkron hesap)."""
        self.assertEqual(rest_mergeable({"mergeable": None, "mergeable_state": "unknown"}), "UNKNOWN")
        self.assertEqual(rest_mergeable({}), "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
