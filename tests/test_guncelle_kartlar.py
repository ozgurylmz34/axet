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


def akis_satirlari() -> dict[str, str]:
    """`GUNCELLE.md` akış tablosunun satırları: adım numarası → satırın tam metni."""
    metin = (AXET_HOME / "GUNCELLE.md").read_text(encoding="utf-8")
    return {m.group(1): m.group(0)
            for m in re.finditer(r"^\|\s*(\d+)\s*\|.*$", metin, re.M)}


def commit_atan_komutlar() -> set[str]:
    """MOTORDAN ölç: hangi alt komutun gövdesi `git commit` çalıştırıyor?"""
    out = set()
    for blok in MOTOR_KAYNAK.split("\ndef komut_")[1:]:
        ad = blok.split("(", 1)[0].strip().replace("_", "-")
        govde = blok.split("\ndef ", 1)[0]
        if re.search(r'git\(\s*"commit"', govde):
            out.add(ad)
    return out


class AkisSozlesmesi(unittest.TestCase):
    """`GUNCELLE.md` akış tablosunun kartlarla ve motorla çelişmediğini ölçer.

    KAPSAM — bakılanlar: adım satırlarının hangi komutu emrettiği · commit beyanı ·
    yeniden başlatma ölçütünün adının yazılı olması. Bakılmayanlar: ajanın metni fiilen
    izlemesi (`_lab`, P9) · adım sırasının doğruluğu.
    """

    def setUp(self) -> None:
        self.satirlar = akis_satirlari()
        self.metin = (AXET_HOME / "GUNCELLE.md").read_text(encoding="utf-8")
        if not self.satirlar:
            self.fail("GUNCELLE.md'de akış tablosu satırı bulunamadı")

    def _adim(self, no: str) -> str:
        self.assertIn(no, self.satirlar, f"akış tablosunda {no}. adım satırı yok")
        return self.satirlar[no]

    def test_yargi_adimi_komut_secimini_karta_birakir(self) -> None:
        """Yargı adımı `oneri`yi KOŞULSUZ emretmez: hangi komutun koşacağını kart söyler.

        Gerekçe (ölçüldü): `oneri` taban gerektirir ve taban yoksa DUR (çıkış 2); ayrıca
        silme/ad-çakışması vakalarında birleştirme önerisi ÜRETMEK yanlış yönlendirir.
        Yargı vakalarının hepsi `oneri` istemez — kart isteyenlerde onu kendi 1. adımında çağırır.
        """
        yargi = [s for n, s in self.satirlar.items()
                 if "kart" in s and "isaretle" in s]
        self.assertTrue(yargi, "akış tablosunda `kart` + `isaretle` içeren adım satırı yok")
        hatali = [s for s in yargi if "oneri" in s]
        self.assertEqual(
            [], hatali,
            "akış adımı `oneri`yi zincire koşulsuz koymuş — komut kararı KARTA aittir: %s" % hatali)

    def test_otomatik_adiminda_da_kart_okunur(self) -> None:
        """`uygula --otomatik` satırı da kart okumayı emreder (sınıf kartlarının ek adımları)."""
        otomatik = [s for s in self.satirlar.values() if "--otomatik" in s]
        self.assertTrue(otomatik, "akış tablosunda `uygula --otomatik` satırı yok")
        eksik = [s for s in otomatik if "kart" not in s]
        self.assertEqual(
            [], eksik,
            "otomatik uygulama adımı kart okumayı emretmiyor ⇒ sınıf kartının zorunlu "
            "ek adımları sessizce atlanır: %s" % eksik)

    def test_commit_atan_her_komut_beyan_edilmis(self) -> None:
        """Motorda `git commit` çalıştıran her alt komutun satırı bunu SÖYLER (klonda commit oluşur)."""
        komutlar = commit_atan_komutlar()
        self.assertTrue(komutlar, "motorda commit atan alt komut bulunamadı (regex bayat?)")
        eksik = []
        for ad in sorted(komutlar):
            satir = next((s for s in self.satirlar.values() if ad in s), None)
            if satir is None or "commit" not in satir.lower():
                eksik.append(ad)
        self.assertEqual([], eksik,
                         f"akış tablosunda commit'i beyan etmeyen komutlar: {eksik}")
        self.assertIn("commit", self.metin.split("## Akış")[0].lower(),
                      "'ne yapar / ne yapmaz' bölümü klonda commit atıldığını söylemiyor")

    def test_yeniden_baslatma_olcutu_adiyla_yazili(self) -> None:
        """"Kapat-aç gerekli mi" sorusunun ölçütü planın alanıdır; adı belgede geçmeli."""
        alan = "yeniden_baslat"
        self.assertIn(alan, MOTOR_KAYNAK, "motorda `yeniden_baslat` alanı yok (sözleşme değişmiş?)")
        self.assertIn(alan, self.metin,
                      "GUNCELLE.md 'gerekiyorsa kapat-aç' diyor ama ölçütün adını "
                      f"(`{alan}`) yazmıyor — ajan tahmin eder")


class KartIddiaTutarliligi(unittest.TestCase):
    """Kart metinlerinin diskteki ve motordaki gerçekle çelişmediğini ölçer.

    KAPSAM — bakılanlar: zorunlu kılınan ölçümün somut komut içermesi · anılan repo
    yollarının var olması · ön kontrolün blokladığı bir durumun vaka sebebi sayılmaması.
    Bakılmayanlar: komutun gerçekten o sonucu ürettiği (canlı koşum yok).
    """

    def setUp(self) -> None:
        self.kartlar = {p.name: p.read_text(encoding="utf-8")
                        for p in sorted(kart_dizini().glob("*.md"))}
        self.assertTrue(self.kartlar, "hiç kart yok")

    def test_zorunlu_hukum_karsilastirmasi_somut_komut_verir(self) -> None:
        """"Hüküm karşılaştırması ZORUNLU" diyen kart, KOŞULACAK komutu da verir.

        "Somut komut" = backtick içinde `python <yol>.py …` biçiminde KOŞULABİLİR bir satır.
        Çıplak dosya adı (`run_review.py`) sayılmaz — ölçüldü (mutasyon M11, 2026-09-18):
        gevşek biçim, gerçek komutlar silindiği hâlde testi yeşil bırakıyordu.
        """
        eksik = []
        for ad, metin in self.kartlar.items():
            if "hüküm" not in metin.lower():
                continue
            komutlar = re.findall(r"`(python\s[^`]*\.py[^`]*)`", metin)
            if not any("run_review.py" in k or "run_tests.py" in k for k in komutlar):
                eksik.append(ad)
        self.assertEqual(
            [], eksik,
            "hüküm karşılaştırmasını zorunlu kılan ama komutu yazmayan kartlar: %s — "
            "ölçütsüz zorunluluk 'baktım, fark yok' ile geçilir" % eksik)

    def test_anilan_repo_yollari_diskte_var(self) -> None:
        """Kartların İŞLEM bölümlerinde backtick içinde anılan repo yolları gerçekten var.

        `## Örnek` bölümü ÖLÇÜLMEZ: örnekler kurgusal bir yayını anlatır (`docs/tasinacak.md`
        gibi) ve var olmaları beklenmez — ölçülen şey, ajanın KOŞACAĞI/AÇACAĞI yolların
        gerçekliğidir.
        """
        kaynaklar = dict(self.kartlar)
        kaynaklar["GUNCELLE.md"] = (AXET_HOME / "GUNCELLE.md").read_text(encoding="utf-8")
        eksik = []
        for ad, metin in kaynaklar.items():
            metin = re.sub(r"^## Örnek\b.*?(?=^## |\Z)", "", metin, flags=re.M | re.S)
            for aday in re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|md|json))`", metin):
                if aday.startswith(".axet-guncelleme") or "/" not in aday:
                    continue  # koşum anında üretilen yol · örnek dosya adı (dizinsiz)
                if not (AXET_HOME / aday).exists():
                    eksik.append(f"{ad}: {aday}")
        self.assertEqual([], eksik, f"diskte olmayan yol anılmış: {eksik}")

    def test_onkontrolun_durdurdugu_durum_vaka_sebebi_gosterilmez(self) -> None:
        """Ön kontrol sığ klonu DURDURUYORSA, hiçbir kart onu kendi vakasının sebebi sayamaz."""
        if "is-shallow-repository" not in MOTOR_KAYNAK:
            self.skipTest("motor sığ klon kontrolü yapmıyor — iddia ölçülemez")
        suclu = sorted(ad for ad, metin in self.kartlar.items() if "sığ klon" in metin)
        self.assertEqual(
            [], suclu,
            "ön kontrol (`onkontrol`) sığ klonda çıkış 2 ile durdurur ⇒ o durum plana hiç "
            "ulaşmaz; kart onu yaşayan bir sebep gibi anlatmamalı: %s" % suclu)


class SinifKartiKapsamTablosu(unittest.TestCase):
    """Her sınıf kartı, kapsadığı alt sınıfları harita.json'daki GERÇEK değerleriyle listeler.

    Neden tablo: sınıf kartının düz metni kolayca aşırı genelleşir ("install.py koş",
    "kapat-aç") oysa üst sınıfın bazı alt sınıflarında o adım YOKTUR. Tablo, iddiayı
    alt sınıf başına bağlar ve harita değişince bu test bayatlığı kırmızıya çevirir.

    KAPSAM — bakılanlar: satır kümesi + `etkin` + özel adım KATEGORİSİ. Bakılmayanlar:
    kartın düz metninin tabloyla uyumu (insan incelemesi).
    """

    BASLIK = "## Kapsam (harita.json)"

    def _ozel_kategori(self, ozel) -> str:
        """Motorun `ozel-adim` kuralı: komut içeriyorsa koşar, içermiyorsa MANUEL basar."""
        if not ozel:
            return "yok"
        return "komut" if guncelle._PY_KOMUT.search(ozel) else "manuel"

    def test_kapsam_tablosu_haritayla_birebir(self) -> None:
        h = harita()
        onek = sinif_kart_oneki()
        hatalar = []
        for u in h["ust_siniflar"]:
            p = kart_dizini() / f"{onek}{u['id']}.md"
            if not p.is_file():
                continue  # eksiklik ayrı testin işi
            metin = p.read_text(encoding="utf-8")
            if self.BASLIK not in metin:
                hatalar.append(f"{p.name}: '{self.BASLIK}' bölümü yok")
                continue
            bolum = metin.split(self.BASLIK, 1)[1].split("\n## ", 1)[0]
            bulunan = {(m.group(1), m.group(2), m.group(3).strip())
                       for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|([^|]*)\|",
                                            bolum, re.M)}
            beklenen = {(s["sinif"], "null" if s["etkin"] is None else s["etkin"],
                         self._ozel_kategori(s["ozel_adim"]))
                        for s in h["siniflar"] if s["ust_sinif"] == u["id"]}
            if bulunan != beklenen:
                hatalar.append(f"{p.name}: fazla={sorted(bulunan - beklenen)} "
                               f"eksik={sorted(beklenen - bulunan)}")
        self.assertEqual([], hatalar, "sınıf kartı kapsam tablosu haritayla uyuşmuyor:\n"
                         + "\n".join(hatalar))


if __name__ == "__main__":
    unittest.main()
