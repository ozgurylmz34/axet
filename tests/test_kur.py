# -*- coding: utf-8 -*-
"""kur.cmd / kur.ps1 — son kullanıcı kurulum aracı. Yerel bare repo kaynak olarak kullanılır (ağ yok), config geçici
XDG_CONFIG_HOME'a yazılır, winget hiçbir testte gerçek hâliyle çağrılmaz (-WingetKapali ya da PATH'in başında sahte
winget). Windows'a özgüdür; başka platformda atlanır.

KAPSAM — bakılmayanlar: gerçek winget kurulumu ve sonrasında PATH yenileme · GitHub'dan klon (ağ) · etkileşimli
terminalde soru-yanıt (yalnız kapalı stdin ve -Evet ölçülür) · aXet'in yeni config'i fiilen yüklediği (doctor --live) ·
beklenmeyen istisna dalı (dış try/catch) · py launcher'ın ASCII olmayan yolları listelemesi."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import AXET_HOME, GeciciTest, _sil

KUR_CMD = AXET_HOME / "kur.cmd"
KUR_PS1 = AXET_HOME / "kur.ps1"
WINDOWS = os.name == "nt"
SYS32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
POWERSHELL = SYS32 / "WindowsPowerShell" / "v1.0" / "powershell.exe"
COMSPEC = os.environ.get("COMSPEC", str(SYS32 / "cmd.exe"))


def _goruntu(kok: Path) -> dict | None:
    """Klasördeki dosyaların (göreli yol -> boyut, mtime, sha256) görüntüsü; klasör yoksa None. Yalnız testin kendi
    geçici klasörleri için kullanılır."""
    if not kok.exists():
        return None
    sonuc = {}
    for p in sorted(kok.rglob("*")):
        if p.is_file():
            st = p.stat()
            sonuc[str(p.relative_to(kok))] = (st.st_size, st.st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
    return sonuc


def _gercek_damga() -> dict:
    """Gerçek kullanıcı config'i ve aXet yerel klasöründe kurulumun dokunabileceği dosyaların boyut+mtime damgası.

    Karar: içerik okunmaz, klasör taranmaz. install.py yalnız global config'i ve yanına `.bak-*` yedeğini yazar →
    config dosyası + yedek adları izlenir. %LOCALAPPDATA%\\axet-code'a kur.ps1 hiç yazmaz; oradan yalnız aXet'in
    ayar/kimlik dosyaları (axet-code.json, skills_manifest.json, auth.enc) boyut+mtime ile izlenir. Klasörün tamamını
    (93 MB ikili dahil) hash'lemek yavaştı, açık bir aXet oturumunun değiştirdiği dosyalarda sahte hata verebilirdi ve
    auth.enc'in içeriği okunmamalı."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    cfg_dizin = (Path(xdg) if xdg else Path.home() / ".config") / "axet-code"
    izlenen = [cfg_dizin / "axet-code.json"]
    if os.environ.get("LOCALAPPDATA"):
        lad = Path(os.environ["LOCALAPPDATA"]) / "axet-code"
        izlenen += [lad / "axet-code.json", lad / "skills_manifest.json", lad / "auth.enc"]
    damga: dict = {}
    for f in izlenen:
        damga[str(f)] = (f.stat().st_size, f.stat().st_mtime_ns) if f.is_file() else None
    damga["yedekler"] = sorted(p.name for p in cfg_dizin.glob("axet-code.json.bak-*")) if cfg_dizin.is_dir() else None
    return damga


@unittest.skipUnless(WINDOWS and KUR_CMD.exists() and POWERSHELL.exists(), "yalnız Windows (kur.cmd + PowerShell 5.1)")
class KurTest(GeciciTest):
    @classmethod
    def setUpClass(cls) -> None:
        cls._once = _gercek_damga()
        cls.sinif_tmp = Path(tempfile.mkdtemp(prefix="axet-kur-")).resolve()
        cls.kaynak_sablon = cls.sinif_tmp / "kaynak.git"
        r = subprocess.run(["git", "clone", "-q", "--bare", str(AXET_HOME), str(cls.kaynak_sablon)],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
        if r.returncode != 0:
            raise RuntimeError(f"bare klon oluşturulamadı: {r.stderr}")

    @classmethod
    def tearDownClass(cls) -> None:
        _sil(cls.sinif_tmp)
        sonra = _gercek_damga()
        if sonra != cls._once:
            raise AssertionError(f"GERÇEK aXet config/yerel dosyası testte değişti:\nönce={cls._once}\nsonra={sonra}")

    def setUp(self) -> None:
        super().setUp()
        self.kaynak = self.tmp / "kaynak.git"
        shutil.copytree(self.kaynak_sablon, self.kaynak)
        self.hedef = self.tmp / "hedef"
        self.cfg = self.xdg / "axet-code" / "axet-code.json"

    # --- yardımcılar ------------------------------------------------------------------------------------------
    def kur(self, *args: str, env: dict | None = None, winget_kapali: bool = True,
            varsayilan: bool = True, hedef: Path | None = None) -> subprocess.CompletedProcess:
        """kur.cmd'yi çağırır. varsayilan=True: -Kaynak <geçici bare> -Hedef <hedef> önden eklenir."""
        arglar = list(args)
        if varsayilan:
            arglar = ["-Kaynak", str(self.kaynak), "-Hedef", str(hedef or self.hedef)] + arglar
        if winget_kapali:
            arglar.append("-WingetKapali")
        return subprocess.run([COMSPEC, "/c", str(KUR_CMD), *arglar], env=env or self.env, cwd=str(self.tmp),
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=600)

    def cfg_oku(self) -> dict:
        return json.loads(self.cfg.read_text(encoding="utf-8"))

    def uzakta_commit(self, dosya: str = "YENI.txt", kaynak: Path | None = None) -> None:
        """Kaynak bare repoya yeni bir commit iter (klonun geride kalmasını sağlar)."""
        kaynak = kaynak or self.kaynak
        is_klonu = self.tmp / f"is-{kaynak.name}"
        if not is_klonu.exists():
            self.git(self.tmp, "clone", "-q", str(kaynak), str(is_klonu))
        self.yaz(is_klonu / dosya, "uzakta eklendi\n")
        self.git(is_klonu, "add", dosya)
        self.git(is_klonu, "commit", "-q", "-m", f"test: {dosya}")
        self.git(is_klonu, "push", "-q", "origin", "HEAD")

    def kurulu(self) -> None:
        r = self.kur("-Evet")
        self.assertEqual(r.returncode, 0, self.cikti(r))

    def sahte_winget(self) -> tuple[Path, Path]:
        """Çağrıyı dosyaya kaydedip hata dönen sahte winget.cmd; (klasör, kayıt dosyası)."""
        bin_ = self.tmp / "_bin"
        bin_.mkdir(exist_ok=True)
        kayit = self.tmp / "winget-cagri.txt"
        (bin_ / "winget.cmd").write_text(f'@echo off\r\necho %* >> "{kayit}"\r\nexit /b 1\r\n', encoding="ascii")
        return bin_, kayit

    @staticmethod
    def path_degistir(env: dict, yeni: str) -> dict:
        env = dict(env)
        for k in list(env):
            if k.upper() == "PATH":
                del env[k]
        env["PATH"] = yeni
        return env

    @staticmethod
    def path_oku(env: dict) -> str:
        return next(v for k, v in env.items() if k.upper() == "PATH")

    def dar_ortam(self, axet: bool) -> tuple[dict, Path]:
        """PATH'te yalnız: 0 baytlık sahte python.exe/python3.exe + çağrıyı kaydeden sahte winget + System32 + PowerShell.
        LOCALAPPDATA geçici klasör (gerçek aXet görünmesin; axet=True ise sahte axet-code.exe konur)."""
        bin_, kayit = self.sahte_winget()
        (bin_ / "python.exe").write_bytes(b"")
        (bin_ / "python3.exe").write_bytes(b"")
        lad = self.tmp / "_localappdata"
        lad.mkdir()
        if axet:
            (lad / "axet-code" / "bin").mkdir(parents=True)
            (lad / "axet-code" / "bin" / "axet-code.exe").write_bytes(b"")
        env = self.path_degistir(self.env, os.pathsep.join([str(bin_), str(SYS32), str(POWERSHELL.parent)]))
        env["LOCALAPPDATA"] = str(lad)
        return env, kayit

    def yabanci_repo(self, ad: str) -> tuple[Path, Path]:
        """scripts/install.py + scripts/doctor.py + skills-sap/ + core/00-temel.md taşıyan ama `CORE-ID: AXET-CORE-`
        imzası OLMAYAN yabancı bare repo; (bare, işaret dosyası). Yabancı betik çalışırsa işaret dosyasını yazar."""
        isaret = self.tmp / f"YABANCI_{ad}_CALISTI.txt"
        bare = self.tmp / f"{ad}.git"
        is_ = self.tmp / f"{ad}-is"
        self.git(self.tmp, "init", "-q", "--bare", "-b", "main", str(bare))
        self.git(self.tmp, "clone", "-q", str(bare), str(is_))
        betik = f"import sys\nopen(r'{isaret}', 'a', encoding='utf-8').write(' '.join(sys.argv) + '\\n')\n"
        self.yaz(is_ / "scripts" / "install.py", betik)
        self.yaz(is_ / "scripts" / "doctor.py", betik)
        self.yaz(is_ / "skills-sap" / "README.md", "yabancı\n")
        self.yaz(is_ / "core" / "00-temel.md", "# başka bir proje\nCORE-ID: BASKA-0.1\n")
        self.git(is_, "add", "-A")
        self.git(is_, "commit", "-q", "-m", "yabanci ilk")
        self.git(is_, "push", "-q", "origin", "main")
        return bare, isaret

    # --- dosya biçimi -----------------------------------------------------------------------------------------
    def test_ps1_bomlu_utf8_ve_cmd_ascii(self):
        # Ölçüldü: PS 5.1 BOM'suz UTF-8 .ps1'i ANSI okur, Türkçe dizgeler bozulur.
        self.assertEqual(KUR_PS1.read_bytes()[:3], b"\xef\xbb\xbf")
        KUR_CMD.read_bytes().decode("ascii")  # cmd.exe kod sayfasından bağımsız kalsın
        metin = KUR_PS1.read_text(encoding="utf-8-sig").lower()
        self.assertNotIn("sap-write", metin)  # Y1: yazma izni ne çalıştırılır ne önerilir
        self.assertNotIn("invoke-expression", metin)
        self.assertIn("install.py", metin)
        self.assertIn("--sap", metin)

    # --- kurulum / güncelleme ---------------------------------------------------------------------------------
    def test_ilk_kurulum_klonlar_sap_config_yazar_doctor_calisir(self):
        r = self.kur("-Evet")
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertTrue((self.hedef / ".git").is_dir())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())
        ctx = self.cfg_oku()["options"]["context_paths"]
        skills = self.cfg_oku()["options"]["skills_paths"]
        self.assertIn((self.hedef / "core" / "00-temel.md").as_posix(), ctx)
        self.assertIn((self.hedef / "core" / "sap").as_posix(), ctx)
        self.assertIn((self.hedef / "skills-sap").as_posix(), skills)
        self.assertIn("SONUÇ: 0 FAIL", c)  # doctor.py koştu
        self.assertIn("Kurulum tamam (yeni klon)", c)
        self.assertIn("YENİ bir aXet oturumu aç", c)  # Türkçe çıktı bozulmadan geldi
        self.assertIn("AXET-CORE", c)
        self.assertIn("%yeni-proje", c)
        self.assertNotIn("beklenmeyen hata", c)

    def test_tekrar_calistirma_degisiklik_yok_sonra_guncelleme(self):
        self.kurulu()
        head = self.git(self.hedef, "rev-parse", "HEAD").stdout.strip()
        r = self.kur("-Evet")
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn("Değişiklik yok; klon zaten güncel.", c)
        self.assertIn("Config zaten bu klonu gösteriyor", c)
        self.assertNotIn("önceki kurulum şu klonu gösteriyordu", c)
        self.assertNotIn("klonun kaynağı", c)  # origin == kaynak -> uyarı yok
        self.assertEqual(self.git(self.hedef, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(self.git(self.hedef, "status", "--porcelain").stdout.strip(), "")

        self.uzakta_commit()
        r = self.kur("-Evet")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("Güncellendi (1 yeni commit)", self.cikti(r))
        self.assertTrue((self.hedef / "YENI.txt").is_file())

    def test_origin_harf_ve_git_eki_farki_uyari_vermez(self):
        self.kurulu()
        ayni = str(self.kaynak).upper()
        self.assertTrue(ayni.endswith(".GIT"))
        ayni = ayni[:-4]  # aynı kaynak: harf farkı + .git eki yok
        r = self.kur("-Kaynak", ayni, "-Hedef", str(self.hedef), "-Evet", varsayilan=False)
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertNotIn("klonun kaynağı", self.cikti(r))
        # kontrol grubu: gerçekten farklı bir kaynak uyarı verir
        r = self.kur("-Kaynak", str(self.tmp / "baska.git"), "-Hedef", str(self.hedef), "-Evet", varsayilan=False)
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("klonun kaynağı", self.cikti(r))

    def test_yerel_degisiklik_varsa_guncellemez_dosyayi_korur(self):
        self.kurulu()
        self.uzakta_commit()
        head = self.git(self.hedef, "rev-parse", "HEAD").stdout.strip()
        readme = self.hedef / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nyerel not\n", encoding="utf-8")
        icerik = readme.read_bytes()
        r = self.kur("-Evet")
        self.assertNotEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("yerel değişiklik var", self.cikti(r))
        self.assertEqual(readme.read_bytes(), icerik)
        self.assertEqual(self.git(self.hedef, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertFalse((self.hedef / "YENI.txt").exists())
        self.assertEqual(self.git(self.hedef, "stash", "list").stdout.strip(), "")

    def test_ayrismis_klon_guncellenmez(self):
        self.kurulu()
        self.uzakta_commit("UZAK.txt")
        self.yaz(self.hedef / "YEREL.txt", "yerel commit\n")
        self.git(self.hedef, "add", "YEREL.txt")
        self.git(self.hedef, "commit", "-q", "-m", "yerel")
        head = self.git(self.hedef, "rev-parse", "HEAD").stdout.strip()
        r = self.kur("-Evet")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("ayrışmış", self.cikti(r))
        self.assertEqual(self.git(self.hedef, "rev-parse", "HEAD").stdout.strip(), head)

    def test_hedef_var_git_degil_durur(self):
        self.hedef.mkdir()
        benim = self.yaz(self.hedef / "benim.txt", "kullanıcı dosyası\n")
        r = self.kur("-Evet")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("git klonunun kökü değil", self.cikti(r))
        self.assertEqual(benim.read_text(encoding="utf-8"), "kullanıcı dosyası\n")
        self.assertEqual(sorted(p.name for p in self.hedef.iterdir()), ["benim.txt"])
        self.assertFalse(self.cfg.exists())

    # --- madde 3: yabancı git reposu (kontrol grubu: yukarıdaki template klonu testleri aynı yoldan geçer) ---------
    def test_hedef_yabanci_git_reposu_pull_ve_betik_calismaz(self):
        bare, isaret = self.yabanci_repo("yabanci")
        self.git(self.tmp, "clone", "-q", str(bare), str(self.hedef))
        self.uzakta_commit("YABANCI_YENI.txt", kaynak=bare)  # pull yapılsaydı bu dosya gelirdi
        head = self.git(self.hedef, "rev-parse", "HEAD").stdout.strip()
        r = self.kur("-Evet")
        c = self.cikti(r)
        self.assertEqual(r.returncode, 1, c)
        self.assertIn("template'inin klonu değil", c)
        self.assertIn("CORE-ID: AXET-CORE-", c)
        self.assertEqual(self.git(self.hedef, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertFalse((self.hedef / ".git" / "FETCH_HEAD").exists(), "yabancı repoda fetch yapıldı")
        self.assertFalse((self.hedef / "YABANCI_YENI.txt").exists())
        self.assertFalse(isaret.exists(), "yabancı install.py/doctor.py çalıştırıldı")
        self.assertFalse(self.cfg.exists())

    def test_kaynak_yabanci_repo_ise_klon_sonrasi_betik_calismaz(self):
        bare, isaret = self.yabanci_repo("yabanci-kaynak")
        r = self.kur("-Kaynak", str(bare), "-Hedef", str(self.hedef), "-Evet", varsayilan=False)
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("klonlanan kaynak bu aXet template'i değil", self.cikti(r))
        self.assertFalse(isaret.exists(), "yabancı install.py/doctor.py çalıştırıldı")
        self.assertFalse(self.cfg.exists())

    def test_kaldir_yabanci_klasorde_betik_calistirmaz(self):
        bare, isaret = self.yabanci_repo("yabanci-kaldir")
        self.git(self.tmp, "clone", "-q", str(bare), str(self.hedef))
        r = self.kur("-Kaldir")
        self.assertEqual(r.returncode, 1, self.cikti(r))
        self.assertIn("template'inin klonu değil", self.cikti(r))
        self.assertFalse(isaret.exists(), "yabancı install.py çalıştırıldı")

    # --- deneme modu ------------------------------------------------------------------------------------------
    def test_deneme_modu_hicbir_sey_yazmaz(self):
        r = self.kur("-DenemeModu")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("DENEME MODU bitti", self.cikti(r))
        self.assertFalse(self.hedef.exists())
        self.assertEqual(list(self.xdg.iterdir()), [])

    def test_deneme_modu_kurulu_klonda_fetch_ve_config_yazmaz(self):
        self.kurulu()
        self.uzakta_commit()
        once_cfg = self.cfg.read_bytes()
        once_git = _goruntu(self.hedef / ".git")
        r = self.kur("-DenemeModu")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("dry-run", self.cikti(r))
        self.assertEqual(self.cfg.read_bytes(), once_cfg)
        self.assertEqual(_goruntu(self.hedef / ".git"), once_git)
        self.assertEqual(sorted(p.name for p in self.cfg.parent.iterdir()), ["axet-code.json"])  # yedek de yok

    # --- madde 4: sonu ters bölü ile biten tırnaklı -Hedef ------------------------------------------------------
    def test_tirnakli_ters_bolu_ile_biten_hedef_durur(self):
        bin_, kayit = self.sahte_winget()
        env = self.path_degistir(self.env, str(bin_) + os.pathsep + self.path_oku(self.env))  # sahte winget önde

        def sarmala(hedef_metni: str) -> subprocess.CompletedProcess:
            # Python'un argüman kaçışını atlamak için komut satırı .cmd içine kullanıcının yazdığı gibi konur.
            # -Kaynak önde: kusur geri gelse bile yerel bare'den klonlanır, ağa çıkılmaz.
            w = self.tmp / "sarmal.cmd"
            w.write_bytes((f'@echo off\r\ncall "{KUR_CMD}" -Kaynak "{self.kaynak}" -Hedef "{hedef_metni}" '
                           f'-DenemeModu -WingetKapali\r\nexit /b %ERRORLEVEL%\r\n').encode("ascii"))
            return subprocess.run([COMSPEC, "/c", str(w)], env=env, cwd=str(self.tmp), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=600)

        bozuk = self.tmp / "c b"
        r = sarmala(str(bozuk) + "\\")
        c = self.cikti(r)
        self.assertEqual(r.returncode, 1, c)
        self.assertIn("ters bölü ile BİTİRME", c)
        self.assertNotIn("Klonlanıyor", c)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir() if p.name.startswith("c b")), [])
        self.assertFalse(kayit.exists(), "winget çağrıldı")
        self.assertEqual(list(self.xdg.iterdir()), [])
        # kontrol grubu: aynı yol ters bölüsüz -> parametreler yerinde, deneme modu tamamlanır, hiçbir şey oluşmaz
        r = sarmala(str(bozuk))
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("DENEME MODU bitti", self.cikti(r))
        self.assertFalse(bozuk.exists())
        self.assertFalse(kayit.exists(), "winget çağrıldı")

    # --- kaldırma ---------------------------------------------------------------------------------------------
    def test_kaldir_config_temizler_klon_kalir(self):
        self.kurulu()
        r = self.kur("-Kaldir")
        self.assertEqual(r.returncode, 0, self.cikti(r))
        metin = json.dumps(self.cfg_oku())
        self.assertNotIn(self.hedef.as_posix(), metin)
        self.assertNotIn(self.hedef.as_posix().lower(), metin.lower())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())
        self.assertIn("SİLİNMEDİ", self.cikti(r))
        self.assertIn("SAP'ye yazma iznini de kapatır", self.cikti(r))

    def test_onceki_baska_klon_uyarilir_ve_iki_cekirdek_kalir(self):
        # Config önce BAŞKA bir klonu (burada AXET_HOME) gösteriyor.
        self.global_config(sap=True)
        r = self.kur("-Evet")
        c = self.cikti(r)
        # Ölçüldü (HEAD f179e14): doctor.py iki template kopyasının aynı skill adlarını FAIL sayar -> kurulum yazılır
        # ama doğrulama geçmez, kur.ps1 çıkış 4 verir. İki çekirdek durumunun kullanıcıya görünür olduğu yer burası.
        self.assertEqual(r.returncode, 4, c)
        self.assertIn("doctor.py doğrulaması geçmedi", c)
        self.assertNotIn("Kurulum tamam", c)
        ctx = self.cfg_oku()["options"]["context_paths"]
        # Ölçüm: install.py yalnız kendi klonunun kayıtlarını yönetir -> iki çekirdek birlikte kalır.
        self.assertIn((AXET_HOME / "core" / "00-temel.md").as_posix(), ctx)
        self.assertIn((self.hedef / "core" / "00-temel.md").as_posix(), ctx)
        # kur.ps1 bunu açıkça yazar, SAP yazma izninin de kapanacağını söyler, komutu bulunan Python'un tam yoluyla
        # verir ve kendisi ÇALIŞTIRMAZ (AXET_HOME kayıtları config'te duruyor).
        self.assertIn("önceki kurulum şu klonu gösteriyordu", c)
        self.assertIn(str(AXET_HOME), c)
        self.assertIn("SAP'ye yazma iznini de KAPATIR", c)
        desen = r'& "([^"]+)" "' + re.escape(str(AXET_HOME / "scripts" / "install.py")) + r'" --uninstall'
        komut = re.search(desen, c)
        self.assertIsNotNone(komut, c)
        self.assertTrue(Path(komut.group(1)).is_file(), komut.group(1))
        # Y1a: doctor'ın FAIL satırlarından SONRA, son mesajda doğru çözüm yeniden basılır
        son = c[c.index("doctor.py doğrulaması geçmedi"):]
        self.assertIn("önerisini UYGULAMA", son)
        self.assertRegex(son, desen)
        self.assertIn("kur.cmd", son[son.index("önerisini UYGULAMA"):])

    # --- madde 1-2: ASCII olmayan Python yolu + ASCII olmayan hedef, UTF-8 ortam değişkenleri YOK ------------------
    def test_ascii_olmayan_python_ve_hedef_utf8_ayarsiz_ortamda(self):
        venv = self.tmp / "Ğüşı Özgür" / "venv"
        r = subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        venv_py = venv / "Scripts" / "python.exe"
        env = {k: v for k, v in self.env.items() if k.upper() not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        env = self.path_degistir(env, str(venv_py.parent) + os.pathsep + self.path_oku(env))
        # kontrol: bu ortamda venv Python'u borudan UTF-8 yazmıyor (yoksa test ASCII dışı yolu sınamaz)
        k = subprocess.run([str(venv_py), "-c", "import sys;print(sys.stdout.encoding)"], env=env, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertNotIn("utf", k.stdout.lower(), "ortam zaten UTF-8; test ASCII dışı yolu sınamıyor")

        hedef = self.tmp / "hedef Özgür ğşı"
        r = self.kur("-Evet", env=env, hedef=hedef)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn(f"OK Python: ", c)
        self.assertIn(str(venv_py), c)  # yol bozulmadan okundu ve o yorumlayıcı seçildi
        self.assertTrue(self.cfg.is_file(), "config yazılmadı:\n" + c)
        ctx = self.cfg_oku()["options"]["context_paths"]
        self.assertIn((hedef / "core" / "00-temel.md").as_posix(), ctx)
        self.assertIn("SONUÇ: 0 FAIL", c)
        self.assertIn("Kurulum tamam (yeni klon)", c)
        self.assertNotIn("beklenmeyen hata", c)

        r = self.kur("-Evet", env=env, hedef=hedef)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn("Config zaten bu klonu gösteriyor", c)
        self.assertNotIn("önceki kurulum şu klonu gösteriyordu", c)

    # --- gate 2 / Y2: dubious ownership ----------------------------------------------------------------------
    def test_dubious_ownership_git_hatasi_ve_tarif_basilir_calistirilmaz(self):
        self.kurulu()  # kontrol grubu: aynı klon, ek ortam değişkeni yokken kurulum geçti
        head = self.git(self.hedef, "rev-parse", "HEAD").stdout.strip()
        gitconfig = Path(self.env["GIT_CONFIG_GLOBAL"])
        once = gitconfig.read_bytes()
        env = dict(self.env)
        # Ölçüldü (Git 2.55): git'in test değişkeni gerçek "detected dubious ownership" hatasını üretir; global config'e
        # ya da dosya sahipliğine dokunmadan UNC/başka sahipli klasör durumunu taklit eder.
        env["GIT_TEST_ASSUME_DIFFERENT_OWNER"] = "1"
        r = self.kur("-Evet", env=env)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 1, c)
        self.assertIn("dubious ownership", c)
        self.assertIn("git config --global --add safe.directory", c)
        self.assertNotIn("git klonunun kökü değil", c)
        self.assertEqual(gitconfig.read_bytes(), once, "global git config'e yazıldı")
        self.assertEqual(self.git(self.hedef, "rev-parse", "HEAD").stdout.strip(), head)

    # --- geçersiz karakterli XDG_CONFIG_HOME: git var ama `git --version` hata veriyor -------------------------
    def test_gecersiz_xdg_git_bulundu_calismadi(self):
        # Ölçüldü (Git 2.55.0.windows.5, GIT_CONFIG_GLOBAL tanımsız): XDG_CONFIG_HOME içinde < ya da | varsa
        # `git --version` rc 128 + "fatal: unable to access '<xdg>/git/config': Invalid argument". GIT_CONFIG_GLOBAL
        # tanımlıyken git bu yolu okumaz ve kusur görünmez -> iki değişken de kaldırılır. Gerçek ~/.gitconfig okunmasın
        # diye HOME geçici klasör. -DenemeModu: yalnız okuma.
        temel = {k: v for k, v in self.env.items() if k.upper() not in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "HOME")}
        temel["HOME"] = str(self.tmp / "_home")
        (self.tmp / "_home").mkdir()
        # Git sürümüne bağlı: bu git `--version` sırasında XDG config yolunu okumuyorsa senaryo üretilemez -> atla.
        dene = subprocess.run(["git", "--version"], env=dict(temel, XDG_CONFIG_HOME=str(self.tmp / "a<b")),
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        if dene.returncode == 0:
            self.skipTest(f"bu git ({dene.stdout.strip()}) --version sırasında XDG yolunu okumuyor; senaryo üretilemez")
        # kontrol grubu: aynı ortam, geçerli XDG -> Git bulunur, deneme modu tamamlanır
        r = self.kur("-DenemeModu", env=temel)
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("OK Git: git version", self.cikti(r))
        for karakter in ("<", "|"):
            with self.subTest(karakter=karakter):
                env = dict(temel)
                env["XDG_CONFIG_HOME"] = str(self.tmp / f"a{karakter}b")
                r = self.kur("-DenemeModu", env=env)
                c = self.cikti(r)
                self.assertEqual(r.returncode, 2, c)
                self.assertIn("Git bulundu ama çalışmadı", c)
                self.assertIn("unable to access", c)  # git'in kendi mesajı basıldı
                self.assertNotIn("EKSİK: Git bulunamadı", c)
                self.assertNotIn("winget install --id Git.Git", c)  # git zaten kurulu: kurulum önerilmez
                self.assertNotIn("OK Git", c)
                self.assertFalse(self.hedef.exists())

    # --- K1: config'teki başka klon diskte yok (silinmiş/taşınmış) ------------------------------------------------
    def test_configteki_baska_klon_silinmisse_bayat_kayit_denir(self):
        # Kontrol grubu: test_onceki_baska_klon_uyarilir_ve_iki_cekirdek_kalir (klon VAR -> --uninstall önerisi, çıkış 4).
        silinmis = self.tmp / "silinmis-klon"
        bayat_core = (silinmis / "core" / "00-temel.md").as_posix()
        bayat_skills = (silinmis / "skills").as_posix()
        bayat_desen = (silinmis / "core").as_posix() + "/*"
        self.yaz(self.cfg, json.dumps({"options": {"context_paths": [bayat_core], "skills_paths": [bayat_skills]},
                                       "permissions": {"rules": {"edit": {bayat_desen: "deny"}}}}, indent=2))
        r = self.kur("-Evet")
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn("SONUÇ: 0 FAIL", c)
        self.assertIn("kayıtlı klon klasörü yok; kayıt bayat", c)
        self.assertNotIn(str(silinmis / "scripts" / "install.py"), c)  # olmayan betik önerilmez
        self.assertNotIn("doctor'ın FAIL satırları", c)  # doctor 0 FAIL
        son = c[c.index("Kurulum tamam"):]
        self.assertIn(str(self.cfg), son)  # elle temizlenecek dosya
        for giris in (bayat_core, bayat_skills, bayat_desen):
            self.assertIn(giris, son)
        # config'e bayat girişler için otomatik yazma yok: install.py yalnız kendi klonunu ekledi
        cfg = self.cfg_oku()
        self.assertIn(bayat_core, cfg["options"]["context_paths"])
        self.assertIn(bayat_skills, cfg["options"]["skills_paths"])
        self.assertIn(bayat_desen, cfg["permissions"]["rules"]["edit"])
        self.assertIn((self.hedef / "core" / "00-temel.md").as_posix(), cfg["options"]["context_paths"])

    # --- K2: junction ile verilen hedef -------------------------------------------------------------------------
    def test_junction_hedef_klon_koku_sayilir(self):
        # Ölçüldü (Git 2.55): junction'lı yolda `rev-parse --show-toplevel` çözümlenmiş (asıl) yolu döndürür.
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(self.hedef))
        bag, alt_bag = self.tmp / "hedef-bag", self.tmp / "alt-bag"
        try:
            for b, hedef in ((bag, self.hedef), (alt_bag, self.hedef / "scripts")):
                k = subprocess.run([COMSPEC, "/c", "mklink", "/J", str(b), str(hedef)], capture_output=True, text=True,
                                   stdin=subprocess.DEVNULL, timeout=60)
                self.assertEqual(k.returncode, 0, k.stdout + k.stderr)
            # kontrol grubu: aynı repo junction'sız -> deneme modu güncellemeyi gösterir
            r = self.kur("-DenemeModu")
            self.assertEqual(r.returncode, 0, self.cikti(r))
            self.assertIn("[deneme] güncellenecekti", self.cikti(r))
            r = self.kur("-DenemeModu", hedef=bag)
            c = self.cikti(r)
            self.assertEqual(r.returncode, 0, c)
            self.assertIn("[deneme] güncellenecekti", c)
            self.assertNotIn("okuyamadı", c)
            # kontrol grubu: repo içindeki alt klasörü gösteren junction kök SAYILMAZ
            r = self.kur("-DenemeModu", hedef=alt_bag)
            c = self.cikti(r)
            self.assertEqual(r.returncode, 1, c)
            self.assertIn("git klonunun kökü değil", c)
            self.assertNotIn("okuyamadı", c)
        finally:
            for b in (bag, alt_bag):  # junction yalnız bağ olarak kaldırılır (hedef silinmez)
                subprocess.run([COMSPEC, "/c", "rmdir", str(b)], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertFalse(bag.exists())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())

    # --- gate 3 / HIGH: junction'lı hedefle iki GERÇEK kurulum ---------------------------------------------------
    def test_junction_hedef_ikinci_kurulum_aktif_klonu_kaldirmayi_onermez(self):
        # Ölçüldü: install.py klon kökünü Path(__file__).resolve() ile (junction ÇÖZÜLMÜŞ) yazar; kur.ps1 karşılaştırması
        # çözülmemiş yolla yapılınca 2. koşumda AKTİF klon için --uninstall önerisi çıktı.
        env = dict(self.env)
        env["HOME"] = str(self.tmp / "_home")
        (self.tmp / "_home").mkdir()
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(self.hedef))
        bag = self.tmp / "hedef-bag"
        try:
            k = subprocess.run([COMSPEC, "/c", "mklink", "/J", str(bag), str(self.hedef)], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            self.assertEqual(k.returncode, 0, k.stdout + k.stderr)
            kontrol_env = dict(env, XDG_CONFIG_HOME=str(self.tmp / "_xdg_kontrol"))
            # kontrol grubu önce: aynı klon, gerçek yol, ayrı config
            for etiket, hedef, e in (("kontrol: gerçek yol", self.hedef, kontrol_env), ("junction", bag, env)):
                with self.subTest(etiket):
                    r1 = self.kur("-Evet", env=e, hedef=hedef)
                    self.assertEqual(r1.returncode, 0, self.cikti(r1))
                    r2 = self.kur("-Evet", env=e, hedef=hedef)
                    c = self.cikti(r2)
                    self.assertEqual(r2.returncode, 0, c)
                    self.assertIn("Config zaten bu klonu gösteriyor", c)
                    self.assertNotIn("önceki kurulum şu klonu gösteriyordu", c)
                    self.assertNotIn("--uninstall", c)
                    self.assertNotIn("ÖNCE BUNU YAP", c)
        finally:
            subprocess.run([COMSPEC, "/c", "rmdir", str(bag)], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertFalse(bag.exists())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())

    # --- gate 3 / HIGH koşulu: yol çözülemezse karşılaştırma ÖLÇÜLEMEDİ, --uninstall önerisi YOK ---------------
    def test_gercek_yol_olculemezse_uninstall_onerilmez(self):
        # Gercek-Yol başarısızsa çözülmemiş yola düşülmez; düşülseydi junction'lı hedefte AKTİF klon "başka klon" sanılıp
        # --uninstall önerilirdi. Python YALNIZ o çağrı için bozulur: PYTHONPATH'teki sitecustomize, AXET_TEST_RESOLVE_BOZUK
        # yolunun resolve()'una hata verdirir (install.py kendi __file__'ını çözer, etkilenmez). -DenemeModu: yazma yok.
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(self.hedef))
        self.yaz(self.cfg, json.dumps({"options": {"context_paths": [(self.hedef / "core" / "00-temel.md").as_posix()]}}))
        site = self.yaz(self.tmp / "_site" / "sitecustomize.py", "\n".join([
            "import os, pathlib",
            "_hedef = os.environ.get('AXET_TEST_RESOLVE_BOZUK')",
            "if _hedef:",
            "    _asil = pathlib.Path.resolve",
            "    def _bozuk(self, strict=False):",
            "        if os.path.normcase(os.path.abspath(str(self))) == os.path.normcase(os.path.abspath(_hedef)):",
            "            raise OSError('test: resolve bozuk')",
            "        return _asil(self, strict)",
            "    pathlib.Path.resolve = _bozuk", ""]))
        bag = self.tmp / "hedef-bag"
        try:
            k = subprocess.run([COMSPEC, "/c", "mklink", "/J", str(bag), str(self.hedef)], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            self.assertEqual(k.returncode, 0, k.stdout + k.stderr)
            bozuk_env = dict(self.env, PYTHONPATH=str(site.parent), AXET_TEST_RESOLVE_BOZUK=str(bag))
            # bozma düzeneğinin kendisi ölçülür: yalnız hedef yolun resolve()'u düşer
            kod = "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())"
            dus = subprocess.run([sys.executable, "-c", kod, str(bag)], env=bozuk_env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(dus.returncode, 0, dus.stdout)
            gec = subprocess.run([sys.executable, "-c", kod, str(bag / "scripts" / "install.py")], env=bozuk_env,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(gec.returncode, 0, gec.stderr)
            # kontrol grubu: Python sağlamken junction çözülür -> aynı klon
            r = self.kur("-DenemeModu", hedef=bag)
            c = self.cikti(r)
            self.assertEqual(r.returncode, 0, c)
            self.assertIn("Config zaten bu klonu gösteriyor", c)
            self.assertNotIn("--uninstall", c)
            # bozuk: karşılaştırma ölçülemez -> uyarı, kaldırma önerisi yok
            r = self.kur("-DenemeModu", env=bozuk_env, hedef=bag)
            c = self.cikti(r)
            self.assertEqual(r.returncode, 0, c)
            self.assertIn("klon karşılaştırması ÖLÇÜLEMEDİ", c)
            self.assertNotIn("--uninstall", c)
            self.assertNotIn("önceki kurulum şu klonu gösteriyordu", c)
            self.assertNotIn("Config zaten bu klonu gösteriyor", c)
        finally:
            subprocess.run([COMSPEC, "/c", "rmdir", str(bag)], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertFalse(bag.exists())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())

    # --- re-gate / LOW 1: config junction'lı biçimi tutuyor, kur gerçek yolla çalışıyor ---------------------------
    def test_config_junction_bicimi_gercek_hedef_aktif_klonu_kaldirmayi_onermez(self):
        # Ölçüldü (re-gate senaryo G): config'teki kök çözülmeden karşılaştırılınca AKTİF klon "önceki kurulum şu klonu
        # gösteriyordu" + --uninstall önerisi aldı. Config'teki kök çözülemezse ÖLÇÜLEMEDİ: öneri yok. -DenemeModu: yazma yok.
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(self.hedef))
        diger = self.tmp / "diger-klon"
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(diger))
        site = self.yaz(self.tmp / "_site" / "sitecustomize.py", "\n".join([
            "import os, pathlib",
            "_hedef = os.environ.get('AXET_TEST_RESOLVE_BOZUK')",
            "if _hedef:",
            "    _asil = pathlib.Path.resolve",
            "    def _bozuk(self, strict=False):",
            "        if os.path.normcase(os.path.abspath(str(self))) == os.path.normcase(os.path.abspath(_hedef)):",
            "            raise OSError('test: resolve bozuk')",
            "        return _asil(self, strict)",
            "    pathlib.Path.resolve = _bozuk", ""]))
        bag = self.tmp / "hedef-bag"
        cekirdek = lambda kok: (kok / "core" / "00-temel.md").as_posix()  # noqa: E731
        try:
            k = subprocess.run([COMSPEC, "/c", "mklink", "/J", str(bag), str(self.hedef)], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            self.assertEqual(k.returncode, 0, k.stdout + k.stderr)
            bozuk_env = dict(self.env, PYTHONPATH=str(site.parent), AXET_TEST_RESOLVE_BOZUK=str(bag))
            vakalar = [  # (ad, config'teki kök, env, beklenen, beklenmeyen)
                ("kontrol: config gerçek yol", self.hedef, self.env, ["Config zaten bu klonu gösteriyor"],
                 ["--uninstall", "önceki kurulum şu klonu gösteriyordu", "ÖLÇÜLEMEDİ"]),
                ("kontrol: gerçekten başka klon önerilir", diger, self.env,
                 ["önceki kurulum şu klonu gösteriyordu", str(diger / "scripts" / "install.py") + '" --uninstall'],
                 ["Config zaten bu klonu gösteriyor"]),
                ("config junction biçimi", bag, self.env, ["Config zaten bu klonu gösteriyor"],
                 ["--uninstall", "önceki kurulum şu klonu gösteriyordu", "kayıt bayat", "ÖLÇÜLEMEDİ"]),
                ("config kökü çözülemez", bag, bozuk_env,
                 ["config'teki klonla karşılaştırma ÖLÇÜLEMEDİ", f"config'te kayıtlı klon: {bag}"],
                 ["--uninstall", "önceki kurulum şu klonu gösteriyordu", "kayıt bayat", "Config zaten bu klonu gösteriyor"]),
            ]
            for ad, kok, env, beklenen, beklenmeyen in vakalar:
                with self.subTest(ad):
                    self.yaz(self.cfg, json.dumps({"options": {"context_paths": [cekirdek(kok)]}}))
                    r = self.kur("-DenemeModu", env=env, hedef=self.hedef)
                    c = self.cikti(r)
                    self.assertEqual(r.returncode, 0, c)
                    for s in beklenen:
                        self.assertIn(s, c)
                    for s in beklenmeyen:
                        self.assertNotIn(s, c)
        finally:
            subprocess.run([COMSPEC, "/c", "rmdir", str(bag)], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertFalse(bag.exists())
        self.assertTrue((self.hedef / "scripts" / "install.py").is_file())

    # --- re-gate / LOW 2: config'te ~ ile yazılmış bayat klon ------------------------------------------------------
    def test_tilde_bayat_kayit_acilmis_yolla_listelenir(self):
        # Ölçüldü (re-gate senaryo H1): Config-Klonlari ~ açmadan GetFullPath yapınca "<cwd>\~\eski-axet" çıktı ve
        # Config-Girisleri (~ açar) eşleşmeyince "giriş kalmamış" dendi; config'te 3 giriş duruyordu.
        ev = self.tmp / "_home"
        ev.mkdir()
        env = dict(self.env, USERPROFILE=str(ev), HOME=str(ev))  # Python expanduser Windows'ta USERPROFILE okur
        girisler = ["~/eski-axet/core/00-temel.md", "~/eski-axet/skills", "~/eski-axet/core/*"]
        self.yaz(self.cfg, json.dumps({"options": {"context_paths": [girisler[0]], "skills_paths": [girisler[1]]},
                                       "permissions": {"rules": {"edit": {girisler[2]: "deny"}}}}))
        r = self.kur("-Evet", env=env)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn(f"kayıt bayat: {ev / 'eski-axet'}", c)
        self.assertNotIn(str(self.tmp / "~"), c)
        self.assertNotIn("giriş kalmamış", c)
        son = c[c.index("BAYAT KAYIT"):]
        for g in girisler:
            self.assertIn(g, son)
        self.assertNotIn(str(ev / "eski-axet" / "scripts" / "install.py"), c)  # olmayan betik önerilmez

    # --- re-gate / ÖNERİ 3: Gercek-Yol stdout'taki başka satırı yol sanmaz (fonksiyon AST'den, betik çalışmaz) --------
    def test_gercek_yol_stdout_banner_yol_sanilmaz(self):
        self.git(self.tmp, "clone", "-q", str(self.kaynak), str(self.hedef))
        site = self.yaz(self.tmp / "_site" / "sitecustomize.py", "\n".join([
            "import atexit, os",
            "_m = os.environ.get('AXET_TEST_BANNER')",
            "if _m == 'duz':",
            "    atexit.register(print, 'AXET-BANNER merhaba')",
            "elif _m == 'isaretli':",
            "    atexit.register(print, 'AXETYOL:C:\\\\sahte-banner')", ""]))
        surucu = self.yaz(self.tmp / "surucu_gy.ps1", "\r\n".join([
            "param([string]$Kur, [string]$Yol, [string]$Py)",
            "$ErrorActionPreference = 'Continue'",
            "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false",
            "$env:PYTHONUTF8 = '1'",
            "$ast = [System.Management.Automation.Language.Parser]::ParseFile($Kur, [ref]$null, [ref]$null)",
            "$fonk = $ast.FindAll({ param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true) |",
            "    Where-Object { $_.Name -in @('Son-Kod', 'Gercek-Yol') }",
            "foreach ($f in $fonk) { . ([scriptblock]::Create($f.Extent.Text)) }",
            "$script:PY = $Py",
            "foreach ($m in @('yok', 'duz', 'isaretli')) {",
            "    $env:AXET_TEST_BANNER = $m",
            "    $s = Gercek-Yol $Yol",
            "    [Console]::Out.WriteLine(\"$m|SONUC|$s\")",
            "    [Console]::Out.WriteLine(\"$m|NULL|$($null -eq $s)\")",
            "    [Console]::Out.WriteLine(\"$m|HATA|$($script:GercekYolHata)\")",
            "}", ""]), newline="")
        bag = self.tmp / "hedef-bag"
        try:
            k = subprocess.run([COMSPEC, "/c", "mklink", "/J", str(bag), str(self.hedef)], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            self.assertEqual(k.returncode, 0, k.stdout + k.stderr)
            env = dict(self.env, PYTHONPATH=str(site.parent))
            r = subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(surucu),
                                "-Kur", str(KUR_PS1), "-Yol", str(bag), "-Py", sys.executable],
                               env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               stdin=subprocess.DEVNULL, timeout=120)
        finally:
            subprocess.run([COMSPEC, "/c", "rmdir", str(bag)], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertFalse(bag.exists())
        c = self.cikti(r)
        cikan = {}
        for satir in r.stdout.splitlines():
            parca = satir.split("|", 2)
            if len(parca) == 3:
                cikan[(parca[0], parca[1])] = parca[2]
        asil = os.path.normcase(str(self.hedef.resolve()))
        with self.subTest("kontrol: banner yok -> junction çözülür"):
            self.assertEqual(os.path.normcase(cikan.get(("yok", "SONUC"), "")), asil, c)
        with self.subTest("stdout banner yol sanılmaz"):
            self.assertNotIn("BANNER", cikan.get(("duz", "SONUC"), "?"), c)
            self.assertEqual(os.path.normcase(cikan.get(("duz", "SONUC"), "")), asil, c)
        with self.subTest("önekli ikinci satır: belirsiz -> ÖLÇÜLEMEDİ"):
            self.assertNotIn("sahte-banner", cikan.get(("isaretli", "SONUC"), "?"), c)
            self.assertEqual(cikan.get(("isaretli", "NULL")), "True", c)
            self.assertTrue(cikan.get(("isaretli", "HATA")), c)

    # --- gate 3 / LOW: git var ama çalışmıyor, XDG ile ilgisiz -----------------------------------------------
    def test_git_calismiyor_xdg_ilgisizse_xdg_notu_basilmaz(self):
        bin_ = self.tmp / "_sahte_git"
        bin_.mkdir()
        shutil.copy(SYS32 / "where.exe", bin_ / "git.exe")  # `git --version` rc 1 veren, git olmayan bir exe
        env = self.path_degistir(self.env, os.pathsep.join([str(bin_), str(Path(sys.executable).parent), str(SYS32),
                                                            str(POWERSHELL.parent)]))
        self.assertTrue(env.get("XDG_CONFIG_HOME"))  # XDG tanımlı ve geçerli: XDG notu yine de basılmamalı
        r = self.kur("-DenemeModu", env=env)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 2, c)
        self.assertIn("git çalıştırılamadı", c)
        self.assertIn(str(bin_ / "git.exe"), c)
        self.assertIn("çıkış kodu 1", c)
        self.assertNotIn("XDG_CONFIG_HOME", c)
        self.assertNotIn("yeniden kurmak", c)
        self.assertNotIn("EKSİK: Git bulunamadı", c)
        self.assertFalse(self.hedef.exists())

    # --- gate 3 / LOW: Config-Girisleri tablosu (fonksiyon AST'den çıkarılır, betik çalışmaz) --------------------
    def test_config_girisleri_tablosu(self):
        up = self.tmp / "_userprofile"
        up.mkdir()
        tablo = [  # (ad, bayat kök, aktif klon, config, beklenen girişler)
            ("ata kök aktif klonu listelemez", r"C:\Users\u", r"C:\Users\u\axet",
             {"options": {"context_paths": ["C:/Users/u/core/00-temel.md", "C:/Users/u/axet/core/00-temel.md"]}},
             ["options.context_paths: C:/Users/u/core/00-temel.md"]),
            ("sürücü kökü aktif klonu listelemez", "C:\\", r"C:\axet",
             {"options": {"context_paths": ["C:/core/00-temel.md", "C:/axet/core/00-temel.md"], "skills_paths": ["C:/axet/skills"]},
              "permissions": {"rules": {"edit": {"C:/core/*": "deny", "C:/axet/core/*": "deny"}}}},
             ["options.context_paths: C:/core/00-temel.md", "permissions.rules.edit: C:/core/*"]),
            ("nokta-nokta normalize", r"C:\old", r"C:\yeni",
             {"options": {"context_paths": ["C:/x/../old/core/00-temel.md"]}},
             ["options.context_paths: C:/x/../old/core/00-temel.md"]),
            ("tilde açılır", str(up / "old"), r"C:\yeni",
             {"options": {"context_paths": ["~/old/core/00-temel.md"]}},
             ["options.context_paths: ~/old/core/00-temel.md"]),
            ("bozuk tipler okunamadı demez", r"C:\old", r"C:\yeni", {"options": ["x"], "permissions": {"rules": None}}, []),
            # kontrol grubu: önceki kodda da doğru olanlar
            ("önek axet/axet2 karışmaz", r"C:\axet", r"C:\yeni",
             {"options": {"context_paths": ["C:/axet2/core/00-temel.md", "C:/axet/core/00-temel.md"]}},
             ["options.context_paths: C:/axet/core/00-temel.md"]),
            ("harf + ters bölü + sondaki ayraç", "C:\\axet\\", r"C:\yeni",
             {"options": {"skills_paths": ["c:\\AXET\\skills\\"]}, "permissions": {"rules": {"edit": {"C:/Axet/core/*": "deny"}}}},
             ["options.skills_paths: c:\\AXET\\skills\\", "permissions.rules.edit: C:/Axet/core/*"]),
            ("ASCII dışı", r"C:\Users\Özgür\İş", r"C:\yeni",
             {"options": {"context_paths": ["C:/Users/Özgür/İş/core/00-temel.md"]}},
             ["options.context_paths: C:/Users/Özgür/İş/core/00-temel.md"]),
        ]
        vakalar = []
        for i, (ad, kok, aktif, cfg, _) in enumerate(tablo):
            xdg = self.tmp / f"_xdg_tablo{i}"
            self.yaz(xdg / "axet-code" / "axet-code.json", json.dumps(cfg, ensure_ascii=False))
            vakalar.append({"ad": ad, "kok": kok, "aktif": aktif, "xdg": str(xdg)})
        vaka_dosyasi = self.yaz(self.tmp / "vakalar.json", json.dumps(vakalar, ensure_ascii=False))
        surucu = self.yaz(self.tmp / "surucu.ps1", "\r\n".join([
            "param([string]$Kur, [string]$Vakalar, [string]$Py)",
            "$ErrorActionPreference = 'Continue'",
            "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false",
            "$env:PYTHONUTF8 = '1'",
            "$ast = [System.Management.Automation.Language.Parser]::ParseFile($Kur, [ref]$null, [ref]$null)",
            "$fonk = $ast.FindAll({ param($a) $a -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true) |",
            "    Where-Object { $_.Name -in @('Son-Kod', 'Config-Yolu', 'Config-Girisleri') }",
            "foreach ($f in $fonk) { . ([scriptblock]::Create($f.Extent.Text)) }",
            "$script:PY = $Py",
            # Ölçüldü (PS 5.1): ConvertFrom-Json JSON dizisini boruda TEK nesne olarak akıtır; önce değişkene atanır.
            "$liste = Get-Content -LiteralPath $Vakalar -Raw -Encoding UTF8 | ConvertFrom-Json",
            "foreach ($v in $liste) {",
            "    $env:XDG_CONFIG_HOME = $v.xdg",
            "    foreach ($s in @(Config-Girisleri $v.kok $v.aktif)) { [Console]::Out.WriteLine(\"$($v.ad)|$s\") }",
            "    [Console]::Out.WriteLine(\"$($v.ad)|<son>\")",
            "}", ""]), newline="")
        env = dict(self.env, USERPROFILE=str(up))
        r = subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(surucu),
                            "-Kur", str(KUR_PS1), "-Vakalar", str(vaka_dosyasi), "-Py", sys.executable],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, timeout=120)
        c = self.cikti(r)
        cikan: dict = {}
        for satir in r.stdout.splitlines():
            if "|" in satir:
                ad, deger = satir.split("|", 1)
                cikan.setdefault(ad, []).append(deger)
        for ad, _, _, _, beklenen in tablo:
            with self.subTest(ad):
                self.assertIn("<son>", cikan.get(ad, []), c)
                self.assertEqual(sorted(x for x in cikan[ad] if x != "<son>"), sorted(beklenen), c)

    # --- gate 2 / Y3: WindowsApps Store yönlendirmesi (bu makinedeki gerçek alias'lar) -------------------------
    def test_windowsapps_store_yonlendirmesi_python_secilmez(self):
        wa = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps"
        stub = wa / "python.exe"
        if not stub.exists():
            self.skipTest("WindowsApps python.exe yok")
        k = subprocess.run([str(stub), "-c", "print(1)"], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        if k.returncode == 0:
            self.skipTest("WindowsApps python.exe bu makinede gerçek bir yorumlayıcı (Store yönlendirmesi değil)")
        env = self.path_degistir(self.env, os.pathsep.join([str(wa), str(SYS32), str(POWERSHELL.parent)]))
        r = self.kur(env=env)  # git PATH'te yok -> 2. adımda durur; -WingetKapali
        c = self.cikti(r)
        self.assertEqual(r.returncode, 2, c)
        secilen = re.search(r"OK Python: \S+ \((.+)\)", c)
        if secilen:  # py alias'ı gerçek yorumlayıcıya çıkabilir; seçilen yol stub OLMAMALI ve gerçek dosya olmalı
            yol = Path(secilen.group(1))
            self.assertNotEqual(os.path.normcase(str(yol)), os.path.normcase(str(stub)), c)
            self.assertTrue(yol.is_file() and yol.stat().st_size > 0, c)
        else:
            self.assertIn("EKSİK: Python 3.9 ya da üstü bulunamadı", c)
        self.assertNotIn("Python was not found", c.split("== 2/5")[0])

    # --- gate 2 / Y4: GitHub raw biçimi (BOM + LF) --------------------------------------------------------------
    def test_lf_satir_sonlu_bomlu_kopya_deneme_modu(self):
        kopya = self.tmp / "raw-lf" / "kur.ps1"
        kopya.parent.mkdir()
        ham = KUR_PS1.read_bytes().replace(b"\r\n", b"\n")
        kopya.write_bytes(ham)
        self.assertEqual(kopya.read_bytes()[:3], b"\xef\xbb\xbf")
        self.assertNotIn(b"\r", kopya.read_bytes())
        r = subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(kopya),
                            "-Kaynak", str(self.kaynak), "-Hedef", str(self.hedef), "-DenemeModu", "-WingetKapali"],
                           env=self.env, cwd=str(self.tmp), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, timeout=300)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        self.assertIn("DENEME MODU bitti", c)
        self.assertIn("İsteğe bağlı: rg (ripgrep)", c)
        self.assertIn("Ön koşul: Git ve Python", c)
        for bozuk in ("ParserError", "Ã", "Ä", "\ufffd"):
            self.assertNotIn(bozuk, c)
        self.assertFalse(self.hedef.exists())

    # --- gate 2 / Y5: göreli hedef ve dış catch ---------------------------------------------------------------
    def test_goreli_hedef_calisma_dizinine_gore_cozulur(self):
        r = self.kur("-Kaynak", str(self.kaynak), "-Hedef", "goreli-klon", "-Evet", varsayilan=False)  # cwd = self.tmp
        c = self.cikti(r)
        self.assertEqual(r.returncode, 0, c)
        beklenen = self.tmp / "goreli-klon"
        self.assertIn(f"Klon   : {beklenen}", c)
        self.assertTrue((beklenen / ".git").is_dir(), c)
        self.assertIn((beklenen / "core" / "00-temel.md").as_posix(), self.cfg_oku()["options"]["context_paths"])
        r = self.kur("-Kaynak", str(self.kaynak), "-Hedef", "goreli-klon", "-Evet", varsayilan=False)
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("Config zaten bu klonu gösteriyor", self.cikti(r))

    def test_beklenmeyen_hata_dis_catch_cikis_1(self):
        # Ölçüldü: USERPROFILE ve XDG_CONFIG_HOME yokken Config-Yolu içindeki Join-Path sonlandırıcı hata verir.
        env = {k: v for k, v in self.env.items() if k.upper() not in ("USERPROFILE", "XDG_CONFIG_HOME")}
        r = self.kur("-DenemeModu", env=env)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 1, c)
        self.assertIn("DURDU: beklenmeyen hata", c)
        self.assertIn("kur.ps1:", c)
        self.assertNotIn("DENEME MODU bitti", c)
        self.assertFalse(self.hedef.exists())

    # --- ön koşul eksik ---------------------------------------------------------------------------------------
    def test_axet_yoksa_durur(self):
        env, kayit = self.dar_ortam(axet=False)
        r = self.kur("-Evet", env=env, winget_kapali=False)
        self.assertEqual(r.returncode, 2, self.cikti(r))
        self.assertIn("şirket kanalından kurulur", self.cikti(r))
        self.assertFalse(kayit.exists(), "winget çağrıldı")
        self.assertFalse(self.hedef.exists())

    def test_git_python_yok_soru_kapali_stdin_winget_cagrilmaz(self):
        env, kayit = self.dar_ortam(axet=True)
        r = self.kur(env=env, winget_kapali=False)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 2, c)
        self.assertNotIn("OK Python", c)  # 0 baytlık sahte python.exe/python3.exe aday olarak elendi
        self.assertIn("EKSİK: Git bulunamadı", c)
        self.assertIn("EKSİK: Python 3.9 ya da üstü bulunamadı", c)
        self.assertIn("giriş kapalı -> hayır", c)
        self.assertIn("https://git-scm.com/download/win", c)
        self.assertIn("https://www.python.org/downloads/windows/", c)
        self.assertFalse(kayit.exists(), "winget soru onaylanmadan çağrıldı")
        self.assertFalse(self.hedef.exists())
        self.assertFalse(self.cfg.exists())

    def test_winget_hata_verirse_tarif_basar_durur(self):
        env, kayit = self.dar_ortam(axet=True)
        r = self.kur("-Evet", env=env, winget_kapali=False)
        c = self.cikti(r)
        self.assertEqual(r.returncode, 2, c)
        cagrilar = kayit.read_text(encoding="ascii", errors="replace")
        self.assertIn("Git.Git", cagrilar)
        self.assertIn("Python.Python.3.14", cagrilar)
        self.assertIn("winget Git kurulumunda hata verdi", c)
        self.assertIn("https://www.python.org/downloads/windows/", c)
        self.assertFalse(self.hedef.exists())

    # --- internet işareti (Zone.Identifier) -------------------------------------------------------------------
    def test_internet_isaretli_kopya_kur_cmd_ile_calisir(self):
        kopya = self.tmp / "indirilen"
        kopya.mkdir()
        for f in (KUR_CMD, KUR_PS1):
            shutil.copy2(f, kopya / f.name)
        with open(str(kopya / "kur.ps1") + ":Zone.Identifier", "w", encoding="ascii") as fh:
            fh.write("[ZoneTransfer]\r\nZoneId=3\r\n")
        politika = subprocess.run([str(POWERSHELL), "-NoProfile", "-Command", "Get-ExecutionPolicy"], capture_output=True,
                                  text=True, stdin=subprocess.DEVNULL, timeout=60).stdout.strip()
        arglar = ["-Kaynak", str(self.kaynak), "-Hedef", str(self.hedef), "-DenemeModu", "-WingetKapali"]
        if politika in ("RemoteSigned", "AllSigned"):
            duz = subprocess.run([str(POWERSHELL), "-NoProfile", "-File", str(kopya / "kur.ps1"), *arglar], env=self.env,
                                 capture_output=True, text=True, encoding="utf-8", errors="replace",
                                 stdin=subprocess.DEVNULL, timeout=120)
            self.assertNotEqual(duz.returncode, 0, self.cikti(duz))
            self.assertNotIn("DENEME MODU bitti", self.cikti(duz))
        r = subprocess.run([COMSPEC, "/c", str(kopya / "kur.cmd"), *arglar], env=self.env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=300)
        self.assertEqual(r.returncode, 0, self.cikti(r))
        self.assertIn("DENEME MODU bitti", self.cikti(r))


if __name__ == "__main__":
    unittest.main()
