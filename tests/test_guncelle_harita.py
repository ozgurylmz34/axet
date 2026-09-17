# -*- coding: utf-8 -*-
"""guncelle/harita.json değişmezleri (TASARIM §3 'Değişmez kural' + §13 P1 kabul ölçütü).

Ölçülenler:
  1. Repodaki (git index'indeki) HER yol TAM BİR sınıfa düşer (sınıfsız = FAIL, beyan edilmemiş
     ikinci eşleşme = FAIL). Örtüşme beyanı YOLA göre kapsanır; ölü beyan da FAIL.
  2. `esler` ve `test.komut` içinde adı geçen her yol diskte vardır.
  3. Birincil olarak HİÇBİR dosya eşlemeyen kural (ölü kural) yoktur.
  4. TASARIM §3 özet tablosunun 13 çekirdek üst sınıfının her birinin en az bir alt sınıfı vardır
     VE `s3_cekirdek` adları §3 tablosunun satırlarıyla BİREBİR (sıra dahil) eşleşir — tablo
     dosyadan okunur, sayı `harita.json`'un kendi bayraklarından türetilmez.
  5. Şema: zorunlu alanlar, etkin/risk değer kümesi, tekil sınıf adı, tanımlı ust_sinif.
  6. TASARIM §3 sınır kararları uygulanmıştır (_gate_status.py, check_package_naming.py).
  7. Denetimin KENDİSİ boş değildir: sentetik bozuk girdilerde gerçekten FAIL verir (negatif test).

KAPSAM — bakılmayanlar: `test.komut`'ların gerçekten koştuğu (yalnız yol varlığı ölçülür) ·
`yukleme` metinlerinin doğruluğu · `risk`/`kritik_yol` yargısının isabeti · dosya içeriği.
"""
from __future__ import annotations

import copy
import fnmatch
import sys
import unittest
from pathlib import Path

AXET_HOME = Path(__file__).resolve().parents[1]
GUNCELLE = AXET_HOME / "guncelle"
if str(GUNCELLE) not in sys.path:
    sys.path.insert(0, str(GUNCELLE))

import siniflandir  # noqa: E402

# TASARIM §3 "Özet eşleme (harita v1 çekirdeği)" tablosunun 13 satırı.
S3_CEKIRDEK_SATIR_SAYISI = 13
TASARIM_YOLU = AXET_HOME / "maintenance" / "guncelle-mimari" / "TASARIM.md"
TASARIM_BASLIK = "**Özet eşleme (harita v1 çekirdeği):**"


def s3_tablo_adlari() -> list[str]:
    """TASARIM §3 özet tablosunun 1. sütunu (sırasıyla), backtick'siz ve boşluk-normalize."""
    metin = TASARIM_YOLU.read_text(encoding="utf-8")
    govde = metin[metin.index(TASARIM_BASLIK) + len(TASARIM_BASLIK):]
    adlar, basladi = [], False
    for satir in govde.splitlines():
        parca = satir.strip()
        if not parca.startswith("|"):
            if basladi:
                break
            continue
        basladi = True
        hucre = parca.strip("|").split("|")[0].strip()
        if hucre.lower() == "sınıf" or (hucre and set(hucre) <= set("-: ")):
            continue
        adlar.append(" ".join(hucre.replace("`", "").split()))
    return adlar


class HaritaTemelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.harita = siniflandir.harita_yukle()
        cls.yollar = siniflandir.evren(AXET_HOME)

    def test_evren_bos_degil(self) -> None:
        self.assertGreater(len(self.yollar), 100,
                           "git evren komutu beklenenden az dosya döndürdü — ölçüm geçersiz")

    def test_denetim_temiz(self) -> None:
        """Haritanın tüm değişmezleri tek seferde: sorun listesi BOŞ olmalı."""
        sorunlar = siniflandir.denetle(self.harita, self.yollar, AXET_HOME)
        self.assertEqual([], sorunlar, "harita denetimi sorun buldu:\n  " + "\n  ".join(sorunlar))

    def test_her_yol_tam_bir_sinifa_duser(self) -> None:
        sinifsiz = [y for y in self.yollar if siniflandir.siniflandir(y, self.harita) is None]
        self.assertEqual([], sinifsiz, f"sınıfsız dosya var: {sinifsiz}")

    def test_beyan_edilmemis_coklu_sinif_yok(self) -> None:
        """Beyan çift adıyla DEĞİL, yol globuyla kapsanır (bug gate 2026-09-15, MEDIUM)."""
        beyan = {(o[0], o[1]): o[2] for o in self.harita.get("beklenen_ortusme", [])}
        ihlal = []
        for y in self.yollar:
            m = siniflandir.eslesenler(y, self.harita)
            for g in m[1:]:
                desenler = beyan.get((m[0], g))
                if desenler is None:
                    ihlal.append(f"{y}: {m[0]} + {g} (beyan yok)")
                elif not any(fnmatch.fnmatchcase(y, d) for d in desenler):
                    ihlal.append(f"{y}: {m[0]} + {g} (beyan bu yolu kapsamiyor: {desenler})")
        self.assertEqual([], ihlal, f"beyan edilmemiş/kapsam dışı örtüşme: {ihlal}")

    def test_olu_kural_yok(self) -> None:
        dokum = siniflandir.dokum(self.harita, self.yollar)
        olu = [k["sinif"] for k in self.harita["siniflar"]
               if not dokum[k["sinif"]] and not k.get("beklenen_bos")]
        self.assertEqual([], olu, f"birincil olarak hiçbir dosya eşlemeyen kural: {olu}")

    def test_s3_cekirdek_ust_siniflari_dolu(self) -> None:
        cekirdek = [u for u in self.harita["ust_siniflar"] if u.get("s3_cekirdek")]
        self.assertEqual(S3_CEKIRDEK_SATIR_SAYISI, len(cekirdek),
                         "TASARIM §3 özet tablosu 13 satırdır; s3_cekirdek sayısı tutmuyor")
        kullanilan = {k["ust_sinif"] for k in self.harita["siniflar"]}
        bos = [u["id"] for u in cekirdek if u["id"] not in kullanilan]
        self.assertEqual([], bos, f"§3 çekirdek satırı alt sınıfsız kaldı: {bos}")

    def test_s3_cekirdek_adlari_tasarim_tablosuyla_eslesir(self) -> None:
        """13 sayısı haritanın kendi bayraklarından değil, §3 TABLOSUNDAN ölçülür.

        Eski hâli öz-referanslıydı: yanlış bir üst sınıfa `s3_cekirdek` konup doğrusundan
        kaldırılsa sayı yine 13 kalır ve test geçerdi (bug gate 2026-09-15, MEDIUM).
        """
        if not TASARIM_YOLU.exists():
            self.skipTest("TASARIM.md yok (public sürümde maintenance/ dışlanır) — "
                          "§3 eşliği ÖLÇÜLEMEDİ, 'temiz' DEĞİL")
        tasarim = s3_tablo_adlari()
        self.assertEqual(S3_CEKIRDEK_SATIR_SAYISI, len(tasarim),
                         f"TASARIM §3 özet tablosu {len(tasarim)} satır okundu, "
                         f"{S3_CEKIRDEK_SATIR_SAYISI} bekleniyordu — tablo değiştiyse harita ve "
                         f"bu sabit birlikte güncellenmeli")
        harita_adlari = [" ".join(u["ad"].replace("`", "").split())
                         for u in self.harita["ust_siniflar"] if u.get("s3_cekirdek")]
        self.assertEqual(tasarim, harita_adlari,
                         "s3_cekirdek üst sınıf adları §3 tablosuyla (sıra dahil) eşleşmiyor")

    def test_esler_ve_test_yollari_diskte_var(self) -> None:
        eksik = [s for s in siniflandir.denetle(self.harita, self.yollar, AXET_HOME)
                 if "diskte yok" in s or "cwd'si yok" in s]
        self.assertEqual([], eksik, f"haritada adı geçen yol diskte yok: {eksik}")


class SinirKarariTest(unittest.TestCase):
    """TASARIM §3'te açıkça karara bağlanan iki sınır dosyası."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.harita = siniflandir.harita_yukle()

    def test_gate_status_validator_gate_motoruna_duser(self) -> None:
        yol = "skills-sap/sap-adt-foundation/scripts/sapadt/lib/validators/_gate_status.py"
        self.assertTrue((AXET_HOME / yol).exists(), f"{yol} diskte yok — sınır kararı ölçülemez")
        self.assertEqual("validator-gate-motor", siniflandir.siniflandir(yol, self.harita))

    def test_check_package_naming_validator_ailesinde(self) -> None:
        yol = "scripts/check_package_naming.py"
        self.assertTrue((AXET_HOME / yol).exists(), f"{yol} diskte yok — sınır kararı ölçülemez")
        sinif = siniflandir.siniflandir(yol, self.harita)
        kayit = next(k for k in self.harita["siniflar"] if k["sinif"] == sinif)
        self.assertEqual("validator-ailesi", kayit["ust_sinif"],
                         f"{yol} validator ailesine düşmeli, düştüğü sınıf: {sinif}")


class DenetimNegatifTest(unittest.TestCase):
    """Denetim boş bir tören değil: bozuk girdide GERÇEKTEN sorun bildiriyor mu."""

    def setUp(self) -> None:
        self.harita = siniflandir.harita_yukle()
        self.yollar = siniflandir.evren(AXET_HOME)

    def _sorunlar(self, harita=None, yollar=None) -> list[str]:
        return siniflandir.denetle(harita or self.harita, yollar or self.yollar, AXET_HOME)

    def test_sinifsiz_dosya_yakalanir(self) -> None:
        sorunlar = self._sorunlar(yollar=self.yollar + ["yepyeni_klasor/bilinmeyen.xyz"])
        self.assertTrue(any("sınıfsız dosya" in s for s in sorunlar),
                        f"sınıfsız dosya yakalanmadı: {sorunlar}")

    def test_beyansiz_ortusme_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["beklenen_ortusme"] = []
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("birden fazla birincil sınıf" in s for s in sorunlar),
                        "örtüşme beyanı silindiği hâlde hiçbir sorun bildirilmedi")

    def test_olu_kural_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"].insert(0, {
            "sinif": "hayalet-sinif", "ust_sinif": "bakim-ic", "glob": ["hic-olmayan-yol/*"],
            "yukleme": "-", "etkin": None, "esler": [], "test": [], "risk": "dusuk",
            "ozel_adim": None, "kritik_yol": False})
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("ölü kural" in s and "hayalet-sinif" in s for s in sorunlar),
                        f"ölü kural yakalanmadı: {sorunlar}")

    def test_olmayan_es_yolu_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["esler"] = ["hic-olmayan-dosya.md"]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("eş yolu diskte yok" in s for s in sorunlar),
                        f"olmayan eş yolu yakalanmadı: {sorunlar}")

    def test_olmayan_test_komutu_yolu_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["test"] = [
            {"komut": "python tests/hic_olmayan_test.py", "cwd": ".", "on_kosul": None}]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("test komutundaki yol diskte yok" in s for s in sorunlar),
                        f"olmayan test yolu yakalanmadı: {sorunlar}")

    def test_bos_s3_cekirdek_ust_sinifi_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["ust_siniflar"].append({"id": "kullanilmayan-ust", "ad": "deneme",
                                      "s3_cekirdek": True})
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("hiçbir alt sınıfa sahip değil" in s for s in sorunlar),
                        f"boş çekirdek üst sınıf yakalanmadı: {sorunlar}")

    def test_beyan_disi_ortusme_yolu_yakalanir(self) -> None:
        """Beyan var ama yol globu kapsamıyorsa FAIL (çift adı düzeyinde muafiyet yok)."""
        bozuk = copy.deepcopy(self.harita)
        for o in bozuk["beklenen_ortusme"]:
            if (o[0], o[1]) == ("validator", "skill-script"):
                o[2] = ["hic-eslesmeyen-yol/*.py"]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("beyan dışı örtüşme yolu" in s for s in sorunlar),
                        f"beyan globu daraltıldığı hâlde yakalanmadı: {sorunlar}")

    def test_olu_ortusme_beyani_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["beklenen_ortusme"].append(["validator", "belge-lisans", ["hicbir/yer/*"]])
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("ölü örtüşme beyanı" in s for s in sorunlar),
                        f"ölü örtüşme beyanı yakalanmadı: {sorunlar}")

    def test_uclu_olmayan_ortusme_beyani_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["beklenen_ortusme"].append(["validator", "belge-lisans"])
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("üçlüsü olmalı" in s for s in sorunlar),
                        f"eksik alanlı örtüşme beyanı yakalanmadı: {sorunlar}")

    def test_gerekcesiz_beklenen_bos_yakalanir(self) -> None:
        """`beklenen_bos` gerekçesiz kullanılamaz — sınırsız kaçış deliği olmasın."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"].insert(0, {
            "sinif": "gerekcesiz-muaf", "ust_sinif": "bakim-ic", "glob": ["hic-olmayan-yol/*"],
            "yukleme": "-", "etkin": None, "esler": [], "test": [], "risk": "dusuk",
            "ozel_adim": None, "kritik_yol": False, "beklenen_bos": True})
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("beklenen_bos_neden" in s for s in sorunlar),
                        f"gerekçesiz beklenen_bos yakalanmadı: {sorunlar}")

    def test_gecersiz_etkin_degeri_yakalanir(self) -> None:
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["etkin"] = "her-zaman"
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("geçersiz etkin" in s for s in sorunlar),
                        f"geçersiz etkin değeri yakalanmadı: {sorunlar}")


    def test_yazim_hatali_k_filtresi_yakalanir(self) -> None:
        """`-k` DEĞERİ hiçbir test adıyla eşleşmiyorsa FAIL (D17 açık kalemi, 2026-09-17).

        Eski hâli: `_yol_simgeleri` `-` ile başlayanı atladığı için filtre DEĞERİNE hiç
        bakılmıyordu → haritaya yazım hatalı bir filtre girilirse denetim sessiz kalıyordu.
        """
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["test"] = [
            {"komut": "python tests/run_tests.py -k guncelle_haritaXX", "cwd": ".",
             "on_kosul": None}]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("hiçbir test adıyla eşleşmiyor" in s for s in sorunlar),
                        f"yazım hatalı -k filtresi yakalanmadı: {sorunlar}")

    def test_dogru_k_filtresi_sorun_uretmez(self) -> None:
        """KONTROL GRUBU: çalıştığı BİLİNEN filtre değeri sorun üretmemeli (yanlış pozitif yok)."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["test"] = [
            {"komut": "python tests/run_tests.py -k guncelle_harita", "cwd": ".",
             "on_kosul": None}]
        k_sorunlari = [s for s in self._sorunlar(harita=bozuk) if "-k" in s]
        self.assertEqual([], k_sorunlari, f"geçerli filtre yanlış yere sorun üretti: {k_sorunlari}")

    def test_degersiz_k_filtresi_yakalanir(self) -> None:
        """`-k`'dan sonra değer yoksa koşucu rc=2 verir; denetim de sessiz kalmamalı."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["test"] = [
            {"komut": "python tests/run_tests.py -k", "cwd": ".", "on_kosul": None}]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("-k" in s and "değer" in s for s in sorunlar),
                        f"değersiz -k yakalanmadı: {sorunlar}")

    def test_yanlis_harfli_es_yolu_yakalanir(self) -> None:
        """Harf-duyarlı varlık denetimi (D17 açık kalemi): Windows'ta `Path.exists()` harf-duyarsız
        olduğu için yanlış harfli yol GEÇİYORDU; Linux/macOS tüketicisinde FAIL olurdu."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["esler"] = ["Scripts/doctor.py"]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("eş yolu diskte yok" in s and "Scripts/doctor.py" in s
                            for s in sorunlar),
                        f"yanlış harfli eş yolu yakalanmadı: {sorunlar}")

    def test_dogru_harfli_es_yolu_gecer(self) -> None:
        """KONTROL GRUBU: doğru harfli aynı yol sorun ÜRETMEMELİ."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["esler"] = ["scripts/doctor.py"]
        sorunlar = [s for s in self._sorunlar(harita=bozuk) if "eş yolu diskte yok" in s]
        self.assertEqual([], sorunlar, f"doğru harfli yol yanlışlıkla eksik sayıldı: {sorunlar}")

    def test_yanlis_harfli_glob_deseni_yakalanir(self) -> None:
        """Glob dalı da harf-duyarlı olmalı: `Path.glob` Windows'ta harf-duyarsız eşler."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["esler"] = ["Scripts/*.py"]
        sorunlar = self._sorunlar(harita=bozuk)
        self.assertTrue(any("eş yolu diskte yok" in s and "Scripts/*.py" in s for s in sorunlar),
                        f"yanlış harfli glob yakalanmadı: {sorunlar}")

    def test_dogru_harfli_glob_deseni_gecer(self) -> None:
        """KONTROL GRUBU: doğru harfli glob sorun ÜRETMEMELİ."""
        bozuk = copy.deepcopy(self.harita)
        bozuk["siniflar"][0]["esler"] = ["scripts/*.py"]
        sorunlar = [s for s in self._sorunlar(harita=bozuk) if "eş yolu diskte yok" in s]
        self.assertEqual([], sorunlar, f"doğru harfli glob yanlışlıkla eksik sayıldı: {sorunlar}")


if __name__ == "__main__":
    unittest.main()
