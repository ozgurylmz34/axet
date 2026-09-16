# -*- coding: utf-8 -*-
"""install.py — sahte (geçici) template klonunda: SAP yazma izni dosyası gerçek klona dokunmaz."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest

from _helpers import AXET_HOME, GeciciTest

# Önceden kurulmuş makinelerin config'indeki template kuralları: 42b37b8'de yayımlanan config/permissions.json
# (bash). Git'ten okunmaz ki test sığ klonda da çalışsın ve RETIRED_RULES'tan türetilmez ki listeden eksik anahtar
# yakalansın. Geçmişle eşliği EmekliKuralTest denetler.
ESKI_BASH_42B37B8 = {
    "git push --force*": "deny", "git push -f*": "deny", "git push *--force*": "deny", "git push * -f*": "deny",
    "git reset --hard*": "deny", "git clean -f*": "deny", "*--no-verify*": "deny", "*install.py*--sap-write*": "deny",
    "*sap-write.local*": "deny", "*behavior_manifest.py*generate*": "deny", "*core.hooksPath*": "deny",
    "*fiori deploy*": "deny", "*fiori undeploy*": "deny", "*npm run deploy*": "deny",
    "*npm --prefix * run deploy*": "deny", "*deploy_ui.py*deploy *": "ask", "rm -rf *": "ask", "rm -r *": "ask",
    "Remove-Item *-Recurse*": "ask", "rd /s *": "ask", "del /s *": "ask",
}


def guncel_kurallar() -> dict:
    return json.loads((AXET_HOME / "config" / "permissions.json").read_text(encoding="utf-8"))["rules"]


def ask_deny_uzunluk_ihlalleri(kurallar: dict) -> list[str]:
    """Her araç için her ask deseni her deny deseninden hem sabit karakterde hem toplam uzunlukta KESİN kısa olmalı.

    Gerekçe (ölçüldü 2026-09-14, aXet.code 1.3.0, tek ölçüm serisi): aynı komuta bir ask ve bir deny deseni uyunca
    uzun desen kazanır, eşitlikte ask kazanır; run modunda ask sormadan onaylar. Ask deny'dan kısa değilse zincirli
    komutta ('echo x; git reset --hard; ... Remove-Item ...') deny'ı ezer ve komut sorulmadan çalışır. Uzunluğun
    sabit karakterle mi ('*' hariç) toplam uzunlukla mı ölçüldüğü DOĞRULANMADI → ikisi birden denetlenir.
    """
    ihlal = []
    for arac, desenler in kurallar.items():
        if not isinstance(desenler, dict):
            continue
        asklar = [p for p, v in desenler.items() if v == "ask"]
        denyler = [p for p, v in desenler.items() if v == "deny"]
        for a in asklar:
            for d in denyler:
                sa, sd = len(a.replace("*", "")), len(d.replace("*", ""))
                if not (sa < sd and len(a) < len(d)):
                    ihlal.append(f"{arac}: ask {a!r} (sabit {sa}, toplam {len(a)}) deny {d!r} (sabit {sd}, toplam "
                                 f"{len(d)}) desenden kısa değil → ikisi aynı zincirli komuta uyarsa ask kazanır ve "
                                 f"komut run modunda sorulmadan çalışır")
    return ihlal


class IzinDesenUzunlukTest(unittest.TestCase):
    def test_ask_desenleri_tum_denylardan_kisa(self):
        kurallar = guncel_kurallar()
        self.assertTrue(any(v == "ask" for d in kurallar.values() for v in d.values()), "ask kuralı yok; test boş geçer")
        self.assertTrue(any(v == "deny" for d in kurallar.values() for v in d.values()), "deny kuralı yok; test boş geçer")
        ihlal = ask_deny_uzunluk_ihlalleri(kurallar)
        self.assertEqual(ihlal, [], "\n".join(ihlal))

    # --- negatif ---
    def test_uzun_ask_yakalanir(self):
        kurallar = {"bash": {"*git push -f*": "deny", "*Remove-Item*-Recurse*": "ask", "*rm -rf *": "ask"}}
        ihlal = ask_deny_uzunluk_ihlalleri(kurallar)
        self.assertEqual(len(ihlal), 1, ihlal)
        self.assertIn("'*Remove-Item*-Recurse*'", ihlal[0])
        self.assertIn("'*git push -f*'", ihlal[0])
        # eşitlik de ihlaldir (eşitlikte ask kazanır): sabit 11=11, toplam 13=13
        self.assertEqual(len(ask_deny_uzunluk_ihlalleri({"bash": {"*git push -f*": "deny", "*Remove-Item*": "ask"}})), 1)
        # yalnız bir ölçüt eşit/uzunsa da ihlal: sabit 6<11 ama toplam 13=13 · toplam 12<13 ama sabit 11=11
        self.assertEqual(len(ask_deny_uzunluk_ihlalleri({"bash": {"*git push -f*": "deny", "*R*e*m*o*v*e*": "ask"}})), 1)
        self.assertEqual(len(ask_deny_uzunluk_ihlalleri({"bash": {"*git push -f*": "deny", "Remove-Item*": "ask"}})), 1)
        # kısa ask ihlal değildir
        self.assertEqual(ask_deny_uzunluk_ihlalleri({"bash": {"*git push -f*": "deny", "*Remove-It*": "ask"}}), [])


class EmekliKuralTest(unittest.TestCase):
    """install.RETIRED_RULES ↔ güncel permissions.json ↔ git geçmişi."""

    def test_emekli_desen_guncel_dosyada_yok(self):
        import install
        guncel = guncel_kurallar()
        cakisan = [f"{d}:{p}" for d, ps in install.RETIRED_RULES.items() for p in ps if p in guncel.get(d, {})]
        self.assertEqual(cakisan, [], "RETIRED_RULES'taki desen güncel config/permissions.json'da da var → kurulum onu "
                                      "hem yazar hem emekli sayar; birinden çıkar")

    def _gecmis(self, *args: str) -> str:
        r = subprocess.run(["git", "-C", str(AXET_HOME), *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, timeout=60)
        if r.returncode != 0:
            self.skipTest(f"git geçmişi okunamadı (sığ klon ya da git yok): git {' '.join(args)} → {r.stderr.strip()}")
        return r.stdout

    def test_gecmiste_yayimlanip_cikan_her_desen_emekli_listesinde(self):
        import install
        guncel = guncel_kurallar()
        commitler = self._gecmis("log", "--format=%h", "--", "config/permissions.json").split()
        self.assertTrue(commitler, "permissions.json için commit bulunamadı")
        # Yayımlanan tek commit'lik kopyada (yayin_hazirla.py) ve sığ klonda eski sürümler yoktur: tek commit güncel
        # dosyaya eşittir ve karşılaştırma boş geçerdi. Sessiz "ok" yerine atla; eski sürüm kapsamı orada
        # git'siz InstallTest (ESKI_BASH_42B37B8 fixture'ı) ile korunur.
        if len(commitler) < 2:
            self.skipTest(f"permissions.json geçmişinde {len(commitler)} commit var (yayın kopyası ya da sığ klon); "
                          "eski sürümlerle karşılaştırma yapılamadı")
        eksik = set()
        for h in commitler:
            eski = json.loads(self._gecmis("show", f"{h}:config/permissions.json"))["rules"]
            for d, ps in eski.items():
                for p, karar in ps.items():
                    if p not in guncel.get(d, {}) and install.RETIRED_RULES.get(d, {}).get(p) != karar:
                        eksik.add(f"{d}:{p}={karar} ({h})")
        self.assertEqual(sorted(eksik), [], "geçmişte yayımlanıp dosyadan çıkan desen RETIRED_RULES'ta yok (ya da karar "
                                            "farklı) → önceden kurulmuş makinelerde yetim kalır")

    def test_eski_fixture_gecmisle_ayni(self):
        eski = json.loads(self._gecmis("show", "42b37b8:config/permissions.json"))["rules"]["bash"]
        self.assertEqual(eski, ESKI_BASH_42B37B8)


class InstallTest(GeciciTest):
    def setUp(self) -> None:
        super().setUp()
        self.klon = self.tmp / "klon"
        for rel in ("scripts/install.py", "config/permissions.json", "core/00-temel.md", "core/sap/00-sap.md",
                    "memory/MEMORY.md"):
            hedef = self.klon / rel
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(AXET_HOME / rel, hedef)
        (self.klon / "skills").mkdir()
        (self.klon / "skills-sap").mkdir()
        self.cfg = self.xdg / "axet-code" / "axet-code.json"

    def install(self, *args: str):
        return self.calistir(self.klon / "scripts" / "install.py", *args)

    def oku(self) -> dict:
        return json.loads(self.cfg.read_text(encoding="utf-8"))

    def eski_kurulum(self, kullanici: dict | None = None) -> None:
        """42b37b8 permissions.json'la kurulmuş makineyi taklit eder: klon kopyasına eski dosya konur, install koşulur,
        sonra güncel dosya geri konur. Gerçek global config'e dokunulmaz (XDG geçici)."""
        dosya = self.klon / "config" / "permissions.json"
        yeni = dosya.read_text(encoding="utf-8")
        dosya.write_text(json.dumps({"rules": {"bash": ESKI_BASH_42B37B8}}), encoding="utf-8")
        if kullanici is not None:
            self.cfg.parent.mkdir(parents=True, exist_ok=True)
            self.cfg.write_text(json.dumps(kullanici), encoding="utf-8")
        r = self.install()
        self.assertEqual(r.returncode, 0, self.cikti(r))
        dosya.write_text(yeni, encoding="utf-8")
        bash = self.oku()["permissions"]["rules"]["bash"]
        self.assertTrue(all(bash.get(k) == v for k, v in ESKI_BASH_42B37B8.items()), "eski kurulum taklidi kurulmadı")

    @staticmethod
    def emekli_beklenen() -> set:
        """Eski kurulumda olup güncel dosyada olmayan desenler (RETIRED_RULES'tan bağımsız hesap)."""
        return set(ESKI_BASH_42B37B8) - set(guncel_kurallar()["bash"])

    def test_eski_kurulumdan_guncelleme_emekli_desenleri_siler(self):
        self.eski_kurulum({"permissions": {"rules": {"bash": {"*benim-aracim*": "allow"}}}})
        r = self.install()
        self.assertEqual(r.returncode, 0, self.cikti(r))
        emekli = self.emekli_beklenen()
        self.assertTrue(emekli, "eski ve güncel dosya aynı; test bir şey ölçmez")
        kurallar = self.oku()["permissions"]["rules"]
        self.assertEqual(sorted(emekli & set(kurallar["bash"])), [], "emekli desen config'te kaldı")
        self.assertEqual(kurallar["bash"], {**guncel_kurallar()["bash"], "*benim-aracim*": "allow"})
        ihlal = ask_deny_uzunluk_ihlalleri(kurallar)
        self.assertEqual(ihlal, [], "\n".join(ihlal))
        self.assertIn(f"Eski template kuralları kaldırıldı ({len(emekli)})", r.stdout)

    def test_eski_kurulumdan_kaldirma_emekli_desen_birakmaz(self):
        self.eski_kurulum({"model": "m1", "permissions": {"rules": {"bash": {"*benim-aracim*": "allow"}}}})
        r = self.install("--uninstall")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        cfg = self.oku()
        self.assertEqual(cfg["model"], "m1")
        self.assertEqual(cfg["permissions"], {"rules": {"bash": {"*benim-aracim*": "allow"}}})

    def test_kullanicinin_degistirdigi_emekli_desen_korunur(self):
        self.eski_kurulum()
        cfg = self.oku()
        cfg["permissions"]["rules"]["bash"]["rm -rf *"] = "deny"
        self.cfg.write_text(json.dumps(cfg), encoding="utf-8")
        r = self.install()
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.oku()["permissions"]["rules"]["bash"].get("rm -rf *"), "deny")
        self.assertIn("UYARI", r.stdout)
        self.assertIn("bash:rm -rf *", r.stdout)
        r = self.install("--uninstall")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.oku()["permissions"], {"rules": {"bash": {"rm -rf *": "deny"}}})

    # --- negatif ---
    def test_emekli_listeden_eksik_desen_yakalanir(self):
        yol = self.klon / "scripts" / "install.py"
        metin = yol.read_text(encoding="utf-8")
        satir = '        "*deploy_ui.py*deploy *": "ask",\n'
        self.assertEqual(metin.count(satir), 1, "negatif test hedef satırı bulamadı")
        yol.write_text(metin.replace(satir, ""), encoding="utf-8")
        self.eski_kurulum()
        self.assertEqual(self.install().returncode, 0)
        kurallar = self.oku()["permissions"]["rules"]
        self.assertEqual(kurallar["bash"].get("*deploy_ui.py*deploy *"), "ask", "eksik liste emekli deseni yine sildi")
        self.assertTrue(any("'*deploy_ui.py*deploy *'" in i for i in ask_deny_uzunluk_ihlalleri(kurallar)))

    def test_bos_configde_kurulum(self):
        r = self.install()
        self.assertEqual(r.returncode, 0, self.cikti(r))
        cfg = self.oku()
        self.assertIn((self.klon / "core" / "00-temel.md").as_posix(), cfg["options"]["context_paths"])
        self.assertIn((self.klon / "skills").as_posix(), cfg["options"]["skills_paths"])
        self.assertEqual(cfg["permissions"]["rules"]["bash"]["*--no-verify*"], "deny")
        self.assertTrue(any(p.endswith("/core/*") for p in cfg["permissions"]["rules"]["edit"]))
        self.assertNotIn((self.klon / "core" / "sap").as_posix(), cfg["options"]["context_paths"])

    def test_kullanici_ayari_korunur_ve_kaldirma(self):
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text(json.dumps({"model": "m1", "options": {"context_paths": ["D:/benim.md"]}}), encoding="utf-8")
        self.assertEqual(self.install().returncode, 0)
        cfg = self.oku()
        self.assertEqual(cfg["model"], "m1")
        self.assertIn("D:/benim.md", cfg["options"]["context_paths"])
        self.assertTrue(list(self.cfg.parent.glob("axet-code.json.bak-*")), "yedek alınmadı")
        self.assertEqual(self.install("--uninstall").returncode, 0)
        cfg = self.oku()
        self.assertEqual(cfg["options"]["context_paths"], ["D:/benim.md"])
        self.assertNotIn("permissions", cfg)

    def test_sap_ac_kapa(self):
        self.assertEqual(self.install("--sap").returncode, 0)
        self.assertIn((self.klon / "core" / "sap").as_posix(), self.oku()["options"]["context_paths"])
        self.assertEqual(self.install().returncode, 0)  # durum korunur
        self.assertIn((self.klon / "core" / "sap").as_posix(), self.oku()["options"]["context_paths"])
        self.assertEqual(self.install("--no-sap").returncode, 0)
        self.assertNotIn((self.klon / "core" / "sap").as_posix(), self.oku()["options"]["context_paths"])

    # --- negatif ---
    def test_bozuk_json_dokunulmaz(self):
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text("{bozuk", encoding="utf-8")
        r = self.install()
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{bozuk")

    def test_sap_write_sap_kapaliyken_reddedilir(self):
        r = self.install("--sap-write")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertFalse((self.klon / "config" / "sap-write.local").exists())
        self.assertFalse(self.cfg.exists())

    def test_dry_run_yazmaz(self):
        r = self.install("--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("dry-run", r.stdout)
        self.assertFalse(self.cfg.exists())

    def test_eksik_template_dosyasi(self):
        (self.klon / "core" / "00-temel.md").unlink()
        r = self.install()
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.cfg.exists())
