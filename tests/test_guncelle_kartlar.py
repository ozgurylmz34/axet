# -*- coding: utf-8 -*-
"""`guncelle/kartlar/**` + `GUNCELLE.md` — vaka/sınıf kartlarının TAMLIĞI (TASARIM §5, P3 kabul ölçütü).

KABUL ÖLÇÜTÜ: **plana girebilen her vaka kodunun bir kartı vardır.** Kartı `scripts/guncelle.py kart
<KOD>` basar; kart yoksa komut çıkış 2 verir ve ajanın o vakada izleyeceği yordam YOKTUR.

Bu dosyanın değişmezi: **kart listesi burada ELLE YAZILMAZ.** Liste iki kaynaktan türetilir —
`scripts/guncelle.py` sabitleri (hangi kodlar plana girer) ve `guncelle/harita.json` (hangi üst
sınıflar var). Elle yazılan liste motor değişince sessizce bayatlar; `KartListesiTuretilmis` bu
dosyanın kendi kaynağını tarayarak o sapmayı kırmızıya çevirir.

KAPSAM — bakılmayanlar: kartların İÇERİĞİNİN doğruluğu/anlaşılırlığı (doküman incelemesi işi; burada
yalnız iskelet başlıkları, başlık satırı ve asgari gövde ölçülür) · `kart` komutunun canlı koşumu
(kartı `origin/main`'den okur, yerel çalışma ağacından DEĞİL — dal merge edilene kadar mekanik olarak
ölçülemez; `tests/test_guncelle.py` sahte public depo ile o kablolamayı ayrıca ölçer) · GUNCELLE.md
metninin modele fiilen talimat olması (`_lab`, P9) · Linux/macOS.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

BURASI = Path(__file__).resolve().parent
AXET_HOME = BURASI.parent
if str(AXET_HOME / "scripts") not in sys.path:
    sys.path.insert(0, str(AXET_HOME / "scripts"))

import guncelle  # noqa: E402  (motor sözleşmesinin KENDİSİ kaynaktır)

MOTOR_KAYNAK = (AXET_HOME / "scripts" / "guncelle.py").read_text(encoding="utf-8")

# Bu dosyada geçmesine izin verilen TEK vaka-kodu dizgesi. Gerekçe (ölçüldü, guncelle.py
# `dosya_vakasi`): `vaka_kodu()` ara sonuç olarak bu kodu döndürür ve `dosya_vakasi` onu DAİMA
# alt koda (temiz/çakışmalı/eşik/ikili) çevirir; plana hiç yazılmaz, dolayısıyla kartı da yoktur.
ARA_KOD = "V" + "4"


def kart_dizini() -> Path:
    """Kart klasörünü MOTORDAN türet: `komut_kart` hangi yoldan okuyorsa kartlar oradadır."""
    m = re.search(r"origin/main:([\w\-/]+)/\{args\.kod\}\.md", MOTOR_KAYNAK)
    assert m, "guncelle.py `komut_kart` içindeki kart yolu bulunamadı (sözleşme değişmiş olabilir)"
    return AXET_HOME / m.group(1)


def sinif_kart_oneki() -> str:
    """Sınıf kartı adlandırmasını motorun KENDİ fonksiyonundan ölç (tahmin etme)."""
    kartlar = guncelle._kart_listesi({"vaka": "?"}, {"ust_sinif": "ORNEK"})
    aday = [k for k in kartlar if k.endswith("ORNEK")]
    assert aday, f"_kart_listesi sınıf kartı üretmedi: {kartlar}"
    return aday[0][: -len("ORNEK")]


def harita() -> dict:
    return json.loads((AXET_HOME / "guncelle" / "harita.json").read_text(encoding="utf-8"))


def beklenen_vaka_kartlari() -> set[str]:
    """Plana GİREN kodlar = otomatik uygulananlar ∪ yargı isteyenler (guncelle.py sabitleri)."""
    return set(guncelle.OTOMATIK_VAKALAR) | set(guncelle.YARGI_VAKALARI)


def beklenen_sinif_kartlari() -> set[str]:
    onek = sinif_kart_oneki()
    return {onek + u["id"] for u in harita()["ust_siniflar"]}


VAKA_BASLIKLARI = ("## Ne demek", "## Neden", "## Adımlar", "## Örnek", "## Beklenen çıktı", "## DUR")
SINIF_BASLIKLARI = ("## Tetik", "## Zorunlu ek adımlar", "## DUR")


class KartTamligi(unittest.TestCase):
    def setUp(self) -> None:
        self.dizin = kart_dizini()

    def test_dizin_var(self) -> None:
        self.assertTrue(self.dizin.is_dir(), f"kart klasörü yok: {self.dizin}")

    def test_her_plan_vaka_kodunun_karti_var(self) -> None:
        """KABUL ÖLÇÜTÜ. Liste guncelle.py sabitlerinden türetilir."""
        eksik = sorted(k for k in beklenen_vaka_kartlari()
                       if not (self.dizin / f"{k}.md").is_file())
        self.assertEqual([], eksik, f"kartı olmayan vaka kodları: {eksik}")

    def test_islemsiz_kodlarin_karti_yok(self) -> None:
        """TASARIM §5: işlem yok ⇒ 'Kart yok; plan bu kodları yalnız sayar'."""
        fazla = sorted(k for k in guncelle.ISLEMSIZ_VAKALAR if (self.dizin / f"{k}.md").is_file())
        self.assertEqual([], fazla, f"işlemsiz kodlara kart yazılmış (§5 ile çelişir): {fazla}")

    def test_her_ust_sinifin_karti_var(self) -> None:
        eksik = sorted(k for k in beklenen_sinif_kartlari()
                       if not (self.dizin / f"{k}.md").is_file())
        self.assertEqual([], eksik, f"kartı olmayan üst sınıflar: {eksik}")

    def test_yetim_kart_yok(self) -> None:
        """Klasörde ne varsa ya bir plan vaka kodudur ya bir üst sınıftır."""
        beklenen = beklenen_vaka_kartlari() | beklenen_sinif_kartlari()
        yetim = sorted(p.stem for p in self.dizin.glob("*.md") if p.stem not in beklenen)
        self.assertEqual([], yetim, f"hiçbir koda/sınıfa bağlanmayan kart: {yetim}")

    def test_kart_iskeleti(self) -> None:
        """Her kart: `# <ad> — <başlık>` ilk satırı + §5 iskelet başlıkları."""
        hatalar: list[str] = []
        for ad in sorted(beklenen_vaka_kartlari() | beklenen_sinif_kartlari()):
            p = self.dizin / f"{ad}.md"
            if not p.is_file():
                continue  # eksiklik ayrı testin işi
            satirlar = p.read_text(encoding="utf-8").splitlines()
            ilk = satirlar[0] if satirlar else ""
            if not re.match(rf"^# {re.escape(ad)} — \S.*", ilk):
                hatalar.append(f"{p.name}: ilk satır `# {ad} — <başlık>` değil: {ilk!r}")
            govde = "\n".join(satirlar)
            beklenen = SINIF_BASLIKLARI if ad.startswith(sinif_kart_oneki()) else VAKA_BASLIKLARI
            for b in beklenen:
                if b not in govde:
                    hatalar.append(f"{p.name}: eksik bölüm {b!r}")
        self.assertEqual([], hatalar, "kart iskeleti bozuk:\n" + "\n".join(hatalar))

    def test_kart_bos_degil(self) -> None:
        kisa = sorted(p.name for p in self.dizin.glob("*.md")
                      if len(p.read_text(encoding="utf-8").strip()) < 200)
        self.assertEqual([], kisa, f"gövdesi yok denecek kadar kısa kart: {kisa}")


class KartListesiTuretilmis(unittest.TestCase):
    """MUTASYON KALKANI: bu test dosyası kart listesini elle sabitlerse kırmızı olur."""

    def test_kart_listesi_elle_sabitlenmemis(self) -> None:
        kaynak = Path(__file__).read_text(encoding="utf-8")
        kodlar = set(re.findall(r"""["'](V[0-9][A-Za-z0-9+]*)["']""", kaynak))
        self.assertEqual(
            set(), kodlar - {ARA_KOD},
            "vaka kodu bu test dosyasına ELLE yazılmış: %s — liste guncelle.py sabitlerinden "
            "TÜRETİLMELİ (elle liste motor değişince sessizce bayatlar)."
            % sorted(kodlar - {ARA_KOD}))
        sinif_kodlari = set(re.findall(r"""["'](sinif-[a-z0-9\-]+)["']""", kaynak))
        self.assertEqual(set(), sinif_kodlari,
                         "sınıf kartı adı elle yazılmış: %s — harita.json'dan türetilmeli."
                         % sorted(sinif_kodlari))

    def test_ara_kodun_karti_yok(self) -> None:
        """Ara kod plana hiç yazılmaz (dosya_vakasi onu daima alt koda çevirir) ⇒ kartı da olmaz."""
        self.assertNotIn(ARA_KOD, beklenen_vaka_kartlari())
        self.assertFalse((kart_dizini() / f"{ARA_KOD}.md").is_file())


class GuncelleMd(unittest.TestCase):
    """`GUNCELLE.md` — ajanın akış belgesi; özet tablosu haritadan türer (TASARIM §7 + §3)."""

    def setUp(self) -> None:
        self.yol = AXET_HOME / "GUNCELLE.md"
        if not self.yol.is_file():
            self.fail(f"GUNCELLE.md yok: {self.yol}")
        self.metin = self.yol.read_text(encoding="utf-8")

    def test_tum_alt_komutlar_anilir(self) -> None:
        komutlar = set(re.findall(r'add_parser\(\s*"([a-z\-]+)"', MOTOR_KAYNAK))
        self.assertTrue(komutlar, "guncelle.py'de alt komut bulunamadı (regex bayat?)")
        eksik = sorted(k for k in komutlar if f"`{k}`" not in self.metin
                       and f"guncelle.py {k}" not in self.metin)
        self.assertEqual([], eksik, f"GUNCELLE.md'de anılmayan alt komutlar: {eksik}")

    def test_tum_ust_siniflar_anilir(self) -> None:
        eksik = sorted(u["id"] for u in harita()["ust_siniflar"] if u["id"] not in self.metin)
        self.assertEqual([], eksik, f"GUNCELLE.md özet tablosunda eksik üst sınıflar: {eksik}")

    def test_kart_dizini_anilir(self) -> None:
        self.assertIn(kart_dizini().name, self.metin)


if __name__ == "__main__":
    unittest.main()
