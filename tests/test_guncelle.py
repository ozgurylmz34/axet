# -*- coding: utf-8 -*-
"""`scripts/guncelle.py` — tüketici güncelleme motoru (TASARIM §4/§6/§7/§8/§12a).

İÇERİK: (a) FIXTURE ÜRETECİ — geçici dizinde sahte "public" template deposu (etiket v1/v2/v3)
+ senaryo başına tüketici klonu; (b) §12a'nın istediği senaryo/altın-çıktı/mutasyon testleri.

Fixture üreteci `SahteYayin` sınıfıdır ve elle de çalıştırılabilir (incelemek için):
    python tests/test_guncelle.py --uret <bos-dizin>

Repo DIŞI TMP zorunlu (ölçülmüş tuzak: repo içi TMP'de git testleri yanlış FAIL) — `GeciciTest`
`tempfile.mkdtemp()` kullanır, o da sistem TMP'sindedir.

KAPSAM — bakılmayanlar: gerçek bir tüketici klonunda uçtan uca koşum (`_lab`, P9) · aXet'in
modeli talimatı gerçekten izlemesi · Linux/macOS (Windows'ta ölçüldü) · `butunluk` turundaki
gerçek `doctor.py`/`install.py` davranışı (fixture'da sahte betikler koşar; gerçekleri yalnız
"komut koştu ve çıkışı kaydedildi" düzeyinde ölçülür) · uzun test takımlarının zaman aşımı.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

BURASI = Path(__file__).resolve().parent
if str(BURASI) not in sys.path:
    sys.path.insert(0, str(BURASI))

from _helpers import GeciciTest  # noqa: E402

AXET_HOME = BURASI.parent
GUNCELLE_PY = AXET_HOME / "scripts" / "guncelle.py"
HARITA = AXET_HOME / "guncelle" / "harita.json"


# =====================================================================================================
# FIXTURE ÜRETECİ
# =====================================================================================================
# v1 ağacı: gerçek harita.json'un sınıflandırabildiği yollardan seçildi (sınıfsız dosya motoru
# `sinif: null` koluna düşürür; burada kablolamayı ölçmek istiyoruz, o kolu değil).
V1_AGAC: dict[str, str] = {
    "core/00-temel.md": "CORE-ID: AXET-CORE-TEST\n# Çekirdek\nsatir1\nsatir2\nsatir3\n"
                        "satir4\nsatir5\nsatir6\nson\n",
    "scripts/install.py": "#!/usr/bin/env python3\nimport sys\nprint('install v1')\nsys.exit(0)\n",
    "scripts/doctor.py": "#!/usr/bin/env python3\nimport sys\nprint('doctor v1')\nsys.exit(0)\n",
    "config/permissions.json": '{"deny": ["a"]}\n',
    "LICENSE": "MIT v1\n",
    "skills/ornek-skill/SKILL.md": "---\nname: ornek-skill\n---\n# Örnek\ngovde v1\n",
    # klon kimliği (`kur.ps1` Template-Eksikleri: core/00-temel.md + scripts/install.py + skills-sap/)
    "skills-sap/sap-ornek/SKILL.md": "---\nname: sap-ornek\n---\nsap govde v1\n",
    "tests/test_ornek.py": "# test v1\n",
    "kur.cmd": "@echo off\r\nrem A\r\nrem B\r\nrem C\r\necho v1\r\nrem D\r\nrem E\r\nrem son\r\n",
    "docs/tasinacak.md": "tasinan icerik\nA\nB\n",
    "docs/tasinan2.md": "ikinci tasinan\nX\nY\nZ\n",
    "docs/silinecek.md": "silinecek v1\n",
    # V4B için tabanda VAR olmalı: tabansız bir ikili dosya V7'dir (ad çakışması), V4B değil
    "docs/logo.png": "\x00\x01PNG-v1\x00",
    "skills/silinen-skill/SKILL.md": "---\nname: silinen-skill\n---\nsilinen v1\n",
    # ölçüm komutlarının gerçekten koşabilmesi için (harita: `python tests/run_tests.py …`)
    "tests/run_tests.py": "import sys\nprint('SONUÇ: 3 test · 0 failure')\nsys.exit(0)\n",
}

# v2'de değişenler (yayın kalemi 2-01/2-02)
V2_DEGISIM: dict[str, str | None] = {
    "scripts/doctor.py": "#!/usr/bin/env python3\nimport sys\nprint('doctor v2')\nsys.exit(0)\n",
    "core/00-temel.md": "CORE-ID: AXET-CORE-TEST\n# Çekirdek v2\nsatir1\nsatir2\nsatir3\n"
                        "satir4\nsatir5\nsatir6\nson\n",
}

# v3'te değişenler/eklenenler/silinenler — §4'ün tüm vaka kodlarını tetikleyebilmek için
V3_DEGISIM: dict[str, str | None] = {
    # V1/V4 adayı: taban v1'den beri iki kez değişen dosya (dosya-başı taban senaryosu)
    "scripts/doctor.py": "#!/usr/bin/env python3\nimport sys\nprint('doctor v3')\nsys.exit(0)\n",
    # V4 adayı: üst satır bizden, alt satır kullanıcıdan → temiz birleşme (V4t)
    "core/00-temel.md": "CORE-ID: AXET-CORE-TEST\n# Çekirdek v3\nsatir1\nsatir2\nsatir3\n"
                        "satir4\nsatir5\nsatir6\nson\n",
    # V1 adayı (kullanıcı dokunmaz)
    "config/permissions.json": '{"deny": ["a", "b"]}\n',
    # V2 adayı: yepyeni dosya
    "scripts/sap_stamp.py": "print('yeni')\n",
    # V5 adayı: kullanıcının sildiği skill bu yayında güncellendi
    "skills/silinen-skill/SKILL.md": "---\nname: silinen-skill\n---\nsilinen v3\n",
    # V6 adayı: template sildi
    "docs/silinecek.md": None,
    # V1R adayı: yeniden adlandırma, kullanıcı dokunmamış (içerik aynı → git -M yakalar)
    "docs/tasinacak.md": None,
    "docs/tasindi.md": "tasinan icerik\nA\nB\n",
    # V4R adayı: yeniden adlandırma + iki taraf da değişmiş
    "docs/tasinan2.md": None,
    "docs/tasindi2.md": "ikinci tasinan\nX bizden\nY\nZ\n",
    # V4B adayı: ikili dosya (binary attribute .png)
    "docs/logo.png": "\x00\x01PNG-v3\x00",
    # CRLF ölçümü: .cmd dosyası (eol=crlf) hem bizde hem kullanıcıda değişir
    "kur.cmd": "@echo off\r\nrem bizden\r\nrem A\r\nrem B\r\nrem C\r\necho v3\r\n"
               "rem D\r\nrem E\r\nrem son\r\n",
    # V7 adayı: kullanıcı aynı yola kendi dosyasını koymuş olacak
    "skills/cakisan/SKILL.md": "---\nname: cakisan\n---\ntemplate surumu\n",
}

YAYINLAR = {
    "yayinlar": [
        {
            "etiket": "v2", "tarih": "2026-01-01", "min_axet": "1.0.0",
            "kalemler": [
                {"id": "2-01", "baslik": "doctor: v2 düzeltmesi", "tur": "duzeltme", "kritik": False,
                 "neden": "hata", "dosyalar": ["scripts/doctor.py"], "gerektirir": [],
                 "test": ["kok:test_ornek"]},
                {"id": "2-02", "baslik": "çekirdek: satır2 netleşti", "tur": "kural", "kritik": False,
                 "neden": "belirsizdi", "dosyalar": ["core/00-temel.md"], "gerektirir": [],
                 "test": []},
            ],
        },
        {
            "etiket": "v3", "tarih": "2026-02-01", "min_axet": "1.0.0",
            "kalemler": [
                {"id": "3-01", "baslik": "doctor + yeni araç", "tur": "yetenek", "kritik": False,
                 "neden": "eksikti", "dosyalar": ["scripts/doctor.py", "scripts/sap_stamp.py"],
                 "gerektirir": [], "test": ["kok:test_ornek"]},
                {"id": "3-02", "baslik": "çekirdek başlığı", "tur": "kural", "kritik": False,
                 "neden": "—", "dosyalar": ["core/00-temel.md"], "gerektirir": [], "test": []},
                {"id": "3-03", "baslik": "izin listesi genişledi", "tur": "guvenlik", "kritik": True,
                 "neden": "açık", "dosyalar": ["config/permissions.json"], "gerektirir": [], "test": []},
                {"id": "3-04", "baslik": "skill onarımı + emeklilik + taşıma", "tur": "duzeltme",
                 "kritik": False, "neden": "—",
                 "dosyalar": ["skills/silinen-skill/SKILL.md", "docs/silinecek.md",
                              "docs/tasinacak.md", "docs/tasindi.md",
                              "docs/tasinan2.md", "docs/tasindi2.md"],
                 "gerektirir": [], "test": []},
                {"id": "3-05", "baslik": "logo + kur.cmd + çakışan skill", "tur": "yetenek",
                 "kritik": False, "neden": "—",
                 "dosyalar": ["docs/logo.png", "kur.cmd", "skills/cakisan/SKILL.md"],
                 "gerektirir": ["3-01"], "test": []},
            ],
        },
    ]
}


class SahteYayin:
    """Sahte public template deposu + ondan türemiş tüketici klonu.

    public: c1(v1) → c2(v2) → c3(v3).  tüketici: v1'de klonlanmış, sonra `fetch --tags` yapmış
    ⇒ HEAD = c1, origin/main = c3, merge-base = c1 (gerçek tüketici deseninin aynısı).
    """

    def __init__(self, test: GeciciTest, kok: Path) -> None:
        self.t = test
        self.kok = kok
        self.public = kok / "public"
        self.tuketici = kok / "tuketici"

    # --- kurulum -------------------------------------------------------------------------------
    def _yaz(self, dizin: Path, agac: dict) -> None:
        for yol, icerik in agac.items():
            h = dizin / yol
            if icerik is None:
                if h.exists():
                    h.unlink()
                continue
            h.parent.mkdir(parents=True, exist_ok=True)
            ikili = h.suffix.lower() in (".png", ".jpg", ".zip", ".pdf", ".exe")
            if ikili:
                h.write_bytes(icerik.encode("latin-1"))
            else:
                with open(h, "w", encoding="utf-8", newline="") as fh:
                    fh.write(icerik)

    def uret(self) -> "SahteYayin":
        self.public.mkdir(parents=True)
        g = self.t.git
        g(self.public, "init", "-q", "-b", "main")
        # .gitattributes: gerçek template'in ilgili satırları (CRLF/binary davranışı ölçülecek)
        self._yaz(self.public, {
            ".gitattributes": "* text=auto\n*.py text eol=lf\n*.md text eol=lf\n*.json text eol=lf\n"
                              "*.cmd text eol=crlf\n*.png binary\n",
            ".gitignore": "/.axet-guncelleme/\n",
        })
        self._yaz(self.public, V1_AGAC)
        g(self.public, "add", "-A")
        g(self.public, "commit", "-q", "-m", "v1")
        g(self.public, "tag", "v1")
        # tüketici klonu: v1 hâli
        g(self.kok, "clone", "-q", str(self.public), str(self.tuketici))
        # public ilerler
        self._yaz(self.public, V2_DEGISIM)
        g(self.public, "add", "-A")
        g(self.public, "commit", "-q", "-m", "v2")
        g(self.public, "tag", "v2")
        self._yaz(self.public, V3_DEGISIM)
        self._yaz(self.public, {"guncelle/yayinlar.json":
                                json.dumps(YAYINLAR, ensure_ascii=False, indent=1) + "\n"})
        g(self.public, "add", "-A")
        g(self.public, "commit", "-q", "-m", "v3")
        g(self.public, "tag", "v3")
        # tüketici uzağı görsün
        g(self.tuketici, "fetch", "-q", "--tags", "origin")
        # `onkontrol` origin'in RESMÎ template adresi olmasını ister (K4). Testte resmî adres
        # sahte public deponun kendisidir; üretim varsayılanı (RESMI_ORIGIN) dokunulmadan kalır.
        self.t.env["AXET_GUNCELLE_BEKLENEN_ORIGIN"] = str(self.public)
        return self

    # --- senaryo mutasyonları ------------------------------------------------------------------
    def yerel_degistir(self, yol: str, icerik: str) -> None:
        h = self.tuketici / yol
        h.parent.mkdir(parents=True, exist_ok=True)
        with open(h, "w", encoding="utf-8", newline="") as fh:
            fh.write(icerik)

    def yerel_sil(self, yol: str) -> None:
        (self.tuketici / yol).unlink()

    def yerel_ikili(self, yol: str, veri: bytes) -> None:
        h = self.tuketici / yol
        h.parent.mkdir(parents=True, exist_ok=True)
        h.write_bytes(veri)

    # --- motoru çağır --------------------------------------------------------------------------
    def calistir(self, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(GUNCELLE_PY), "--klon", str(self.tuketici), *args],
            cwd=str(self.kok), env=self.t.env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=timeout)

    def durum_dizini(self) -> Path:
        return self.tuketici / ".axet-guncelleme"

    def plan(self) -> dict:
        return json.loads((self.durum_dizini() / "plan.json").read_text(encoding="utf-8"))

    def durum(self) -> dict:
        return json.loads((self.durum_dizini() / "durum.json").read_text(encoding="utf-8"))

    def vakalar(self) -> dict[str, str]:
        """yol → vaka kodu (altın çıktı karşılaştırması için düzleştirilmiş plan)."""
        out: dict[str, str] = {}
        for k in self.plan()["kalemler"]:
            for d in k["dosyalar"]:
                out[d["yol"]] = d["vaka"]
        return out


class GuncelleTemel(GeciciTest):
    """Ortak kurulum: sahte yayın + tüketici klonu, senaryo mutasyonları uygulanmış."""

    def setUp(self) -> None:
        super().setUp()
        self.f = SahteYayin(self, self.tmp).uret()

    def senaryolari_uygula(self) -> None:
        """§12a'nın istediği tüm vaka kodlarını aynı klonda tetikleyen mutasyon kümesi."""
        f = self.f
        # V3: yerel değişmiş, yeni gelmiyor
        f.yerel_degistir("LICENSE", "MIT yerel\n")
        # V4t: taban ≠ yerel ≠ yeni, satırlar çakışmıyor (kullanıcı son satırı değiştirdi)
        # ⚠ kullanıcının değişikliği bizimkinden UZAK bir satırda olmalı: git birleşmesi
        # BİTİŞİK satır değişikliklerini de çakışma sayar (ölçüldü 2026-09-17).
        f.yerel_degistir("core/00-temel.md",
                         "CORE-ID: AXET-CORE-TEST\n# Çekirdek\nsatir1\nsatir2\nsatir3\n"
                         "satir4\nsatir5\nsatir6\nson yerel\n")
        # V4c: aynı satırda iki taraf da değişti
        f.yerel_degistir("scripts/doctor.py",
                         "#!/usr/bin/env python3\nimport sys\nprint('doctor YEREL')\nsys.exit(0)\n")
        # V5: kullanıcı silmiş, yeni yayın güncelledi
        f.yerel_sil("skills/silinen-skill/SKILL.md")
        # V6d: template sildi, kullanıcı değiştirmiş
        f.yerel_degistir("docs/silinecek.md", "silinecek YEREL\n")
        # V7: kullanıcı, template'in yeni dosyasının yoluna kendi dosyasını koydu
        f.yerel_degistir("skills/cakisan/SKILL.md", "---\nname: cakisan\n---\nKULLANICININ dosyasi\n")
        # V4B: ikili dosya iki tarafta da farklı
        f.yerel_ikili("docs/logo.png", b"\x00\x01PNG-YEREL\x00")
        # V4R: taşınan dosyanın yerelde de değişmiş olması
        f.yerel_degistir("docs/tasinan2.md", "ikinci tasinan\nX\nY\nZ yerelden\n")
        # V4t (.cmd, CRLF): kullanıcı kendi satırını ekledi
        f.yerel_degistir("kur.cmd", "@echo off\r\nrem A\r\nrem B\r\nrem C\r\necho v1\r\n"
                                    "rem D\r\nrem E\r\nrem son\r\nrem yerelden\r\n")
        # VKD: kullanıcının kendi dosyası (template hiç bilmiyor)
        f.yerel_degistir("kendi-notum.md", "benim notum\n")
        # V4e: yerel zaten yeniyle aynı
        f.yerel_degistir("config/permissions.json", '{"deny": ["a", "b"]}\n')

    def hazirla_ve_planla(self) -> subprocess.CompletedProcess:
        r = self.f.calistir("hazirla")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        return self.f.calistir("plan")

    def ozel_adimlari_kostur(self) -> None:
        """§7 adım 9: plandaki her `ozel_adim` ayrıca koşulur."""
        adlar = sorted({a for k in self.f.plan()["kalemler"] for a in k["ozel_adimlar"]})
        self.assertTrue(adlar, "fixture en az bir özel adım üretmeliydi (yoksa test anlamsız)")
        for ad in adlar:
            r = self.f.calistir("ozel-adim", ad)
            self.assertEqual(r.returncode, 0, f"{ad}: {self.cikti(r)}")


# =====================================================================================================
# 1. ÖN KONTROL / HAZIRLA
# =====================================================================================================
class OnkontrolTest(GuncelleTemel):
    def test_temiz_klonda_onkontrol_gecer(self):
        r = self.f.calistir("onkontrol")
        self.assertEqual(r.returncode, 0, self.cikti(r))

    def test_yabanci_origin_durdurur(self):
        """K4/§6: origin resmî template adresi değilse geçici kopya çıkarılmaz → DUR."""
        self.git(self.f.tuketici, "remote", "set-url", "origin",
                 "https://github.com/baskasi/fork.git")
        r = self.f.calistir("onkontrol")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertIn("origin", self.cikti(r).lower())

    def test_klon_kimligi_bozuksa_durdurur(self):
        (self.f.tuketici / "core" / "00-temel.md").unlink()
        r = self.f.calistir("onkontrol")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertIn("00-temel.md", self.cikti(r))

    def test_hazirla_etiket_ve_anlik_commit_uretir(self):
        self.f.yerel_degistir("LICENSE", "MIT yerel\n")
        r = self.f.calistir("hazirla")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        etiketler = self.git(self.f.tuketici, "tag", "--list", "guncelle-oncesi-*").stdout.split()
        self.assertEqual(len(etiketler), 1, etiketler)
        # anlık commit gerçekten yerel değişikliği taşıyor
        g = self.git(self.f.tuketici, "show", f"{etiketler[0]}:LICENSE").stdout
        self.assertEqual(g, "MIT yerel\n")

    def test_hazirla_git_kimligi_tanimsiz_ortamda_calisir(self):
        """Tüketicide git kimliği tanımsız olabilir (§2a)."""
        for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"):
            self.env.pop(k, None)
        self.f.yerel_degistir("LICENSE", "MIT yerel\n")
        r = self.f.calistir("hazirla")
        self.assertEqual(r.returncode, 0, self.cikti(r))


# =====================================================================================================
# 2. PLAN — §4 vaka kodlarının ALTIN ÇIKTISI
# =====================================================================================================
class PlanVakaTest(GuncelleTemel):
    ALTIN = {
        "scripts/doctor.py": "V4c",
        "core/00-temel.md": "V4t",
        "docs/tasinan2.md": "V4R",
        "scripts/sap_stamp.py": "V2",
        "skills/silinen-skill/SKILL.md": "V5",
        "docs/silinecek.md": "V6d",
        "skills/cakisan/SKILL.md": "V7",
        "docs/logo.png": "V4B",
        "kur.cmd": "V4t",
        "docs/tasinacak.md": "V1R",
    }

    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        r = self.hazirla_ve_planla()
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.p = self.f.plan()
        self.v = self.f.vakalar()

    def test_altin_cikti_vaka_kodlari(self):
        for yol, beklenen in self.ALTIN.items():
            self.assertEqual(self.v.get(yol), beklenen, f"{yol}: {self.v.get(yol)} ≠ {beklenen}")

    def test_islem_gerektirmeyen_kodlar_dosya_listesinde_degil_sayacta(self):
        """V3/V4e/VKD/V0 listelenmez, yalnız sayılır (§4 + §5 'işlem yok')."""
        self.assertNotIn("LICENSE", self.v, "V3 listelenmemeli")
        self.assertNotIn("config/permissions.json", self.v, "V4e listelenmemeli")
        self.assertNotIn("kendi-notum.md", self.v)
        self.assertGreaterEqual(self.p["sayaclar"].get("V3", 0), 1)
        self.assertGreaterEqual(self.p["sayaclar"].get("V4e", 0), 1)
        self.assertGreaterEqual(self.p["sayaclar"].get("VKD", 0), 1)

    def test_kullanicinin_kendi_dosyasi_hic_kapsama_girmez(self):
        """§2a: iki ağaçta da olmayan yol kullanıcınındır — VKD sayacında bile yolu geçmez."""
        metin = json.dumps(self.p, ensure_ascii=False)
        self.assertNotIn("kendi-notum.md", metin)

    def test_yeniden_adlandirma_hedef_yolu_tasir(self):
        kalem = [d for k in self.p["kalemler"] for d in k["dosyalar"] if d["yol"] == "docs/tasinacak.md"]
        self.assertEqual(len(kalem), 1)
        self.assertEqual(kalem[0].get("yeni_yol"), "docs/tasindi.md")

    def test_dosya_basi_taban_v2de_alinan_dosya_v3te_V1_olur(self):
        """§2a: uygulanan.json tabanı doğru yayına taşır; merge-base olsaydı yanlış çakışma çıkardı."""
        # doctor.py'yi v2 sürümüne getir ve "v2'de uygulandı" diye kaydet
        self.f.yerel_degistir("scripts/doctor.py", V2_DEGISIM["scripts/doctor.py"])
        d = self.f.durum_dizini()
        d.mkdir(exist_ok=True)
        (d / "uygulanan.json").write_text(json.dumps(
            {"surum": 1, "dosyalar": {"scripts/doctor.py": "v2"}, "kalemler": {}},
            ensure_ascii=False), encoding="utf-8")
        r = self.f.calistir("plan")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.f.vakalar().get("scripts/doctor.py"), "V1")

    def test_paket_ayni_dosyaya_dokunan_kalemleri_birlestirir(self):
        """§6: aynı dosyaya dokunan kalemler union-find ile tek pakete bağlanır."""
        paket = {k["id"]: k["paket"] for k in self.p["kalemler"]}
        self.assertEqual(paket["2-01"], paket["3-01"], "doctor.py'ye ikisi de dokunuyor")
        self.assertEqual(paket["2-02"], paket["3-02"], "core/00-temel.md'ye ikisi de dokunuyor")

    def test_guvenlik_kalemi_kritik_gelir(self):
        k = {x["id"]: x for x in self.p["kalemler"]}["3-03"]
        self.assertTrue(k["kritik"])

    def test_yeniden_baslat_alani_en_yuksek_gereksinimi_tasir(self):
        self.assertIn(self.p["yeniden_baslat"],
                      ("gerekmez", "yeni-oturum", "install-sonra-yeni-oturum"))
        # config/permissions.json (install-sonra-yeni-oturum) planda V4e = LİSTELENMEZ;
        # listelenenlerin en yükseği çekirdek kuralın "yeni-oturum"u.
        self.assertEqual(self.p["yeniden_baslat"], "yeni-oturum")

    def test_plan_sahte_degil_gercek_haritadan_siniflandirir(self):
        s = {d["yol"]: d["sinif"] for k in self.p["kalemler"] for d in k["dosyalar"]}
        self.assertEqual(s["core/00-temel.md"], "cekirdek-kural")
        self.assertEqual(s["kur.cmd"], "kurulum-araci-kok")
        self.assertEqual(s["skills/cakisan/SKILL.md"], "skill-govde")

    def test_null_etkinli_sinif_plana_girer_ve_kaybolmaz(self):
        """D17 tuzağı: `etkin: null` bir sınıf (kurulum-araci-kok) plandan DÜŞMEZ."""
        d = [x for k in self.p["kalemler"] for x in k["dosyalar"] if x["yol"] == "kur.cmd"]
        self.assertEqual(len(d), 1)
        self.assertIsNone(d[0]["etkin"])


class PlanKenarTest(GuncelleTemel):
    def test_hic_is_yoksa_cikis_1(self):
        """§6: `plan` 1 = güncel, iş yok."""
        # tüketiciyi v3'e getir (hiçbir fark kalmasın)
        self.git(self.f.tuketici, "merge", "-q", "--ff-only", "origin/main")
        r = self.f.calistir("plan")
        self.assertEqual(r.returncode, 1, self.cikti(r))

    def test_yayinlar_json_yoksa_cikis_2(self):
        """Eşlemesiz plan üretmek kalem sözleşmesini uydurmak olur → hata (0/1 değil)."""
        self.git(self.f.public, "rm", "-q", "guncelle/yayinlar.json")
        self.git(self.f.public, "commit", "-q", "-m", "yayinlar gitti")
        self.git(self.f.tuketici, "fetch", "-q", "--tags", "origin")
        r = self.f.calistir("plan")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertIn("yayinlar.json", self.cikti(r))

    def test_sinifsiz_dosya_plani_patlatmaz_WARN_yazar(self):
        """Harita bir yolu tanımıyorsa motor DURMAZ: `sinif: null` + görünür WARN.

        Sessizce düşürmek en tehlikeli davranış olurdu (dosya hiç güncellenmez ve kimse bilmez).
        `--harita` ile `belge-docs` sınıfı çıkarılıp `docs/**` bilerek sınıfsız bırakılıyor.
        """
        harita = json.loads(HARITA.read_text(encoding="utf-8"))
        harita["siniflar"] = [k for k in harita["siniflar"] if k["sinif"] != "belge-docs"]
        kirpik = self.tmp / "harita-kirpik.json"
        kirpik.write_text(json.dumps(harita, ensure_ascii=False), encoding="utf-8")
        self.f.yerel_degistir("docs/silinecek.md", "silinecek YEREL\n")
        self.assertEqual(self.f.calistir("hazirla").returncode, 0)
        r = self.f.calistir("--harita", str(kirpik), "plan")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("sınıfsız", self.cikti(r))
        d = [x for k in self.f.plan()["kalemler"] for x in k["dosyalar"]
             if x["yol"] == "docs/silinecek.md"]
        self.assertEqual(len(d), 1, "sınıfsız dosya plandan DÜŞMEMELİ")
        self.assertIsNone(d[0]["sinif"])

    def test_taban_bulunamazsa_VTB(self):
        """§4: klonda taban commit'i yoksa (sığ klon/force push izi) otomatik işlem YASAK."""
        d = self.f.durum_dizini()
        d.mkdir(exist_ok=True)
        (d / "uygulanan.json").write_text(json.dumps(
            {"surum": 1, "dosyalar": {"scripts/doctor.py": "yok-boyle-etiket"}, "kalemler": {}},
            ensure_ascii=False), encoding="utf-8")
        self.f.yerel_degistir("scripts/doctor.py", "print('yerel baska')\n")
        r = self.f.calistir("plan")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.f.vakalar().get("scripts/doctor.py"), "VTB")


# =====================================================================================================
# 3. `etkin`in BEŞ değeri (D17 kayıtlı tuzak)
# =====================================================================================================
class EtkinBesDegerTest(unittest.TestCase):
    """harita.json'daki `etkin` enum'unun 5 değeri var ve 5.si `null`; 38 sınıfın 13'ü null.
    Dört değer varsayan bir zincir o sınıfları sessizce "bilinmeyen" kovasına düşürür (D17)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(AXET_HOME / "scripts"))
        import guncelle  # noqa: PLC0415
        cls.g = guncelle
        cls.harita = json.loads(HARITA.read_text(encoding="utf-8"))

    def test_haritadaki_her_etkin_degeri_acikca_ele_alinir(self):
        for deger in self.harita["etkin_degerleri"]:
            with self.subTest(etkin=deger):
                self.assertIn(deger, self.g.ETKIN_DAVRANIS,
                              f"`etkin={deger!r}` motorda ele alınmıyor — sessizce bilinmeyen kovasına düşer")

    def test_null_ayri_bir_dal_gerekmez_demek(self):
        self.assertIsNone(self.g.ETKIN_DAVRANIS[None]["yeniden_baslat"])

    def test_bilinmeyen_etkin_sessizce_duşmez_patlar(self):
        """Yeni bir 6. değer eklenirse motor SESSİZ kalmaz (fail-loud)."""
        with self.assertRaises(self.g.BilinmeyenEtkin):
            self.g.etkin_davranis("altinci-deger")

    def test_null_sinif_sayisi_haritayla_tutarli(self):
        n = sum(1 for k in self.harita["siniflar"] if k.get("etkin") is None)
        self.assertGreaterEqual(n, 1, "harita'da hiç null yoksa bu tuzak testi anlamını yitirmiştir")


# =====================================================================================================
# 4. SEÇİM
# =====================================================================================================
class SecTest(GuncelleTemel):
    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)

    def test_hepsi_tum_kalemleri_secer(self):
        r = self.f.calistir("sec", "--hepsi")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        s = json.loads((self.f.durum_dizini() / "secim.json").read_text(encoding="utf-8"))
        self.assertEqual(len(s["kalemler"]), len(self.f.plan()["kalemler"]))

    def test_kritikler_varsayilan_secili(self):
        r = self.f.calistir("sec")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        s = json.loads((self.f.durum_dizini() / "secim.json").read_text(encoding="utf-8"))
        self.assertIn("3-03", s["kalemler"])

    def test_gerektirir_karsilanmazsa_cikis_2(self):
        """§6: seçilen kalemin bağımlılığı seçilmemişse `sec` çıkış 2."""
        r = self.f.calistir("sec", "--kalem", "3-05", "--cikar", "3-01")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertIn("3-01", self.cikti(r))

    def test_secim_paket_biriminde(self):
        """Q2: aynı dosyaya dokunan kalemler birlikte seçilir."""
        r = self.f.calistir("sec", "--kalem", "2-01")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        s = json.loads((self.f.durum_dizini() / "secim.json").read_text(encoding="utf-8"))
        self.assertIn("3-01", s["kalemler"], "2-01 ile 3-01 aynı pakette (doctor.py)")


# =====================================================================================================
# 5. UYGULA (otomatik vakalar)
# =====================================================================================================
class UygulaTest(GuncelleTemel):
    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)

    def test_otomatik_vakalar_yazilir_ve_dogrulanir(self):
        r = self.f.calistir("uygula", "--otomatik")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        d = self.f.durum()["dosyalar"]
        # V2 — yeni dosya
        self.assertTrue((self.f.tuketici / "scripts/sap_stamp.py").exists())
        self.assertEqual(d["scripts/sap_stamp.py"]["durum"], "dogrulandi")
        # V5 — geri getirildi + görünür log
        self.assertTrue((self.f.tuketici / "skills/silinen-skill/SKILL.md").exists())
        self.assertIn("GERİ GETİRİLDİ", self.cikti(r))
        # V1R — taşındı
        self.assertTrue((self.f.tuketici / "docs/tasindi.md").exists())
        self.assertFalse((self.f.tuketici / "docs/tasinacak.md").exists())

    def test_yargi_vakalarina_uygula_dokunmaz(self):
        self.f.calistir("uygula", "--otomatik")
        # V4c dosyası yerelde kalmalı
        self.assertIn("doctor YEREL", (self.f.tuketici / "scripts/doctor.py").read_text(encoding="utf-8"))
        # V7 dosyası kullanıcınınki kalmalı
        self.assertIn("KULLANICININ",
                      (self.f.tuketici / "skills/cakisan/SKILL.md").read_text(encoding="utf-8"))
        # V6d silinmemeli
        self.assertTrue((self.f.tuketici / "docs/silinecek.md").exists())

    def test_V6_silinir_ama_V6d_silinmez(self):
        self.f.calistir("uygula", "--otomatik")
        d = self.f.durum()["dosyalar"]
        self.assertEqual(d["docs/silinecek.md"]["vaka"], "V6d")
        self.assertNotIn(d["docs/silinecek.md"]["durum"], ("dogrulandi",),
                         "V6d otomatik kapanamaz — kullanıcıya bilgi vakasıdır")

    def test_secilmeyen_pakete_dokunmaz(self):
        # yeniden seç: yalnız 3-03 (kritik) paketi
        self.assertEqual(self.f.calistir("sec", "--kalem", "3-03").returncode, 0)
        self.f.calistir("uygula", "--otomatik")
        self.assertFalse((self.f.tuketici / "scripts/sap_stamp.py").exists())
        self.assertEqual((self.f.tuketici / "config/permissions.json")
                         .read_text(encoding="utf-8"), '{"deny": ["a", "b"]}\n')


# =====================================================================================================
# 6. ÖNERİ / İŞARETLE
# =====================================================================================================
class OneriIsaretleTest(GuncelleTemel):
    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)

    def test_V4t_temiz_birlesme_cikis_0(self):
        r = self.f.calistir("oneri", "core/00-temel.md")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        o = (self.f.durum_dizini() / "oneri" / "core/00-temel.md").read_text(encoding="utf-8")
        self.assertIn("# Çekirdek v3", o, "bizim değişikliğimiz")
        self.assertIn("son yerel", o, "kullanıcının değişikliği")
        self.assertNotIn("<<<<<<<", o)

    def test_V4t_iki_fark_ayri_ayri_basilir(self):
        c = self.cikti(self.f.calistir("oneri", "core/00-temel.md"))
        self.assertIn("T→L", c)
        self.assertIn("T→Y", c)

    def test_V4c_cakisma_cikis_1_ve_isaretli_dosya(self):
        r = self.f.calistir("oneri", "scripts/doctor.py")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        o = (self.f.durum_dizini() / "oneri" / "scripts/doctor.py").read_text(encoding="utf-8")
        self.assertIn("<<<<<<<", o)

    def test_esik_asilirsa_cikis_3_ve_elle_diff(self):
        """K6(a): >3 çakışma bloğu ya da yerel fark >%50 → birleştirme denenmez."""
        self.f.yerel_degistir("core/00-temel.md", "tamamen\nbaska\nbir\nicerik\nburada\n")
        self.assertEqual(self.f.calistir("plan").returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)
        r = self.f.calistir("oneri", "core/00-temel.md")
        self.assertEqual(r.returncode, 3, self.cikti(r))
        self.assertTrue((self.f.durum_dizini() / "elle" / "core/00-temel.md.yerel.diff").exists())
        self.assertTrue((self.f.durum_dizini() / "elle" / "core/00-temel.md.yeni.diff").exists())

    def test_isaretle_birlesik_yazar_ve_geri_okuyup_dogrular(self):
        self.f.calistir("oneri", "core/00-temel.md")
        r = self.f.calistir("isaretle", "core/00-temel.md", "--karar", "birlesik")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.f.durum()["dosyalar"]["core/00-temel.md"]["durum"], "dogrulandi")
        disk = (self.f.tuketici / "core/00-temel.md").read_text(encoding="utf-8")
        self.assertIn("# Çekirdek v3", disk)
        self.assertIn("son yerel", disk)

    def test_isaretle_cakisma_isareti_kalirsa_cikis_1(self):
        """§5 V4c adım 5: script çakışma işareti kalmadığını doğrular."""
        self.f.calistir("oneri", "scripts/doctor.py")
        r = self.f.calistir("isaretle", "scripts/doctor.py", "--karar", "birlesik")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("<<<<<<<", self.cikti(r))

    def test_isaretle_yeni_ve_yerel_kararlari(self):
        r = self.f.calistir("isaretle", "docs/logo.png", "--karar", "yeni")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual((self.f.tuketici / "docs/logo.png").read_bytes(), b"\x00\x01PNG-v3\x00")
        r = self.f.calistir("isaretle", "docs/silinecek.md", "--karar", "yerel")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual((self.f.tuketici / "docs/silinecek.md").read_text(encoding="utf-8"),
                         "silinecek YEREL\n")

    def test_isaretle_yeniden_adlandir_kullanicinin_dosyasini_korur(self):
        r = self.f.calistir("isaretle", "skills/cakisan/SKILL.md", "--karar", "yeniden-adlandir")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("KULLANICININ", (self.f.tuketici / "skills/cakisan/SKILL.md.yerel")
                      .read_text(encoding="utf-8"))
        self.assertIn("template surumu", (self.f.tuketici / "skills/cakisan/SKILL.md")
                      .read_text(encoding="utf-8"))

    def test_isaretle_gecersiz_karar_cikis_2(self):
        r = self.f.calistir("isaretle", "core/00-temel.md", "--karar", "uydurma")
        self.assertEqual(r.returncode, 2, self.cikti(r))

    def test_ertelendi_gerekce_ister(self):
        r = self.f.calistir("isaretle", "core/00-temel.md", "--karar", "ertelendi")
        self.assertEqual(r.returncode, 2, self.cikti(r))
        r = self.f.calistir("isaretle", "core/00-temel.md", "--karar", "ertelendi",
                            "--gerekce", "elle bakılacak")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.f.durum()["dosyalar"]["core/00-temel.md"]["durum"], "atlandi")

    def test_crlf_dosyada_birlesme_satir_sonunu_bozmaz(self):
        """TASARIM §14 DOĞRULANMADI kalemi: `git merge-file` CRLF/LF karışık dosyada.
        `kur.cmd` deposunda LF, çalışma ağacında CRLF (`.gitattributes` eol=crlf)."""
        r = self.f.calistir("oneri", "kur.cmd")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual(self.f.calistir("isaretle", "kur.cmd", "--karar", "birlesik").returncode,
                         0)
        ham = (self.f.tuketici / "kur.cmd").read_bytes()
        self.assertIn(b"rem yerelden", ham)
        self.assertIn(b"rem bizden", ham)
        self.assertEqual(ham.count(b"\r\n"), ham.count(b"\n"),
                         "çalışma ağacında HER satır sonu CRLF olmalı (eol=crlf); çıplak LF "
                         "kalırsa cmd.exe goto/etiket satırlarını yanlış okur")
        self.assertNotIn(b"\r\r\n", ham, "satır sonu ikizlenmesi (CR çoğaldı)")


# =====================================================================================================
# 7. ÖLÇÜM / BÜTÜNLÜK / GERİ AL / KAPANIŞ / DURUM
# =====================================================================================================
class AkisTest(GuncelleTemel):
    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)

    def _tum_yargilari_kapat(self) -> None:
        for yol, karar in (("core/00-temel.md", "yeni"), ("scripts/doctor.py", "yeni"),
                           ("kur.cmd", "yeni"), ("docs/logo.png", "yeni"),
                           ("docs/tasinan2.md", "yeni"),
                           ("skills/cakisan/SKILL.md", "yeniden-adlandir"),
                           ("docs/silinecek.md", "yerel")):
            r = self.f.calistir("isaretle", yol, "--karar", karar)
            self.assertEqual(r.returncode, 0, f"{yol}: {self.cikti(r)}")

    def test_olc_once_ve_sonra_kaydeder(self):
        r = self.f.calistir("olc", "--asama", "once")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        veri = json.loads((self.f.durum_dizini() / "olcum-once.json").read_text(encoding="utf-8"))
        self.assertTrue(veri["testler"], "en az bir test komutu seçilmeliydi")

    def test_olc_gecersiz_asama_cikis_2(self):
        self.assertEqual(self.f.calistir("olc", "--asama", "ortada").returncode, 2)

    def test_geri_al_tek_dosya(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self.assertTrue((self.f.tuketici / "scripts/sap_stamp.py").exists())
        r = self.f.calistir("geri-al", "scripts/sap_stamp.py")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertFalse((self.f.tuketici / "scripts/sap_stamp.py").exists(),
                         "tabanda olmayan dosya geri almada silinmeli")

    def test_geri_al_hepsi_yerel_degisikligi_korur(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        r = self.f.calistir("geri-al", "--hepsi")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertEqual((self.f.tuketici / "LICENSE").read_text(encoding="utf-8"), "MIT yerel\n")
        self.assertIn("doctor YEREL",
                      (self.f.tuketici / "scripts/doctor.py").read_text(encoding="utf-8"))

    def test_durum_tablo_basar(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        r = self.f.calistir("durum")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("scripts/sap_stamp.py", self.cikti(r))
        self.assertIn("dogrulandi", self.cikti(r))

    # --- §12a KAPANIŞ MUTASYONLARI -------------------------------------------------------------
    def test_kapanis_bekleyen_dosya_varsa_1(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("KAPANMADI", (self.f.durum_dizini() / "RAPOR.md").read_text(encoding="utf-8"))

    def test_kapanis_durum_json_elle_dogrulandi_yapilirsa_disk_farkli_1(self):
        """§6: ajanın 'yaptım' demesi durum değiştirmez — kapanış diskten yeniden doğrular.

        ⚠ Akışın GERİ KALANI tamamlanır (ölçüm + özel adım + bütünlük), yoksa `kapanis` zaten
        başka bir sebeple 1 döner ve test bu kuralı ölçmemiş olur. Mutasyon M4 ilk hâlinde tam
        olarak bunu gösterdi: disk doğrulaması kapatıldığı hâlde test YEŞİL kalıyordu.
        """
        self.assertEqual(self.f.calistir("olc", "--asama", "once").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self._tum_yargilari_kapat()
        self.ozel_adimlari_kostur()
        self.assertEqual(self.f.calistir("olc", "--asama", "sonra").returncode, 0)
        self.assertEqual(self.f.calistir("butunluk").returncode, 0)
        # kontrol grubu: bu noktada akış TEMİZ kapanmalı
        self.assertEqual(self.f.calistir("kapanis").returncode, 0,
                         "kontrol grubu kırmızıysa asıl ölçüm anlamsız")
        d = self.f.durum()
        for k in d["dosyalar"].values():
            k["durum"] = "dogrulandi"
        (self.f.durum_dizini() / "durum.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        # diski boz
        self.f.yerel_degistir("scripts/sap_stamp.py", "elle bozuldu\n")
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("scripts/sap_stamp.py", self.cikti(r))

    def test_kapanis_kabul_ile_cikis_3_ve_gerekce_raporda(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        r = self.f.calistir("kapanis", "--kabul", "bilerek yarım bırakıldı")
        self.assertEqual(r.returncode, 3, self.cikti(r))
        rapor = (self.f.durum_dizini() / "RAPOR.md").read_text(encoding="utf-8")
        self.assertIn("bilerek yarım bırakıldı", rapor)

    def test_ozel_adim_kosar_ve_duruma_yazilir(self):
        self.ozel_adimlari_kostur()
        ozel = self.f.durum()["ozel_adimlar"]
        self.assertTrue(ozel)
        self.assertTrue(all(v["durum"] in ("kostu", "manuel") for v in ozel.values()), ozel)

    def test_ozel_adim_bilinmeyen_sinif_cikis_2(self):
        self.assertEqual(self.f.calistir("ozel-adim", "boyle-bir-sinif-yok").returncode, 2)

    def test_kapanis_tamamlanmis_akista_0_ve_uygulanan_json_guncellenir(self):
        self.assertEqual(self.f.calistir("olc", "--asama", "once").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self._tum_yargilari_kapat()
        self.ozel_adimlari_kostur()
        self.assertEqual(self.f.calistir("olc", "--asama", "sonra").returncode, 0)
        self.assertEqual(self.f.calistir("butunluk").returncode, 0)
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        u = json.loads((self.f.durum_dizini() / "uygulanan.json").read_text(encoding="utf-8"))
        self.assertEqual(u["dosyalar"]["scripts/sap_stamp.py"], "v3")
        self.assertIn("3-01", u["kalemler"])
        # kapanış commit'i atıldı
        son = self.git(self.f.tuketici, "log", "-1", "--format=%s").stdout
        self.assertTrue(son.startswith("guncelle:"), son)

    def test_kapanis_butunluk_kosmamissa_1(self):
        self.assertEqual(self.f.calistir("olc", "--asama", "once").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self._tum_yargilari_kapat()
        self.ozel_adimlari_kostur()
        self.assertEqual(self.f.calistir("olc", "--asama", "sonra").returncode, 0)
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("bütünlük", self.cikti(r).lower())

    def test_kapanis_yeni_kirmizi_testte_1(self):
        self.assertEqual(self.f.calistir("olc", "--asama", "once").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self._tum_yargilari_kapat()
        self.ozel_adimlari_kostur()
        self.assertEqual(self.f.calistir("olc", "--asama", "sonra").returncode, 0)
        self.assertEqual(self.f.calistir("butunluk").returncode, 0)
        # sonra-ölçümüne elle yeni kırmızı koy
        y = self.f.durum_dizini() / "olcum-sonra.json"
        veri = json.loads(y.read_text(encoding="utf-8"))
        for t in veri["testler"]:
            t["cikis"] = 1
        y.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("kırmızı", self.cikti(r).lower())

    def test_kapanis_ozel_adim_kosmamissa_1(self):
        """config/permissions.json sınıfının özel adımı (install.py) koşmadan kapanmaz."""
        # permissions.json'u V4e'den çıkar: yerelde tabana döndür → V1 olur, özel adım gerekir
        self.f.yerel_degistir("config/permissions.json", '{"deny": ["a"]}\n')
        self.assertEqual(self.f.calistir("plan").returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)
        self.assertEqual(self.f.calistir("olc", "--asama", "once").returncode, 0)
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self._tum_yargilari_kapat()
        self.assertEqual(self.f.calistir("olc", "--asama", "sonra").returncode, 0)
        self.assertEqual(self.f.calistir("butunluk").returncode, 0)
        r = self.f.calistir("kapanis")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("özel adım", self.cikti(r).lower())

    def test_rapor_kapsam_beyani_iceriyor(self):
        self.assertEqual(self.f.calistir("uygula", "--otomatik").returncode, 0)
        self.f.calistir("kapanis")
        rapor = (self.f.durum_dizini() / "RAPOR.md").read_text(encoding="utf-8")
        self.assertIn("KAPSAM —", rapor)
        self.assertIn("bakılmayanlar", rapor)


class ButunlukTest(GuncelleTemel):
    def setUp(self) -> None:
        super().setUp()
        self.senaryolari_uygula()
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)
        self.assertEqual(self.f.calistir("sec", "--hepsi").returncode, 0)

    def test_butunluk_install_dry_run_ve_doctor_kosar(self):
        r = self.f.calistir("butunluk")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        b = json.loads((self.f.durum_dizini() / "butunluk.json").read_text(encoding="utf-8"))
        adlar = [x["ad"] for x in b["adimlar"]]
        self.assertIn("install --dry-run", adlar)
        self.assertIn("doctor", adlar)

    def test_doctor_kirmiziysa_butunluk_1(self):
        self.f.yerel_degistir("scripts/doctor.py", "import sys\nprint('kirmizi')\nsys.exit(1)\n")
        r = self.f.calistir("butunluk")
        self.assertEqual(r.returncode, 1, self.cikti(r))

    def test_asgari_guvence_yerelde_degismis_kanonigi_bildirir(self):
        """§8 adım 7: engellemez ama WARN satırı yazar."""
        r = self.f.calistir("butunluk")
        b = json.loads((self.f.durum_dizini() / "butunluk.json").read_text(encoding="utf-8"))
        metin = json.dumps(b, ensure_ascii=False) + self.cikti(r)
        self.assertIn("asgari güvence", metin.lower())


class MotorBagimsizligiTest(GuncelleTemel):
    """K4 lider notu: motor klondaki (eski olabilecek) `scripts/*.py`'yi IMPORT ETMEZ."""

    def test_klondaki_bozuk_modul_plani_etkilemez(self):
        self.senaryolari_uygula()
        for ad in ("behavior_manifest.py", "doctor.py", "install.py", "siniflandir.py"):
            hedef = self.f.tuketici / ("guncelle/" + ad if ad == "siniflandir.py"
                                       else "scripts/" + ad)
            hedef.parent.mkdir(parents=True, exist_ok=True)
            hedef.write_text("raise RuntimeError('eski bozuk motor')\n", encoding="utf-8")
        self.assertEqual(self.hazirla_ve_planla().returncode, 0)
        self.assertEqual(self.f.vakalar().get("core/00-temel.md"), "V4t")

    def test_kaynak_metninde_klon_scriptleri_import_edilmiyor(self):
        metin = GUNCELLE_PY.read_text(encoding="utf-8")
        for yasak in ("import doctor", "import install", "import behavior_manifest",
                      "import new_project", "import session_brief"):
            self.assertNotIn(yasak, metin, f"K4 ihlali: {yasak}")


class KartTest(GuncelleTemel):
    def test_kart_yoksa_cikis_2(self):
        r = self.f.calistir("kart", "V4c")
        self.assertEqual(r.returncode, 2, self.cikti(r))

    def test_kart_yeni_surumden_okunur(self):
        self.f._yaz(self.f.public, {"guncelle/kartlar/V4c.md": "# V4c\nkart gövdesi\n"})
        self.git(self.f.public, "add", "-A")
        self.git(self.f.public, "commit", "-q", "-m", "kart")
        self.git(self.f.tuketici, "fetch", "-q", "--tags", "origin")
        # yerel kopya BOZUK olsun — kart yine de yeni sürümden gelmeli
        self.f.yerel_degistir("guncelle/kartlar/V4c.md", "BOZUK YEREL\n")
        r = self.f.calistir("kart", "V4c")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("kart gövdesi", self.cikti(r))
        self.assertNotIn("BOZUK", self.cikti(r))


def _uret_elle(hedef: str) -> int:
    """`python tests/test_guncelle.py --uret <dizin>` — fixture'ı elle inceleme için üretir."""
    import tempfile

    class _Sahte(GeciciTest):
        def runTest(self):  # pragma: no cover
            pass

    t = _Sahte()
    t.setUp()
    try:
        kok = Path(hedef).resolve()
        kok.mkdir(parents=True, exist_ok=True)
        t.tmp = kok
        f = SahteYayin(t, kok).uret()
        print(f"public : {f.public}\ntüketici: {f.tuketici}")
        print(f"dene   : python {GUNCELLE_PY} --klon {f.tuketici} plan")
        return 0
    finally:
        tempfile  # noqa: B018


if __name__ == "__main__":
    if "--uret" in sys.argv:
        raise SystemExit(_uret_elle(sys.argv[sys.argv.index("--uret") + 1]))
    unittest.main()
