#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kaynak_paketi.py — ikili kaynak belgeden (.docx / .xlsx) MEKANİK kaynak paketi ve kaynak → belge iz denetimi.

Kullanım:
  python kaynak_paketi.py cikar <kaynak.docx|.xlsx> [--hedef-kok <dizin>] [--id <ad>]
  python kaynak_paketi.py iz <paket-dizini> --tablo <iz-tablosu.md> --belge <FS.md> [--belge <EK.md> …]

cikar: kaynak belgeyi model YENİDEN YAZMADAN pakete çıkarır → <hedef-kok>/<id>/ (varsayılan hedef kök:
  <çalışma dizini>/.axet-code/tmp, varsayılan id: <dosya adı>-<içerik özetinin ilk 8 hanesi>):
    metin.md   tam metin, kaynak sırasıyla; her metin bloğu (başlık, paragraf, tablo satırı) bir kaynak maddesi KM-nnnn
    media/     belgedeki görseller (KG-nn) · gomulu/  gömülü nesneler (KN-nn): OLE paket nesnesinin asıl dosyası
               (ör. HTML prototip), OLE içindeki OOXML paketi, altChunk içeriği; tanınmayan ham kopyalanır
    INDEX.md   sayım tablosu (kaynaktan bağımsız sayım ↔ diskteki paket) + dosya listesi + nasıl okunur
    paket.json makine için aynı bilgi (iz alt komutu okur)
  Doğrulama paketi DİSKTEN yeniden okur ve kaynağın ayrı kodla yapılan sayımıyla karşılaştırır; eşit değilse FAIL.
iz: kaynak maddesi → belge kimliği (FR/KR/TC/SCR…) eşleme tablosunu denetler: her KM/KG/KN satırda mı, boş eşleme,
  belgede olmayan kimlik, pakette olmayan madde. Belgeyi okuyup "doğru eşlendi mi" yargısı VERMEZ (inceleyicinin işi).
Çıkış: 0 PASS · 1 FAIL (paket/tablo kullanılamaz) · 2 girdi okunamadı · 3 biçim desteklenmiyor (.pdf, .doc, .xls …).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

for _a in (sys.stdout, sys.stderr):
    try:
        _a.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
SCOPE_CIKAR = (
    "KAPSAM (SCOPE): kaynak_paketi cikar — .docx: ana gövde (paragraf, başlık, tablo; tablo içi tablo hücre metnine "
    "düzleşir; metin kutusunun paragraf ve tabloları bulunduğu paragrafın satırına düzleşir; denklem metni satır içinde "
    "⟦denklem⟧ işaretiyle), SmartArt (D) ve grafik (G) metni kendi KM satırında, word/media görselleri, "
    "word/embeddings nesneleri, altChunk. .xlsx: sayfa satırları, xl/drawings metin kutuları (K), SmartArt, grafik, "
    "xl/media, xl/embeddings. BAKMADIKLARI: üst/altbilgi, dipnot, yorum, izlenen değişiklikte silinen metin, "
    "gömülü/altChunk içeriğin METNİ (dosya olarak çıkar, metin.md'ye girmez), görselin içindeki yazı, metin taşımayan "
    "çizim öğeleri (mürekkep, 3B model), xlsx'te birleştirilmiş hücre/biçim, nesnenin hangi hücrede durduğu ve sayı/"
    "tarih hücresinin karakteri (xlsx'te yalnız metin hücreleri karakter sayımına girer). Boyut sınırı: zip üyesi "
    "≤ 100 MiB, açılmış toplam ≤ 512 MiB — aşan girdi ÖLÇÜLEMEDİ (çıkış 2). Doğrulama sayım eşitliğidir; içerik "
    "doğruluğu değil.")
SCOPE_IZ = (
    "KAPSAM (SCOPE): kaynak_paketi iz — paketin her KM/KG/KN maddesi tabloda tam bir satırda mı, eşleme boş mu, "
    "kimlik belgede geçiyor mu, tablo pakette olmayan madde anıyor mu, tablodaki kaynak sha256'sı paketinkiyle aynı mı; "
    "belgedeki FR/KR tabloda anılıyor mu, paket boş mu, tabloda sha256 var mı (UYARI). "
    "BAKMADIKLARI: eşlemenin ANLAMCA doğruluğu (KM metni gerçekten o FR'de karşılanmış mı), BİLGİ/KAPSAM-DIŞI "
    "işaretinin haklılığı — ikisi de inceleyici yargısıdır.")

DESTEKLENEN = (".docx", ".docm", ".xlsx", ".xlsm")
DESTEKLENMEYEN_NEDEN = {
    ".pdf": "PDF'ten metin standart kütüphaneyle güvenilir biçimde (sıra, tablo) çıkarılamıyor",
    ".doc": "eski ikili Word biçimi okunmuyor",
    ".xls": "eski ikili Excel biçimi okunmuyor",
    ".rtf": "RTF okunmuyor",
    ".pptx": "sunu biçimi okunmuyor",
}
KM_RE = re.compile(r"^(#{1,6} )?\[(KM-\d{4,})\] ")
NOT_RE = re.compile(r"⟦[^⟧]*⟧")
SATIR_RE = re.compile(r"^⟦(T\d+|SY(\d+))\.S(\d+)⟧ ")
NESNE_RE = re.compile(r"^⟦([DGK])\d+ (SmartArt|grafik|metin kutusu): [^⟧]*⟧ ?")
NESNE_ANAHTAR = {"SmartArt": "diyagram", "grafik": "grafik", "metin kutusu": "metin_kutusu"}
DENKLEM = "⟦denklem⟧"

# Boyut sınırları (zip üyesinin açılmış boyu ve tüm üyelerin toplamı; zip başlığındaki beyandan okunur, açmadan).
# Ölçülmüş bir eşik değil, paydır: tipik bir istek belgesi onlarca MB'ın altındadır; çıkarım üyeyi belleğe alır ve
# tepe bellek açılmış boyun yaklaşık iki katıdır (ölçüldü 2026-11-19: 150 MB'lık sıkıştırılmış sıfır üyesi → 339 MB
# tepe). Aşan girdi FAIL değil ÖLÇÜLEMEDİ'dir (çıkış 2): paket hiç yazılmaz.
MAX_UYE = 100 * 1024 * 1024
MAX_TOPLAM = 512 * 1024 * 1024


class Okunamadi(Exception):
    """Girdi okunamadı (bozuk zip, eksik ana parça) — çıkış 2."""


def yerel(tag) -> str:
    """'{ad alanı}yerel' → 'yerel'. Ad alanı URI'leri bu dosyada bilerek yazılmaz (skill iz taraması URL yasaklar)."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def attr_yerel(el, ad: str):
    for k, v in el.attrib.items():
        if yerel(k) == ad:
            return v
    return None


def ozet(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guvenli_ad(ad: str, varsayilan: str = "dosya") -> str:
    ad = ad.replace("\\", "/").rsplit("/", 1)[-1]
    ad = re.sub(r'[<>:"|?*\x00-\x1f]', "_", ad).strip(" .")
    return ad[:120] or varsayilan


def bosluksuz(s: str) -> int:
    return sum(1 for ch in s if not ch.isspace())


# ── OLE / CFB (bileşik ikili dosya) okuyucu — yalnız okuma, stdlib ─────────────────────────────────────────────
ENDOFCHAIN = 0xFFFFFFFE
FREESECT = 0xFFFFFFFF
CFB_IMZA = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class CfbHata(Exception):
    pass


def cfb_akislari(data: bytes) -> dict[str, bytes]:
    """CFB içindeki akışlar {ad: içerik}. Bozuk/kısa dosya her yolda CfbHata verir (struct/indeks hatası sızmaz)."""
    try:
        return _cfb_akislari(data)
    except CfbHata:
        raise
    except (struct.error, IndexError, ValueError, OverflowError, UnicodeError) as exc:
        raise CfbHata(f"bozuk CFB ({type(exc).__name__}: {exc})") from None


def _cfb_akislari(data: bytes) -> dict[str, bytes]:
    """Ağaç yürünmez, dizin girdileri sırayla okunur (yalnız ad gerekiyor). Tablo boyları (DIFAT/FAT sektör sayısı)
    dosyadaki sektör sayısıyla sınırlanır; DIFAT zinciri ziyaret kümesiyle yürünür (döngü = bozuk)."""
    if len(data) < 512 or data[:8] != CFB_IMZA:
        raise CfbHata("CFB imzası yok")
    sector_shift, mini_shift = struct.unpack_from("<HH", data, 0x1E)
    if sector_shift not in (9, 12) or mini_shift != 6:
        raise CfbHata("beklenmeyen sektör boyu")
    ssz = 1 << sector_shift
    n_sektor = max(0, (len(data) - ssz + ssz - 1) // ssz)  # başlıktan sonraki sektör sayısı (son kısmi dahil)
    n_fat, first_dir = struct.unpack_from("<II", data, 0x2C)
    cutoff, first_minifat, n_minifat, first_difat, n_difat = struct.unpack_from("<IIIII", data, 0x38)
    n_fat, n_difat = min(n_fat, n_sektor), min(n_difat, n_sektor)

    def sektor(n: int, tam: bool = True) -> bytes:
        off = (n + 1) * ssz
        if n >= 0xFFFFFFFA or off >= len(data):
            raise CfbHata(f"sektör dışı: {n}")
        parca = data[off:off + ssz]
        if tam and len(parca) < ssz:  # tablo sektörü (DIFAT/FAT/dizin/mini FAT) kesik olamaz
            raise CfbHata(f"kısa sektör: {n} ({len(parca)}/{ssz} bayt)")
        return parca

    fat_ids = [x for x in struct.unpack_from("<109I", data, 0x4C) if x != FREESECT]
    d, gorulen = first_difat, set()
    while d not in (ENDOFCHAIN, FREESECT) and len(gorulen) < n_difat:
        if d in gorulen:
            raise CfbHata("DIFAT zinciri döngülü")
        gorulen.add(d)
        vals = struct.unpack_from("<%dI" % (ssz // 4), sektor(d))
        fat_ids += [x for x in vals[:-1] if x != FREESECT]
        d = vals[-1]
    fat: list[int] = []
    for f in fat_ids[:n_fat]:
        fat += struct.unpack_from("<%dI" % (ssz // 4), sektor(f))

    def zincir(start: int, tablo: list[int]) -> list[int]:
        out, n = [], start
        while n not in (ENDOFCHAIN, FREESECT):
            if n >= len(tablo) or len(out) > len(tablo):
                raise CfbHata("bozuk sektör zinciri")
            out.append(n)
            n = tablo[n]
        return out

    dir_data = b"".join(sektor(n) for n in zincir(first_dir, fat))
    girdiler = []
    for i in range(0, len(dir_data) - 127, 128):
        e = dir_data[i:i + 128]
        ad_len = struct.unpack_from("<H", e, 64)[0]
        tur = e[66]
        start, size = struct.unpack_from("<IQ", e, 116)
        if tur == 0:
            continue
        ad = e[:max(0, ad_len - 2)].decode("utf-16-le", "replace")
        if (struct.unpack_from("<H", data, 0x1A)[0]) == 3:
            size &= 0xFFFFFFFF
        girdiler.append((ad, tur, start, size))
    kok = next((g for g in girdiler if g[1] == 5), None)
    if kok is None:
        raise CfbHata("kök girdi yok")
    mini_stream = b"".join(sektor(n) for n in zincir(kok[2], fat))[:kok[3]] if kok[3] else b""
    minifat: list[int] = []
    if n_minifat and first_minifat not in (ENDOFCHAIN, FREESECT):
        for n in zincir(first_minifat, fat):
            minifat += struct.unpack_from("<%dI" % (ssz // 4), sektor(n))
    akislar: dict[str, bytes] = {}
    for ad, tur, start, size in girdiler:
        if tur != 2:
            continue
        if size < cutoff:
            parca = b"".join(mini_stream[n * 64:(n + 1) * 64] for n in zincir(start, minifat)) if size else b""
        else:
            parca = b"".join(sektor(n, tam=False) for n in zincir(start, fat))
        if len(parca) < size:  # kesik dosya: akışı kısaltıp "tam" diye vermek yerine bozuk say
            raise CfbHata(f"akış kısa: {ad!r} {len(parca)}/{size} bayt")
        akislar[ad] = parca[:size]
    return akislar


def _cstr(b: bytes, i: int) -> tuple[bytes, int]:
    j = b.index(b"\x00", i)
    return b[i:j], j + 1


def ole10native(akis: bytes) -> tuple[str, bytes]:
    """Packager (\\x01Ole10Native) akışı → (dosya adı, içerik). Biçim dışıysa ValueError."""
    try:
        i = 4  # toplam boy
        i += 2  # bayrak
        etiket, i = _cstr(akis, i)
        _kaynak, i = _cstr(akis, i)
        i += 4  # sabit (0x00030000)
        tlen = struct.unpack_from("<I", akis, i)[0]
        i += 4 + tlen
        dlen = struct.unpack_from("<I", akis, i)[0]
        i += 4
        if dlen > len(akis) - i:
            raise ValueError("içerik boyu akıştan büyük")
        icerik = akis[i:i + dlen]
        ad = etiket.decode("cp1254", "replace")
        # Yeni Packager sürümleri içerikten sonra UTF-16 kopyalar yazar: geçici yol, etiket, kaynak yol.
        j = i + dlen
        try:
            uni = []
            for _ in range(3):
                n = struct.unpack_from("<I", akis, j)[0]
                uni.append(akis[j + 4:j + 4 + 2 * n].decode("utf-16-le"))
                j += 4 + 2 * n
            if uni[1].strip():
                ad = uni[1]
        except (struct.error, UnicodeDecodeError):
            pass
        return ad, icerik
    except (ValueError, struct.error, IndexError) as exc:
        raise ValueError(f"Ole10Native biçimi okunamadı: {exc}") from None


def ooxml_uzanti(data: bytes) -> str | None:
    """Zip ise içeriğe bakıp .docx/.xlsx/.pptx; değilse None."""
    import io
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            adlar = z.namelist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError, EOFError):
        return None
    for onek, uz in (("word/", ".docx"), ("xl/", ".xlsx"), ("ppt/", ".pptx")):
        if any(a.startswith(onek) for a in adlar):
            return uz
    return ".zip"


def gomulu_coz(ad: str, data: bytes) -> tuple[str, bytes, str]:
    """Gömülü parça → (önerilen dosya adı, içerik, tür açıklaması). Tanınmazsa ham içerik + 'TANINMADI'.
    Tek bir bozuk gömülü nesne paketin tamamını düşürmez: beklenmeyen her hata ham kopya + TANINMADI olur."""
    taban = guvenli_ad(ad)
    try:
        return _gomulu_coz(taban, data)
    except Exception as exc:  # noqa: BLE001 — bilinçli geniş: girdi güvenilmez, tek nesne paketi düşürmesin
        return taban, data, f"TANINMADI — çözümlenemedi ({type(exc).__name__}: {exc}); ham kopya"


def _gomulu_coz(taban: str, data: bytes) -> tuple[str, bytes, str]:
    uz = ooxml_uzanti(data)
    if uz:
        return (taban if taban.lower().endswith(uz) else taban + uz), data, f"OOXML paketi ({uz})"
    if data[:8] == CFB_IMZA:
        try:
            akislar = cfb_akislari(data)
        except CfbHata as exc:
            return taban, data, f"TANINMADI — OLE okunamadı ({exc}); ham kopya"
        if "\x01Ole10Native" in akislar:
            try:
                p_ad, icerik = ole10native(akislar["\x01Ole10Native"])
                return guvenli_ad(p_ad, taban + ".bin"), icerik, "OLE paket nesnesi (asıl dosya çıkarıldı)"
            except ValueError as exc:
                return taban, data, f"TANINMADI — {exc}; ham kopya"
        if "Package" in akislar:
            uz2 = ooxml_uzanti(akislar["Package"]) or ".bin"
            return Path(taban).stem + uz2, akislar["Package"], f"OLE içinde OOXML paketi ({uz2})"
        return taban, data, "TANINMADI — OLE akışları: " + ", ".join(sorted(repr(k) for k in akislar)[:8]) + "; ham kopya"
    return taban, data, "doğrudan dosya (ham kopya)"

# ── BÖLÜM: docx ─────────────────────────────────────────────────────────────────────────────────────────────
W_SON = "wordprocessingml/2006/main}"
PARAGRAF_AYRACI = "\x00"  # yalnız bellekte; diske hücrede " ¶ ", paragrafta boşluk olarak yazılır


M_SON = "officeDocument/2006/math}"
A_SON = "drawingml/2006/main}"


def w(tag, ad: str) -> bool:
    """Öğe Word ana ad alanında `ad` mı? (DrawingML `a:t` gibi aynı yerel adlı başka öğeler sayılmaz.)"""
    return isinstance(tag, str) and tag.endswith(W_SON + ad)


def m_(tag, ad: str) -> bool:
    """Öğe Office Math (denklem) ad alanında `ad` mı?"""
    return isinstance(tag, str) and tag.endswith(M_SON + ad)


def _denklem_metni(el) -> str:
    return "".join((x.text or "") for x in el.iter() if m_(x.tag, "t")).replace("\r", " ").replace("\n", " ")


# Metin taşıyan çizim nesneleri: parça adı deseni (tür başına). Bağımsız sayım da AYNI desenle parça bulur ama
# metni ayrı (düzenli ifade) kodla sayar.
NESNE_PARCA = {
    "docx": {"diyagram": re.compile(r"^word/diagrams/data\d*\.xml$"),
             "grafik": re.compile(r"^word/charts/chart(?:Ex)?\d*\.xml$")},
    "xlsx": {"diyagram": re.compile(r"^xl/diagrams/data\d*\.xml$"),
             "grafik": re.compile(r"^xl/charts/chart(?:Ex)?\d*\.xml$"),
             "cizim": re.compile(r"^xl/drawings/drawing\d*\.xml$")},
}
NESNE_ETIKET = {"diyagram": ("D", "SmartArt"), "grafik": ("G", "grafik"), "metin_kutusu": ("K", "metin kutusu")}


def _temiz(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\r", " ").replace("\n", " ")).strip()


def nesne_hucreleri(z: zipfile.ZipFile, parca: str, tur: str) -> list[str]:
    """SmartArt: her DrawingML paragrafı bir hücre · grafik: her yaprak `t`/`v` öğesi (başlık, seri adı, kategori,
    değer) bir hücre. Boş hücre yazılmaz."""
    kok = ET.fromstring(z.read(parca))
    if tur == "diyagram":
        hucreler = ["".join((x.text or "") for x in p.iter() if isinstance(x.tag, str) and x.tag.endswith(A_SON + "t"))
                    for p in kok.iter() if isinstance(p.tag, str) and p.tag.endswith(A_SON + "p")]
    else:
        hucreler = [(x.text or "") for x in kok.iter() if yerel(x.tag) in ("t", "v") and len(x) == 0]
    return [h for h in (_temiz(h) for h in hucreler) if bosluksuz(h)]


def cizim_kutulari(z: zipfile.ZipFile, parca: str) -> list[list[str]]:
    """xlsx çizim parçasındaki metin kutuları: her `txBody` bir kutu, her DrawingML paragrafı bir hücre."""
    kok = ET.fromstring(z.read(parca))
    out = []
    for tb in kok.iter():
        if yerel(tb.tag) != "txBody":
            continue
        hucreler = [_temiz("".join((x.text or "") for x in p.iter() if isinstance(x.tag, str)
                                   and x.tag.endswith(A_SON + "t")))
                    for p in tb.iter() if isinstance(p.tag, str) and p.tag.endswith(A_SON + "p")]
        hucreler = [h for h in hucreler if bosluksuz(h)]
        if hucreler:
            out.append(hucreler)
    return out


def nesne_satiri(c: "Cikti", tur: str, no: int, parca: str, hucreler: list[str] | None) -> None:
    """Metinli nesne = bir KM satırı (hücreler tablo satırı gibi kaçırılır); metinsiz nesne yalnız işaret satırı;
    okunamayan parça (hucreler None) işaret satırında 'metin alınmadı' der — bağımsız sayım metin bulursa FAIL olur."""
    harf, etiket = NESNE_ETIKET[tur]
    isaret = "⟦%s%02d %s: %s⟧" % (harf, no, etiket, parca)
    if hucreler:
        c.satirlar.append("[%s] %s | %s |" % (c.km_yeni(), isaret, " | ".join(_tablo_kacis(h) for h in hucreler)))
    else:
        c.satirlar.append("%s %s" % (isaret, "metin yok" if hucreler is not None else "metin alınmadı (parça okunamadı)"))
    c.nesneler.append(("%s%02d" % (harf, no), etiket, parca))


class Cikti:
    """Çıkarımın bellek içi sonucu; paket diske bundan yazılır, doğrulama ise diskten okur."""

    def __init__(self, tur: str):
        self.tur = tur
        self.satirlar: list[str] = []
        self.km = 0
        self.gorseller: list[tuple[str, str, str]] = []           # (KG id, zip parçası, paket dosyası)
        self.gomululer: list[tuple[str, str, str, bytes, str]] = []  # (KN id, zip parçası, dosya, içerik, tür)
        self.notlar: list[str] = []
        self.sayfalar: list[str] = []
        self.nesneler: list[tuple[str, str, str]] = []  # (D01/G01/K01, etiket, kaynak parçası)

    def km_yeni(self) -> str:
        self.km += 1
        return "KM-%04d" % self.km


def parca_iliskileri(z: zipfile.ZipFile, parca: str) -> dict[str, tuple[str, str]]:
    """rId → (ilişki tipinin son parçası, zip içi hedef yol). Dış hedefler atlanır."""
    klasor, ad = parca.rsplit("/", 1) if "/" in parca else ("", parca)
    rels = (klasor + "/" if klasor else "") + "_rels/" + ad + ".rels"
    try:
        kok = ET.fromstring(z.read(rels))
    except KeyError:
        return {}
    out = {}
    for r in kok:
        if (r.get("TargetMode") or "").lower() == "external":
            continue
        hedef = r.get("Target", "")
        yol = hedef.lstrip("/") if hedef.startswith("/") else os.path.normpath(
            os.path.join(klasor, hedef)).replace("\\", "/")
        out[r.get("Id", "")] = ((r.get("Type") or "").rsplit("/", 1)[-1], yol)
    return out


def stil_seviyeleri(z: zipfile.ZipFile) -> dict[str, int]:
    """Paragraf stil kimliği → başlık seviyesi (1-9). Ad ('heading 2', 'Başlık 2', 'Title') ya da outlineLvl;
    basedOn zinciri izlenir. Türkçe Word'ün 'Balk1' gibi kimlikleri ad üzerinden yakalanır."""
    try:
        kok = ET.fromstring(z.read("word/styles.xml"))
    except KeyError:
        return {}
    ham: dict[str, tuple[int | None, str | None]] = {}
    for st in kok:
        if not w(st.tag, "style") or attr_yerel(st, "type") != "paragraph":
            continue
        sid = attr_yerel(st, "styleId") or ""
        seviye, temel = None, None
        for c in st:
            if w(c.tag, "name"):
                ad = (attr_yerel(c, "val") or "").lower().replace("İ", "i")
                m = re.match(r"^(?:heading|başlık|baslik)\s*(\d)$", ad)
                if m:
                    seviye = int(m.group(1))
                elif ad in ("title", "konu başlığı", "konu basligi"):
                    seviye = 1
            elif w(c.tag, "basedOn"):
                temel = attr_yerel(c, "val")
            elif w(c.tag, "pPr"):
                for o in c:
                    if w(o.tag, "outlineLvl"):
                        v = attr_yerel(o, "val") or ""
                        if v.isdigit() and int(v) < 9 and seviye is None:
                            seviye = int(v) + 1
        ham[sid] = (seviye, temel)
    out: dict[str, int] = {}
    for sid in ham:
        s, adim, cur = None, 0, sid
        while cur in ham and adim < 20:
            if ham[cur][0] is not None:
                s = ham[cur][0]
                break
            cur, adim = ham[cur][1], adim + 1
        if s:
            out[sid] = s
    return out


def _yuru(el, parcalar: list[str], nesneler: list[tuple[str, str]]):
    """Metni ve nesne başvurularını belge sırasıyla toplar; mc:Fallback (yinelenen eski gösterim) atlanır."""
    for c in el:
        t = yerel(c.tag)
        if t == "Fallback" or w(c.tag, "pPr") or w(c.tag, "rPr") or w(c.tag, "instrText") or w(c.tag, "delText"):
            continue
        if w(c.tag, "t"):
            parcalar.append((c.text or "").replace("\r", " ").replace("\n", " "))
            continue
        if m_(c.tag, "oMath"):
            metin = _denklem_metni(c)
            if bosluksuz(metin):
                parcalar.append(" %s %s " % (DENKLEM, metin))
            continue
        if t == "relIds" and attr_yerel(c, "dm"):
            nesneler.append(("diyagram", attr_yerel(c, "dm")))
        elif t == "chart" and attr_yerel(c, "id"):
            nesneler.append(("grafik", attr_yerel(c, "id")))
        if w(c.tag, "tab") or w(c.tag, "br") or w(c.tag, "cr"):
            parcalar.append(" ")
            continue
        if w(c.tag, "p") and any(p.strip() for p in parcalar):
            parcalar.append(PARAGRAF_AYRACI)
        if t == "blip":
            rid = attr_yerel(c, "embed")
            if rid:
                nesneler.append(("gorsel", rid))
        elif t == "imagedata":
            rid = attr_yerel(c, "id")
            if rid:
                nesneler.append(("gorsel", rid))
        elif t == "OLEObject":
            rid = attr_yerel(c, "id")
            if rid:
                nesneler.append(("gomulu", rid))
        _yuru(c, parcalar, nesneler)


def _tablo_kacis(s: str) -> str:
    """Hücre metni: kaynaktaki \\ | ¶ ters bölüyle kaçırılır, sonra paragraf ayracı ¶ olur (sayım ikisini ayırır)."""
    return re.sub(r"([\\|¶])", r"\\\1", s).replace(PARAGRAF_AYRACI, " ¶ ")


def _satirlar(el):
    """Tablonun satırları (sdt/customXml sarmalı içindekiler dahil); iç içe tablonun satırları hariç."""
    for c in el:
        if w(c.tag, "tr"):
            yield c
        elif not w(c.tag, "tbl") and not w(c.tag, "tc"):
            yield from _satirlar(c)


def _hucreler(el):
    for c in el:
        if w(c.tag, "tc"):
            yield c
        elif not w(c.tag, "tbl") and not w(c.tag, "tr"):
            yield from _hucreler(c)


def docx_cikar(z: zipfile.ZipFile) -> Cikti:
    try:
        govde_xml = z.read("word/document.xml")
    except KeyError:
        raise Okunamadi("word/document.xml yok — .docx değil ya da bozuk") from None
    try:
        kok = ET.fromstring(govde_xml)
    except ET.ParseError as exc:
        raise Okunamadi(f"word/document.xml ayrıştırılamadı: {exc}") from None
    govde = next((c for c in kok if w(c.tag, "body")), None)
    if govde is None:
        raise Okunamadi("belge gövdesi (body) yok")
    c = Cikti("docx")
    rels = parca_iliskileri(z, "word/document.xml")
    stiller = stil_seviyeleri(z)
    adlar = z.namelist()

    kg_by = {}
    for i, ad in enumerate(sorted(a for a in adlar if a.startswith("word/media/") and not a.endswith("/")), 1):
        kid = "KG-%02d" % i
        dosya = "%s_%s" % (kid, guvenli_ad(ad))
        c.gorseller.append((kid, ad, dosya))
        kg_by[ad] = (kid, "media/" + dosya)
    gomulu_adlar = sorted(a for a in adlar if a.startswith("word/embeddings/") and not a.endswith("/"))
    gomulu_adlar += sorted({h for tip, h in rels.values() if tip.lower() == "afchunk" and h in adlar})
    kn_by = {}
    for i, ad in enumerate(gomulu_adlar, 1):
        kid = "KN-%02d" % i
        p_ad, icerik, tur = gomulu_coz(ad, z.read(ad))
        dosya = "%s_%s" % (kid, p_ad)
        c.gomululer.append((kid, ad, dosya, icerik, tur))
        kn_by[ad] = (kid, "gomulu/" + dosya)

    nesne_by: dict[str, tuple[str, int]] = {}
    for tur, desen in NESNE_PARCA["docx"].items():
        for i, ad in enumerate(sorted(a for a in adlar if desen.match(a)), 1):
            nesne_by[ad] = (tur, i)
    yazilan_nesne: set[str] = set()

    def nesne_yaz(parca: str) -> None:
        if parca in yazilan_nesne:
            return
        yazilan_nesne.add(parca)
        tur, no = nesne_by[parca]
        try:
            hucreler = nesne_hucreleri(z, parca, tur)
        except ET.ParseError:
            hucreler = None
        nesne_satiri(c, tur, no, parca, hucreler)

    def notlar_metni(nesneler) -> tuple[str, list[str]]:
        """(satır sonu işaretleri, bu satırdan SONRA yazılacak metinli nesne parçaları)."""
        out, sonra = [], []
        for tur, rid in nesneler:
            hedef = rels.get(rid, ("", ""))[1]
            if tur == "gorsel" and hedef in kg_by:
                out.append("⟦%s görsel: %s⟧" % kg_by[hedef])
            elif tur == "gomulu" and hedef in kn_by:
                out.append("⟦%s gömülü: %s⟧" % kn_by[hedef])
            elif tur in ("diyagram", "grafik") and hedef in nesne_by:
                harf, _etiket = NESNE_ETIKET[tur]
                out.append("⟦%s%02d sonraki satırda⟧" % (harf, nesne_by[hedef][1]))
                sonra.append(hedef)
            else:
                out.append("⟦%s başvurusu çözülemedi: %s⟧" % (tur, rid))
        return " ".join(dict.fromkeys(out)), list(dict.fromkeys(sonra))

    sayac = {"tablo": 0}

    def paragraf(p):
        parcalar, nesneler = [], []
        _yuru(p, parcalar, nesneler)
        metin = re.sub(r"\s+", " ", "".join(parcalar).replace(PARAGRAF_AYRACI, " ")).strip()
        ek, sonra = notlar_metni(nesneler)
        seviye, liste = None, False
        ppr = next((x for x in p if w(x.tag, "pPr")), None)
        if ppr is not None:
            for x in ppr:
                if w(x.tag, "pStyle"):
                    seviye = stiller.get(attr_yerel(x, "val") or "")
                elif w(x.tag, "outlineLvl"):
                    v = attr_yerel(x, "val") or ""
                    seviye = int(v) + 1 if v.isdigit() and int(v) < 9 else None
                elif w(x.tag, "numPr"):
                    liste = True
        if metin:
            kid = c.km_yeni()
            if seviye:
                c.satirlar.append("%s [%s] %s%s" % ("#" * min(seviye, 6), kid, metin, (" " + ek) if ek else ""))
            else:
                c.satirlar.append("[%s] %s%s%s" % (kid, "⟦liste⟧ " if liste else "", metin, (" " + ek) if ek else ""))
        elif ek:
            c.satirlar.append(ek)
        for parca in sonra:
            nesne_yaz(parca)

    def tablo(tbl):
        sayac["tablo"] += 1
        tno = sayac["tablo"]
        satirlar = list(_satirlar(tbl))
        ic_ice = any(w(x.tag, "tbl") for tr in satirlar for x in tr.iter())
        c.satirlar.append("")
        c.satirlar.append("**Tablo T%02d** — %d satır%s" % (tno, len(satirlar),
                                                         " (iç içe tablo hücre metnine düzleştirildi)" if ic_ice else ""))
        for sno, tr in enumerate(satirlar, 1):
            hucre_metinleri, nesneler = [], []
            for tc in _hucreler(tr):
                parcalar = []
                _yuru(tc, parcalar, nesneler)
                hucre_metinleri.append(re.sub(r"\s+", " ", "".join(parcalar)).strip())
            ek, sonra = notlar_metni(nesneler)
            if any(bosluksuz(h.replace(PARAGRAF_AYRACI, "")) for h in hucre_metinleri):
                kid = c.km_yeni()
                c.satirlar.append("[%s] ⟦T%02d.S%02d⟧ | %s |%s" % (
                    kid, tno, sno, " | ".join(_tablo_kacis(h) for h in hucre_metinleri), (" " + ek) if ek else ""))
            elif ek:
                c.satirlar.append("⟦T%02d.S%02d⟧ %s" % (tno, sno, ek))
            for parca in sonra:
                nesne_yaz(parca)
        c.satirlar.append("")

    def kapsayici(el):
        for x in el:
            if w(x.tag, "p"):
                paragraf(x)
            elif w(x.tag, "tbl"):
                tablo(x)
            elif w(x.tag, "altChunk"):
                hedef = rels.get(attr_yerel(x, "id") or "", ("", ""))[1]
                c.satirlar.append("⟦%s gömülü (altChunk): %s⟧" % kn_by[hedef] if hedef in kn_by
                                  else "⟦altChunk başvurusu çözülemedi⟧")
            elif w(x.tag, "sectPr") or w(x.tag, "sdtPr") or w(x.tag, "sdtEndPr"):
                continue
            else:
                kapsayici(x)

    kapsayici(govde)
    kalan = [a for a in sorted(nesne_by, key=lambda a: (nesne_by[a][0], nesne_by[a][1])) if a not in yazilan_nesne]
    if kalan:
        c.satirlar += ["", "## Gövdede konumu bulunamayan metin nesneleri (üst/altbilgi ya da başka parçadan bağlı)", ""]
        for parca in kalan:
            nesne_yaz(parca)
    for parca, aciklama in (("word/footnotes.xml", "dipnot"), ("word/endnotes.xml", "son not"),
                            ("word/comments.xml", "yorum")):
        if parca in adlar and re.search(rb"<w:t[ >]", z.read(parca)):
            c.notlar.append(f"{aciklama} parçasında metin var — metin.md'ye ALINMADI (kaynağı Word'de aç)")
    if any(re.match(r"word/(header|footer)\d*\.xml$", a) for a in adlar):
        c.notlar.append("üst/altbilgi metni metin.md'ye alınmadı")
    return c

# ── BÖLÜM: xlsx ─────────────────────────────────────────────────────────────────────────────────────────────
def xlsx_okuyucu():
    """office-excel skill'inin stdlib okuyucusu (aynı template klonunda). Yoksa None → xlsx desteklenmiyor."""
    yol = HERE.parent.parent.parent / "skills" / "office-excel" / "scripts"
    if not (yol / "xlsx_lite.py").is_file():
        return None
    if str(yol) not in sys.path:
        sys.path.insert(0, str(yol))
    try:
        import xlsx_lite  # noqa: WPS433
    except Exception:
        return None
    return xlsx_lite


def _hucre_metni(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def xlsx_cikar(z: zipfile.ZipFile, yol: Path, xl) -> Cikti:
    c = Cikti("xlsx")
    try:
        sayfalar = xl.sheet_parts(z)
    except Exception as exc:
        raise Okunamadi(f"çalışma kitabı okunamadı: {exc}") from None
    for sno, (ad, _parca) in enumerate(sayfalar, 1):
        c.sayfalar.append(ad)
        try:
            _ad, satirlar = xl.read_rows(str(yol), sno)
        except Exception as exc:
            raise Okunamadi(f"sayfa {ad!r} okunamadı: {exc}") from None
        c.satirlar.append("")
        c.satirlar.append("## Sayfa SY%02d: %s" % (sno, ad))
        for rno, satir in enumerate(satirlar, 1):
            hucreler = [_hucre_metni(v).replace("\r", " ").replace("\n", " ") for v in satir]
            if not any(bosluksuz(h) for h in hucreler):
                continue
            c.satirlar.append("[%s] ⟦SY%02d.S%04d⟧ | %s |" % (c.km_yeni(), sno, rno,
                                                          " | ".join(_tablo_kacis(h) for h in hucreler)))
    adlar = z.namelist()
    nesne_basligi = ["", "## Çizim, SmartArt ve grafik metinleri (hangi hücrede durduğu yazılmaz)", ""]
    for tur in ("diyagram", "grafik"):
        for no, parca in enumerate(sorted(a for a in adlar if NESNE_PARCA["xlsx"][tur].match(a)), 1):
            c.satirlar += nesne_basligi
            nesne_basligi = []
            try:
                hucreler = nesne_hucreleri(z, parca, tur)
            except ET.ParseError:
                hucreler = None
            nesne_satiri(c, tur, no, parca, hucreler)
    kutu_no = 0
    for parca in sorted(a for a in adlar if NESNE_PARCA["xlsx"]["cizim"].match(a)):
        try:
            kutular = cizim_kutulari(z, parca)
        except ET.ParseError:
            c.notlar.append("çizim parçası okunamadı: %s — metin kutuları ALINMADI" % parca)
            continue
        for hucreler in kutular:
            kutu_no += 1
            c.satirlar += nesne_basligi
            nesne_basligi = []
            nesne_satiri(c, "metin_kutusu", kutu_no, parca, hucreler)
    for i, ad in enumerate(sorted(a for a in adlar if a.startswith("xl/media/") and not a.endswith("/")), 1):
        kid = "KG-%02d" % i
        c.gorseller.append((kid, ad, "%s_%s" % (kid, guvenli_ad(ad))))
    for i, ad in enumerate(sorted(a for a in adlar if a.startswith("xl/embeddings/") and not a.endswith("/")), 1):
        kid = "KN-%02d" % i
        p_ad, icerik, tur = gomulu_coz(ad, z.read(ad))
        c.gomululer.append((kid, ad, "%s_%s" % (kid, p_ad), icerik, tur))
    if c.gorseller or c.gomululer:
        c.notlar.append("xlsx'te görsel/nesnenin hangi hücrede durduğu metin.md'ye yazılmaz (yalnız dosya olarak çıkar)")
    if any(a.startswith("xl/comments") for a in adlar):
        c.notlar.append("hücre yorumları metin.md'ye ALINMADI")
    return c

# ── BÖLÜM: bağımsız sayım + paket yazımı + doğrulama ──────────────────────────────────────────────────────────
# Bağımsız sayım çıkarım kodunu KULLANMAZ: gövdeyi kapsayıcı yürüyüşüyle değil ata haritasıyla sayar; nesne
# parçalarının (SmartArt, grafik, çizim) metnini ElementTree yerine düzenli ifadeyle sayar. Çıkarım bir kapsayıcıyı
# ya da nesneyi atlarsa iki sayı ayrılır ve paket FAIL olur.
SAYIM_ADLARI = [("km", "kaynak maddesi (KM: başlık + paragraf + tablo satırı + metinli nesne)"), ("baslik", "başlık"),
                ("tablo", "tablo"), ("tablo_satiri", "tablo satırı (metinli)"),
                ("karakter", "metin karakteri (boşluksuz; xlsx'te yalnız metin hücreleri)"),
                ("denklem", "denklem"), ("sayfa", "çalışma sayfası"), ("diyagram", "SmartArt (D)"),
                ("grafik", "grafik (G)"), ("metin_kutusu", "çizim metin kutusu (K)"),
                ("nesne_karakteri", "nesne metni karakteri (D/G/K, boşluksuz)"),
                ("gorsel", "görsel (KG)"), ("gomulu", "gömülü nesne (KN)")]
_YAPRAK = r"<(?:\w+:)?(%s)(?:\s[^<>]*)?>([^<]*)</(?:\w+:)?\1>"
_YAPRAK_T = re.compile(_YAPRAK % "t")
_YAPRAK_TV = re.compile(_YAPRAK % "t|v")
_TXBODY = re.compile(r"<((?:\w+:)?txBody)\b.*?</\1>", re.S)


def _yaprak_karakteri(xml: str, desen: re.Pattern) -> int:
    return sum(bosluksuz(html.unescape(m.group(2))) for m in desen.finditer(xml))


def _nesne_say(z: zipfile.ZipFile, tur: str) -> dict[str, int]:
    """SmartArt / grafik / (xlsx) çizim metin kutusu: adet + metinli olanlar (KM) + metin karakteri."""
    s = {"diyagram": 0, "grafik": 0, "nesne_km": 0, "nesne_karakteri": 0}
    if tur == "xlsx":
        s["metin_kutusu"] = 0
    for ad in z.namelist():
        for anahtar, desen in NESNE_PARCA[tur].items():
            if not desen.match(ad):
                continue
            xml = z.read(ad).decode("utf-8", "replace")
            if anahtar == "cizim":
                for blok in _TXBODY.finditer(xml):
                    n = _yaprak_karakteri(blok.group(0), _YAPRAK_T)
                    if n:
                        s["metin_kutusu"] += 1
                        s["nesne_km"] += 1
                        s["nesne_karakteri"] += n
                continue
            s[anahtar] += 1
            n = _yaprak_karakteri(xml, _YAPRAK_T if anahtar == "diyagram" else _YAPRAK_TV)
            s["nesne_karakteri"] += n
            s["nesne_km"] += 1 if n else 0
    return s


def _afchunk_hedefleri(z: zipfile.ZipFile) -> set[str]:
    try:
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8", "replace")
    except KeyError:
        return set()
    out = set()
    for m in re.finditer(r"<(?:\w+:)?Relationship\b([^>]*)/?>", rels):
        a = m.group(1)
        tip = re.search(r'Type="([^"]*)"', a)
        hed = re.search(r'Target="([^"]*)"', a)
        if tip and hed and tip.group(1).lower().endswith("/afchunk") and 'TargetMode="External"' not in a:
            h = hed.group(1)
            yol = h.lstrip("/") if h.startswith("/") else os.path.normpath("word/" + h).replace("\\", "/")
            if yol in z.namelist():
                out.add(yol)
    return out


def bagimsiz_docx(z: zipfile.ZipFile) -> dict[str, int]:
    kok = ET.fromstring(z.read("word/document.xml"))
    ebeveyn = {ch: par for par in kok.iter() for ch in par}

    def atalar(el):
        while el in ebeveyn:
            el = ebeveyn[el]
            yield el

    def fallbackta(el) -> bool:
        return any(yerel(a.tag) == "Fallback" for a in atalar(el))

    # Gövde metni: Word metni + denklem metni (ikisi de satırın metnine girer).
    metinler = [t for t in kok.iter() if (w(t.tag, "t") or m_(t.tag, "t")) and not fallbackta(t)]
    dolu = {t for t in metinler if (t.text or "").strip()}
    dolu_atalar: set = set()
    for t in dolu:
        dolu_atalar.update(atalar(t))
    stiller = stil_seviyeleri(z)
    s = {"km": 0, "baslik": 0, "tablo": 0, "tablo_satiri": 0, "denklem": 0,
         "karakter": sum(bosluksuz(t.text or "") for t in metinler)}
    for el in kok.iter():
        if w(el.tag, "p"):
            if any(w(a.tag, "p") or w(a.tag, "tbl") for a in atalar(el)) or el not in dolu_atalar:
                continue
            s["km"] += 1
            seviye = None
            for x in el.iter():
                if w(x.tag, "pStyle") and ebeveyn.get(ebeveyn.get(x)) is el:
                    seviye = stiller.get(attr_yerel(x, "val") or "")
                if w(x.tag, "outlineLvl") and ebeveyn.get(ebeveyn.get(x)) is el:
                    v = attr_yerel(x, "val") or ""
                    seviye = int(v) + 1 if v.isdigit() and int(v) < 9 else None
            if seviye:
                s["baslik"] += 1
        elif w(el.tag, "tbl"):
            # Paragraf içindeki tablo (metin kutusu) paragrafın satırına düzleşir: tablo/satır sayılmaz.
            if not any(w(a.tag, "tbl") or w(a.tag, "p") for a in atalar(el)):
                s["tablo"] += 1
        elif w(el.tag, "tr"):
            ust = list(atalar(el))
            if sum(1 for a in ust if w(a.tag, "tbl")) == 1 and not any(w(a.tag, "p") for a in ust) \
                    and el in dolu_atalar:
                s["tablo_satiri"] += 1
                s["km"] += 1
        elif m_(el.tag, "oMath") and not fallbackta(el) and not any(m_(a.tag, "oMath") for a in atalar(el)):
            if any(bosluksuz(x.text or "") for x in el.iter() if m_(x.tag, "t")):
                s["denklem"] += 1
    nesne = _nesne_say(z, "docx")
    s["km"] += nesne.pop("nesne_km")
    s.update(nesne)
    adlar = z.namelist()
    s["gorsel"] = sum(1 for a in adlar if a.startswith("word/media/") and not a.endswith("/"))
    s["gomulu"] = sum(1 for a in adlar if a.startswith("word/embeddings/") and not a.endswith("/")) \
        + len(_afchunk_hedefleri(z))
    return s


def _xml_metni(parca: str) -> str:
    parca = re.sub(r"<(?:\w+:)?rPh\b.*?</(?:\w+:)?rPh>", "", parca, flags=re.S)
    return html.unescape("".join(re.findall(r"<(?:\w+:)?t\b[^>]*>(.*?)</(?:\w+:)?t>", parca, flags=re.S)))


def _sutun_no(ref: str) -> int | None:
    m = re.match(r"^([A-Z]+)\d", ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def bagimsiz_xlsx(z: zipfile.ZipFile) -> tuple[dict[str, int], set[tuple[int, int, int]]]:
    """Döner: (sayım, metin hücresi maskesi {(sayfa no, Excel satır no, sütun sırası)}). Sayfa sırası workbook.xml'deki
    `sheet` sırasıdır. Karakter yalnız metin hücrelerinden (paylaşılan dizge, satır içi dizge, formül dizgesi) sayılır;
    sayı/tarih/mantıksal hücrenin gösterimi çıkarımda biçimlendiği için sayılmaz — maske diskteki pakette aynı
    konumdaki hücreleri seçer."""
    def oku(ad):
        try:
            return z.read(ad).decode("utf-8", "replace")
        except KeyError:
            return ""
    rid_yol, paylasilan_yolu = {}, None
    for m in re.finditer(r"<(?:\w+:)?Relationship\b([^>]*)/?>", oku("xl/_rels/workbook.xml.rels")):
        tip = re.search(r'Type="([^"]*)"', m.group(1))
        hed = re.search(r'Target="([^"]*)"', m.group(1))
        rid = re.search(r'\bId="([^"]*)"', m.group(1))
        if not (tip and hed):
            continue
        h = hed.group(1)
        yol = h.lstrip("/") if h.startswith("/") else os.path.normpath("xl/" + h).replace("\\", "/")
        if tip.group(1).endswith("/worksheet") and rid:
            rid_yol[rid.group(1)] = yol
        elif tip.group(1).endswith("/sharedStrings"):
            paylasilan_yolu = yol
    sayfa_yollari = []
    for m in re.finditer(r"<(?:\w+:)?sheet\b([^>]*)/?>", oku("xl/workbook.xml")):
        rid = re.search(r'\b(?:\w+:)?id="([^"]*)"', m.group(1))
        if rid and rid.group(1) in rid_yol:
            sayfa_yollari.append(rid_yol[rid.group(1)])
    paylasilan = [_xml_metni(si) for si in re.findall(r"<(?:\w+:)?si\b[^>]*>(.*?)</(?:\w+:)?si>",
                                                     oku(paylasilan_yolu) if paylasilan_yolu else "", flags=re.S)]
    km, karakter, maske = 0, 0, set()
    for sno, yol in enumerate(sayfa_yollari, 1):
        rno_sira = 0
        for r_attr, satir in re.findall(r"<(?:\w+:)?row\b([^>]*?)(?<!/)>(.*?)</(?:\w+:)?row>", oku(yol), flags=re.S):
            rm = re.search(r'\br="(\d+)"', r_attr)
            rno = int(rm.group(1)) if rm else rno_sira + 1
            rno_sira = rno
            dolu, sira = False, 0
            for attrs, ic in re.findall(r"<(?:\w+:)?c\b([^>]*?)(?:/>|>(.*?)</(?:\w+:)?c>)", satir, flags=re.S):
                ref = re.search(r'\br="([^"]*)"', attrs)
                sno_c = _sutun_no(ref.group(1)) if ref else None
                sira = sno_c if sno_c is not None else sira
                tur = re.search(r'\bt="([^"]*)"', attrs)
                tur = tur.group(1) if tur else "n"
                v = re.search(r"<(?:\w+:)?v\b[^>]*>(.*?)</(?:\w+:)?v>", ic or "", flags=re.S)
                v = html.unescape(v.group(1)) if v else ""
                if tur == "s":
                    deger = paylasilan[int(v)] if v.strip().isdigit() and int(v) < len(paylasilan) else ""
                elif tur == "inlineStr":
                    deger = _xml_metni(ic or "")
                else:
                    deger = v
                if tur in ("s", "inlineStr", "str"):
                    karakter += bosluksuz(deger)
                    maske.add((sno, rno, sira))
                if deger.strip():
                    dolu = True
                sira += 1
            km += 1 if dolu else 0
    adlar = z.namelist()
    s = {"km": km, "karakter": karakter, "sayfa": len(sayfa_yollari),
         "gorsel": sum(1 for a in adlar if a.startswith("xl/media/") and not a.endswith("/")),
         "gomulu": sum(1 for a in adlar if a.startswith("xl/embeddings/") and not a.endswith("/"))}
    nesne = _nesne_say(z, "xlsx")
    s["km"] += nesne.pop("nesne_km")
    s.update(nesne)
    return s, maske


def _satir_karakteri(govde: str, tablo_satiri: bool) -> int:
    govde = NOT_RE.sub("", govde)
    if tablo_satiri:
        govde = re.sub(r"\\(.)|[|¶]", lambda m: m.group(1) or "", govde)
    return bosluksuz(govde)


def _hucre_bol(govde: str) -> list[str]:
    """`| a | b\\|c |` → ['a', 'b|c'] — kaçışı çözer; `|` yalnız kaçırılmamışsa ayraçtır."""
    s = govde.strip()
    if s.startswith("|"):
        s = s[1:]
    hucreler, cur, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            cur.append(s[i + 1])
            i += 2
            continue
        if ch == "|":
            hucreler.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if "".join(cur).strip():
        hucreler.append("".join(cur))
    return [h.strip() for h in hucreler]


def diskten_say(paket: Path, tur: str, maske: set | None = None) -> tuple[dict[str, int], list[str]]:
    """Paketi DİSKTEN okuyup sayar (bellekteki çıkarım sonucuna bakmaz). Döner: (sayım, biçim sorunları).
    xlsx'te karakter yalnız `maske` (bağımsız sayımın metin hücresi konumları) verilirse sayılır."""
    sorunlar: list[str] = []
    metin = (paket / "metin.md").read_text(encoding="utf-8")
    s = {"km": 0, "baslik": 0, "tablo": 0, "tablo_satiri": 0, "karakter": 0, "denklem": 0, "sayfa": 0,
         "diyagram": 0, "grafik": 0, "metin_kutusu": 0, "nesne_karakteri": 0}
    beklenen = 1
    for satir in metin.splitlines():
        if re.match(r"^\*\*Tablo T\d+\*\* ", satir):
            s["tablo"] += 1
        if re.match(r"^## Sayfa SY\d+: ", satir):
            s["sayfa"] += 1
        m = KM_RE.match(satir)
        govde = satir[m.end():] if m else satir
        om = NESNE_RE.match(govde)
        if om:
            s[NESNE_ANAHTAR[om.group(2)]] += 1
        if not m:
            continue
        s["km"] += 1
        if m.group(2) != "KM-%04d" % beklenen:
            sorunlar.append(f"KM sırası bozuk: {m.group(2)} (beklenen KM-{beklenen:04d})")
        beklenen = int(m.group(2)[3:]) + 1
        if m.group(1):
            s["baslik"] += 1
        if om:
            s["nesne_karakteri"] += _satir_karakteri(govde[om.end():], True)
            continue
        s["denklem"] += govde.count(DENKLEM)
        rm = SATIR_RE.match(govde)
        if rm and rm.group(1).startswith("T"):
            s["tablo_satiri"] += 1
        if rm and rm.group(2):  # xlsx satırı: yalnız metin hücresi konumları
            if maske is not None:
                sno, rno = int(rm.group(2)), int(rm.group(3))
                s["karakter"] += sum(bosluksuz(h) for i, h in enumerate(_hucre_bol(govde[rm.end():]))
                                     if (sno, rno, i) in maske)
            continue
        s["karakter"] += _satir_karakteri(govde[rm.end():] if rm else govde, bool(rm))
    for klasor, anahtar in (("media", "gorsel"), ("gomulu", "gomulu")):
        d = paket / klasor
        s[anahtar] = sum(1 for p in d.iterdir() if p.is_file()) if d.is_dir() else 0
    return s, sorunlar


def karsilastir(kaynak: dict[str, int], paket: dict[str, int]) -> list[str]:
    return ["%s: kaynak %d ≠ paket %d" % (ad, kaynak[k], paket.get(k, 0))
            for k, ad in SAYIM_ADLARI if k in kaynak and kaynak[k] != paket.get(k, 0)]


def boyut_denetle(z: zipfile.ZipFile) -> None:
    """Zip başlığındaki açılmış boyları sınırla (MAX_UYE / MAX_TOPLAM); aşan girdi Okunamadi (çıkış 2)."""
    toplam = 0
    for bilgi in z.infolist():
        if bilgi.file_size > MAX_UYE:
            raise Okunamadi("boyut sınırı: %s açılınca %d bayt (sınır %d) — çıkarım yapılmadı"
                            % (bilgi.filename, bilgi.file_size, MAX_UYE))
        toplam += bilgi.file_size
    if toplam > MAX_TOPLAM:
        raise Okunamadi("boyut sınırı: açılmış toplam %d bayt (sınır %d) — çıkarım yapılmadı" % (toplam, MAX_TOPLAM))


def varsayilan_id(kaynak: Path, veri: bytes) -> str:
    kok = re.sub(r"[^A-Za-z0-9ÇĞİÖŞÜçğıöşü_-]+", "-", kaynak.stem).strip("-")[:40] or "kaynak"
    return "%s-%s" % (kok, ozet(veri)[:8])


def paketi_yaz(c: Cikti, z: zipfile.ZipFile, kaynak: Path, veri: bytes, hedef: Path) -> None:
    (hedef / "media").mkdir(parents=True, exist_ok=True)
    (hedef / "gomulu").mkdir(parents=True, exist_ok=True)
    bas = ["<!-- kaynak_paketi.py MEKANİK çıkarım: %s (sha256 %s). Elle ya da modelle yeniden yazılmaz; "
           "işaretler INDEX.md 'Nasıl okunur' bölümünde. -->" % (kaynak.name, ozet(veri)[:16]), ""]
    (hedef / "metin.md").write_text("\n".join(bas + c.satirlar).rstrip() + "\n", encoding="utf-8")
    for _kid, ad, dosya in c.gorseller:
        (hedef / "media" / dosya).write_bytes(z.read(ad))
    for _kid, _ad, dosya, icerik, _tur in c.gomululer:
        (hedef / "gomulu" / dosya).write_bytes(icerik)


def index_yaz(c: Cikti, kaynak: Path, veri: bytes, hedef: Path, kaynak_say: dict, paket_say: dict,
              farklar: list[str]) -> None:
    sonuc = "PASS" if not farklar else "FAIL"
    L = ["# Kaynak paketi — %s" % kaynak.name, "",
         "> Mekanik çıkarım (`kaynak_paketi.py cikar`). Bu klasördeki metin model tarafından YENİDEN YAZILMAZ, "
         "özetlenip kaynağın yerine konmaz. Alt ajana ya da inceleyiciye ikili kaynağın değil bu klasörün yolu verilir.",
         "", "- Kaynak: `%s` · %d bayt · sha256 `%s` · tür %s" % (kaynak.name, len(veri), ozet(veri), c.tur),
         "- Paket: `%s`" % hedef.as_posix(),
         "- DOĞRULAMA: **%s** — kaynağın bağımsız sayımı ↔ diskteki paket%s" % (
             sonuc, "" if not farklar else " (EŞİT DEĞİL: " + "; ".join(farklar) + ") — bu paketi KULLANMA"),
         "", "## Sayım", "", "| Ölçü | Kaynak (bağımsız) | Paket (diskten) | Durum |", "|---|---|---|---|"]
    for k, ad in SAYIM_ADLARI:
        if k in kaynak_say:
            L.append("| %s | %d | %d | %s |" % (ad, kaynak_say[k], paket_say.get(k, 0),
                                               "eşit" if kaynak_say[k] == paket_say.get(k, 0) else "**FARKLI**"))
    L += ["", "## Dosyalar", "", "- `metin.md` — kaynak maddeleri %s" % (
        "KM-0001…KM-%04d" % c.km if c.km else "yok"), ""]
    if c.sayfalar:
        L += ["Sayfalar: " + " · ".join("SY%02d = %s" % (i, a) for i, a in enumerate(c.sayfalar, 1)), ""]
    if c.gorseller or c.gomululer:
        L += ["| Kimlik | Kaynak parçası | Paket dosyası | Tür |", "|---|---|---|---|"]
        L += ["| %s | `%s` | `media/%s` | görsel |" % (k, a, d) for k, a, d in c.gorseller]
        L += ["| %s | `%s` | `gomulu/%s` | %s |" % (k, a, d, t) for k, a, d, _i, t in c.gomululer]
        L.append("")
    if c.nesneler:
        L += ["Metin taşıyan çizim nesneleri (metni metin.md'de kendi KM satırında): " + " · ".join(
            "%s %s `%s`" % n for n in c.nesneler), ""]
    tanınmayan = [k for k, _a, _d, _i, t in c.gomululer if t.startswith("TANINMADI")]
    L += ["## Kapsam dışı / notlar", ""]
    L += ["- " + n for n in c.notlar] or ["- (yok)"]
    if tanınmayan:
        L.append("- TANINMAYAN gömülü nesne: %s — ham kopyalandı, içeriği kullanıcıya sor" % ", ".join(tanınmayan))
    L += ["- Otomatik numaralar (başlık/liste numarası) Word'ün ürettiği metindir, metin.md'de yoktur.", "",
          "## Nasıl okunur", "",
          "- Her `[KM-nnnn]` satırı bir kaynak maddesidir; `#` ile başlayan satır başlıktır.",
          "- `⟦T01.S03⟧ | a | b |` = tablo 1, satır 3; hücreler `|`, hücre içi paragraf `¶`; hücredeki gerçek `|`, `¶`, "
          "ters bölü ters bölüyle kaçırılır. xlsx'te `⟦SY01.S0003⟧` = sayfa 1, Excel satırı 3.",
          "- `⟦…⟧` paketin eklediği işarettir (görsel/gömülü nesnenin konumu, liste öğesi, `⟦denklem⟧`); kaynak metni "
          "değildir. `⟦D01 SmartArt: …⟧ | a | b |` = SmartArt'ın paragrafları, `⟦G01 grafik: …⟧` = grafiğin başlık, "
          "seri, kategori ve değer metni, `⟦K01 metin kutusu: …⟧` = xlsx çizimindeki metin kutusu.",
          "- Gömülü HTML prototip tarayıcıda açılabilir; ekran görüntüsü `capture_kd_screens.js` ile `file://` "
          "adresinden çekilebilir.",
          "- İzlenebilirlik: FS yazılırken bu kimliklerle iz tablosu kurulur — paketin yanında DEĞİL, git'te izlenen "
          "`<source_root>/<MODÜL>/<PAKET>/ref_docs/iz-<belge no>.md` — ve `kaynak_paketi.py iz` ile denetlenir "
          "(`traceability.md` §2-B). Tablonun başına kaynağın adı ve sha256'sı yazılır: paket bu klasörde git dışıdır, "
          "aynı kaynaktan `cikar` ile aynı kimliklerle yeniden üretilir."]
    (hedef / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    meta = {"surum": 1, "kaynak": {"ad": kaynak.name, "boyut": len(veri), "sha256": ozet(veri), "tur": c.tur},
            "km_toplam": c.km, "kg": [k for k, _a, _d in c.gorseller], "kn": [k for k, *_r in c.gomululer],
            "sayim": {"kaynak": kaynak_say, "paket": paket_say}, "dogrulama": {"sonuc": sonuc, "farklar": farklar},
            "gomulu": [{"kimlik": k, "parca": a, "dosya": "gomulu/" + d, "tur": t} for k, a, d, _i, t in c.gomululer],
            "nesne": [{"kimlik": k, "tur": t, "parca": a} for k, t, a in c.nesneler]}
    (hedef / "paket.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

# ── BÖLÜM: iz denetimi ────────────────────────────────────────────────────────────────────────────────────────
MADDE_RE = re.compile(r"\b(K[MGN])-(\d+)(?:\s*(?:\.\.|…|–|—)\s*(?:K[MGN]-)?(\d+))?\b")
GEREKSINIM_RE = re.compile(r"\b(?:FR|KR)-\d{3}\b")
SHA_RE = re.compile(r"\bsha256\W{0,3}([0-9a-fA-F]{16,64})\b")


def _norm(s: str) -> str:
    s = s.replace("İ", "i").replace("I", "ı").lower()
    return s.translate(str.maketrans("ışğüöç", "isguoc"))


def _hucreler_md(satir: str) -> list[str]:
    govde = satir.strip()
    if govde.startswith("|"):
        govde = govde[1:]
    if govde.endswith("|") and not govde.endswith("\\|"):
        govde = govde[:-1]
    return [h.strip() for h in re.split(r"(?<!\\)\|", govde)]


def iz_denetle(paket: Path, tablo: Path, belgeler: list[Path]) -> tuple[int, list[str]]:
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from doc_equivalence_check import ids as belge_kimlikleri  # aynı klasör; kimlik desenleri tek yerde

    L: list[str] = [SCOPE_IZ]
    try:
        meta = json.loads((paket / "paket.json").read_text(encoding="utf-8"))
        tablo_metni = tablo.read_text(encoding="utf-8")
        belge_metni = "\n".join(p.read_text(encoding="utf-8") for p in belgeler)
        disk, _sorun = diskten_say(paket, meta.get("kaynak", {}).get("tur", ""))
    except (OSError, ValueError) as exc:
        raise Okunamadi(str(exc)) from None
    fail: list[str] = []
    uyari: list[str] = []
    if meta.get("dogrulama", {}).get("sonuc") != "PASS":
        fail.append("paketin kendi doğrulaması PASS değil — önce paketi yeniden çıkar")
    if disk["km"] != meta.get("km_toplam"):
        fail.append("metin.md'deki KM sayısı (%d) paket.json ile (%s) uyuşmuyor — paket elle değiştirilmiş"
                    % (disk["km"], meta.get("km_toplam")))
    beklenen = {("KM", i) for i in range(1, int(meta.get("km_toplam") or 0) + 1)}
    beklenen |= {(k[:2], int(k[3:])) for k in meta.get("kg", []) + meta.get("kn", [])}
    belge_ids = belge_kimlikleri(belge_metni)
    kapsanan: dict[tuple[str, int], list[int]] = {}
    hayalet, bos, taninmayan, belgede_yok, gerekcesiz, elle = [], [], [], [], [], []
    anilan_ids: set[str] = set()
    satir_say = 0
    for no, satir in enumerate(tablo_metni.splitlines(), 1):
        if not satir.strip().startswith("|") or re.match(r"^\s*\|[\s:|-]+\|?\s*$", satir):
            continue
        h = _hucreler_md(satir)
        maddeler = []
        for m in MADDE_RE.finditer(h[0]):
            bas = int(m.group(2))
            son = int(m.group(3)) if m.group(3) else bas
            maddeler += [(m.group(1), i) for i in range(bas, son + 1)] if son >= bas else [(m.group(1), bas)]
        if not maddeler:
            continue  # başlık satırı
        satir_say += 1
        for md in maddeler:
            kapsanan.setdefault(md, []).append(no)
            if md not in beklenen:
                hayalet.append("%s-%s (satır %d)" % (md[0], md[1], no))
        esleme = h[1] if len(h) > 1 else ""
        notu = h[2] if len(h) > 2 else ""
        n = _norm(esleme)
        if not n or n in ("-", "—", "?"):
            bos.append("satır %d: %s" % (no, h[0]))
        elif re.match(r"^bilgi\b", n):
            elle.append("satır %d BİLGİ: %s" % (no, h[0]))
        elif re.match(r"^kapsam[- ]?disi\b", n):
            elle.append("satır %d KAPSAM-DIŞI: %s" % (no, h[0]))
            if not notu.strip(" -—"):
                gerekcesiz.append("satır %d: %s" % (no, h[0]))
        else:
            ids = belge_kimlikleri(esleme)
            if not ids:
                taninmayan.append("satır %d: %r" % (no, esleme))
            anilan_ids |= ids
            for i in sorted(ids - belge_ids):
                belgede_yok.append("%s (satır %d)" % (i, no))
    kaynak_bilgi = meta.get("kaynak", {})
    sha = str(kaynak_bilgi.get("sha256", "")).lower()
    sha_tabloda = [x.lower() for x in SHA_RE.findall(tablo_metni)]
    sha_yanlis = ["tablo: %s · paket: %s" % (", ".join(sha_tabloda), sha[:16])] \
        if sha_tabloda and not any(sha.startswith(x) for x in sha_tabloda) else []
    sha_yok = ["tablonun başına `Kaynak: %s · sha256 %s` satırını yaz" % (kaynak_bilgi.get("ad", "?"), sha[:16])] \
        if not sha_tabloda else []
    bos_paket = ["paket 0 kaynak maddesi taşıyor — kaynak gerçekten boş mu? INDEX.md kapsam notlarına bak"] \
        if not beklenen else []
    eksik = sorted(beklenen - set(kapsanan))
    cift = {md: s for md, s in kapsanan.items() if len(s) > 1}
    kaynaksiz = sorted(set(GEREKSINIM_RE.findall(belge_metni)) - anilan_ids)

    def fmt(md):
        return "%s-%0*d" % (md[0], 4 if md[0] == "KM" else 2, md[1])

    L.append("## İz denetimi — paket `%s` · tablo `%s` · belge %s" % (
        paket.as_posix(), tablo.as_posix(), ", ".join("`%s`" % p.as_posix() for p in belgeler)))
    L.append("kaynak: %s · sha256 %s" % (kaynak_bilgi.get("ad", "?"), sha[:16]))
    L.append("paket maddeleri: %d (KM %d · KG %d · KN %d) · madde anan tablo satırı: %d · kapsanan: %d/%d" % (
        len(beklenen), meta.get("km_toplam") or 0, len(meta.get("kg", [])), len(meta.get("kn", [])), satir_say,
        len(beklenen & set(kapsanan)), len(beklenen)))
    for baslik, liste, sinif in (
            ("EKSİK — tabloda olmayan kaynak maddesi", [fmt(m) for m in eksik], fail),
            ("HAYALET — pakette olmayan madde", hayalet, fail),
            ("BOŞ EŞLEME", bos, fail),
            ("TANINMAYAN EŞLEME — ne belge kimliği ne BİLGİ/KAPSAM-DIŞI", taninmayan, fail),
            ("BELGEDE YOK — eşlenen kimlik belgede geçmiyor", belgede_yok, fail),
            ("KAPSAM-DIŞI GEREKÇESİZ — not sütunu boş", gerekcesiz, fail),
            ("BAŞKA KAYNAĞIN TABLOSU — tablodaki sha256 paketin kaynağıyla uyuşmuyor", sha_yanlis, fail),
            ("UYARI boş paket", bos_paket, uyari),
            ("UYARI tabloda kaynak sha256'sı yok — iz hangi kaynağa ait olduğunu söylemiyor", sha_yok, uyari),
            ("UYARI çift eşleme — aynı madde birden çok satırda",
             ["%s (satır %s)" % (fmt(m), ", ".join(map(str, s))) for m, s in sorted(cift.items())], uyari),
            ("UYARI kaynaksız gereksinim — belgede var, tabloda anılmıyor (danışman önerisi mi? gerekçesi 11-A/EK'te mi?)",
             kaynaksiz, uyari)):
        L.append("%s: %d" % (baslik, len(liste)))
        for x in liste[:200]:
            L.append("  - %s" % x)
        if liste:
            sinif.append(baslik)
    L.append("İNCELEYİCİNİN ELLE OKUYACAĞI (BİLGİ / KAPSAM-DIŞI işaretli satırlar — madde metni metin.md'de): %d" % len(elle))
    for x in elle[:200]:
        L.append("  - %s" % x)
    for f in fail:
        if f.startswith(("paket", "metin.md")):
            L.append("FAIL: " + f)
    L.append("SONUÇ: " + ("PASS — her kaynak maddesi bir satırda, eşlemeler belgede var (anlamca doğruluk ölçülmedi)"
                          if not fail else "FAIL — yukarıdaki listeler kapatılmadan inceleme bu tabloya dayanamaz"))
    return (0 if not fail else 1), L

# ── BÖLÜM: main ───────────────────────────────────────────────────────────────────────────────────────────────
def cikar(a: argparse.Namespace) -> int:
    print(SCOPE_CIKAR)
    kaynak = Path(a.kaynak)
    uz = kaynak.suffix.lower()
    if uz not in DESTEKLENEN:
        neden = DESTEKLENMEYEN_NEDEN.get(uz, "bu uzantı için okuyucu yok")
        print(f"DESTEKLENMİYOR: {kaynak.name} ({uz or 'uzantısız'}) — {neden}. Desteklenen: {', '.join(DESTEKLENEN)}. "
              "Kullanıcıdan kaynağın .docx/.xlsx hâlini iste. Metni modelle yeniden yazarak paket ÜRETME.")
        return 3
    try:
        veri = kaynak.read_bytes()
    except OSError as exc:
        print(f"[ÖLÇÜLEMEDİ] {kaynak}: {exc}", file=sys.stderr)
        return 2
    import io
    try:
        z = zipfile.ZipFile(io.BytesIO(veri))
    except zipfile.BadZipFile:
        print(f"[ÖLÇÜLEMEDİ] {kaynak.name}: zip değil — bozuk ya da uzantısı yanlış (eski .doc/.xls olabilir)",
              file=sys.stderr)
        return 2
    maske = None
    try:
        boyut_denetle(z)
        if uz in (".xlsx", ".xlsm"):
            xl = xlsx_okuyucu()
            if xl is None:
                print("DESTEKLENMİYOR: xlsx okuyucusu (skills/office-excel/scripts/xlsx_lite.py) bu klonda yok.")
                return 3
            c = xlsx_cikar(z, kaynak, xl)
            kaynak_say, maske = bagimsiz_xlsx(z)
        else:
            c = docx_cikar(z)
            kaynak_say = bagimsiz_docx(z)
    except Okunamadi as exc:
        print(f"[ÖLÇÜLEMEDİ] {kaynak.name}: {exc}", file=sys.stderr)
        return 2
    kok = Path(a.hedef_kok) if a.hedef_kok else Path.cwd() / ".axet-code" / "tmp"
    hedef = (kok / guvenli_ad(a.id or varsayilan_id(kaynak, veri), "kaynak")).resolve()
    paketi_yaz(c, z, kaynak, veri, hedef)
    paket_say, sorunlar = diskten_say(hedef, c.tur, maske)
    farklar = karsilastir(kaynak_say, paket_say) + sorunlar
    index_yaz(c, kaynak, veri, hedef, kaynak_say, paket_say, farklar)
    print(f"PAKET: {hedef.as_posix()}")
    for k, ad in SAYIM_ADLARI:
        if k in kaynak_say:
            print("  %-45s kaynak %6d · paket %6d%s" % (ad, kaynak_say[k], paket_say.get(k, 0),
                                                       "" if kaynak_say[k] == paket_say.get(k, 0) else "  ← FARKLI"))
    for kid, _ad, dosya, _i, tur in c.gomululer:
        print(f"  {kid}: gomulu/{dosya} — {tur}")
    for kid, etiket, parca in c.nesneler:
        print(f"  {kid}: {etiket} — {parca} (metni metin.md'de)")
    try:
        hedef.relative_to(Path.cwd().resolve())
    except ValueError:
        print("UYARI: paket çalışma dizini DIŞINDA — alt ajanın dış okuması izin sorusunda asılı kalabilir; "
              "brife proje içindeki bir yol ver.")
    if farklar:
        print("DOĞRULAMA: FAIL — " + "; ".join(farklar) + ". Bu paketi brife/yazıma KAYNAK olarak verme.")
        return 1
    print(f"DOĞRULAMA: PASS. Yazıma ve brife verilecek yol: {(hedef / 'INDEX.md').as_posix()}")
    return 0


def iz(a: argparse.Namespace) -> int:
    try:
        rc, satirlar = iz_denetle(Path(a.paket), Path(a.tablo), [Path(b) for b in a.belge])
    except Okunamadi as exc:
        print(SCOPE_IZ)
        print(f"[ÖLÇÜLEMEDİ] {exc} — bu 'PASS' ANLAMINA GELMEZ.", file=sys.stderr)
        return 2
    print("\n".join(satirlar))
    return rc


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="İkili kaynak belgeden mekanik kaynak paketi + kaynak→belge iz denetimi")
    alt = ap.add_subparsers(dest="komut", required=True)
    c = alt.add_parser("cikar", help="kaynak paketi üret")
    c.add_argument("kaynak")
    c.add_argument("--hedef-kok", default=None, help="varsayılan: <çalışma dizini>/.axet-code/tmp")
    c.add_argument("--id", default=None, help="paket klasör adı; varsayılan <dosya adı>-<içerik özeti 8 hane>")
    i = alt.add_parser("iz", help="kaynak maddesi → belge kimliği tablosunu denetle")
    i.add_argument("paket")
    i.add_argument("--tablo", required=True)
    i.add_argument("--belge", action="append", required=True, help="tekrarlanabilir: FS + EK …")
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return cikar(a) if a.komut == "cikar" else iz(a)
    except Exception as exc:  # noqa: BLE001 — yakalanmayan hata Python'un çıkış 1'i olur ve FAIL ile karışır
        print(f"[ÖLÇÜLEMEDİ] beklenmeyen hata ({type(exc).__name__}: {exc}) — bu 'PASS' ya da 'FAIL' DEĞİLDİR; "
              "girdiyi ve hatayı bakımcıya bildir.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
