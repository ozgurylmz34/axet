#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vakum-assertion tarayıcısı — testin ADININ vaat ettiğini GÖVDESİNİN ölçüp ölçmediğine bakar.

**Vakum assertion**: var olan, yeşil koşan, ama hiçbir şey kanıtlamayan test. Ölçülmüş üç biçimi:
  ① testin adı bir şey vaat ediyor, gövdesi onu hiç ölçmüyor,
  ② `rc != 0` bekleniyor ama beklenen hata, ölçülmek istenenden ÖNCE gelen bambaşka bir arızadan
     doğuyor — kural tamamen kaldırılsa test yine yeşil kalır,
  ③ mutasyon, hatalı ama İKNA EDİCİ bir çıktı üretiyor ve test onu kabul ediyor.
Bu araç ①'e ve ②'ye bakar; ③ statik olarak görülemez, yalnız mutasyonla çıkar.

⛔ **BU BİR GATE DEĞİLDİR — elle koşulan teşhis aracıdır.**
Bulgu bulsa da bulmasa da **daima çıkış 0** döner ve hiçbir akışı bloklamaz. Bu bilinçli:
yeni bir gate açmak ADR 0019 moratoryumunun 5 şartı + kullanıcının açık onayını gerektirir;
o onay istenmedi. Çıkış kodunu bulguya bağlamak aracı sessizce gate'e çevirirdi.

⚠ **DARALTMA aracıdır, KANIT değildir.** "Şu 43 teste bak" der; "43'ü bozuk" DEMEZ.
Bir testin gerçekten kusurlu olduğuna yalnız **mutasyon** karar verir: testin koruduğu kuralı
üründen tamamen kaldır → test hâlâ yeşilse bulgu, kırmızıysa aday düşer ("ölçüldü, sağlam").

Kullanım:  python maintenance/vakum_tara.py <repo-kökü>

Aracın KENDİ kalibrasyonu `tests/test_vakum_tara.py`'dedir ve iki kez sessizce körleştiği için
vardır (2026-09-18): gövde dilimi `def` satırını içeriyordu ⇒ her test kendi vaadini kendi adıyla
kanıtlıyordu; ayrıca sözcük sınırına `_` dahildi ⇒ `s3` simgesi `s3_cekirdek` içinde geçtiği hâlde
"yok" sayılıyordu. İkisi de yalnız kontrol grubuyla (bilinen doğru-pozitif + bilinen doğru-negatif)
yakalandı. **Bu dosyayı değiştiren, o testleri koşmadan bırakmaz.**
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ASSERT_RE = re.compile(r"\bself\.assert\w+|(?<![\w.])assert\s|\bassertRaises\b")
RC_BEKLE = re.compile(r"assertEqual\(\s*[^,]*\b(rc|returncode|cikis|kod)\b[^,]*,\s*([1-9])"
                      r"|assertEqual\(\s*([1-9])\s*,\s*[^,]*\b(rc|returncode|cikis|kod)\b", re.I)
ICERIK = re.compile(r"assertIn\(|assertRegex\(|assertNotIn\(|\bin\s+(out|cikti|stdout|stderr|r\.stdout)", re.I)

# Testin adındaki parça ancak KOD-BENZERİ bir SİMGE ise "vaat" sayılır.
# Türkçe betimleyici sözcükler (ezme, riskli, bulgu…) alan terimi olarak görülünce 684 yanlış
# pozitif üretti; bu daraltma o yüzden şart (ölçüldü 2026-09-18).
#   V1R V4c V4t V6d   -> vaka kodu (harf + rakam [+ harf])
#   h1 a4 m2 y7 l3 d2 -> küçük harfli vaka kodu (aynı sınıf)
#   VTB VKD ALL_CAPS  -> sabit / enum adı
KOD_SIMGE = re.compile(r"^(?:[A-Za-z]\d+[A-Za-z]?|[A-Z][A-Z0-9_]{2,})$")

BAKILANLAR = ("test adındaki kod-benzeri simge gövdede geçiyor mu · "
              "hiç assert var mı (proje assert yardımcıları dahil) · "
              "rc!=0 iddiasının yanında HANGİ hata olduğu doğrulanıyor mu")
BAKILMAYANLAR = ("bulgunun GERÇEKTEN kusur olup olmadığı (yalnız mutasyon söyler) · "
                 "assertion'ın anlamca doğruluğu · fixture'ın kurduğu senaryonun gerçekliği · "
                 "aşırı-belirtilmiş (over-specified) assertion · `tests/` dışındaki testler · "
                 "Python olmayan test dosyaları · testin gerçekten KOŞTUĞU")


def yardimcilar(agac: ast.AST, satirlar: list[str]) -> set[str]:
    """Gövdesinde assert BULUNAN test-dışı metotlar = projenin kendi assert yardımcıları (`self.var` gibi).

    Tanınmazlarsa araç 400+ testin çoğunu ASSERT-YOK diye raporlar ve okunamaz hâle gelir.
    """
    ad: set[str] = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.FunctionDef) and not d.name.startswith("test"):
            gov = "\n".join(satirlar[d.lineno - 1:(d.end_lineno or d.lineno)])
            if ASSERT_RE.search(gov):
                ad.add(d.name)
    return ad


def tara(kok: Path) -> tuple[int, int, list[tuple[str, int, str, str]]]:
    bulgular: list[tuple[str, int, str, str]] = []
    df = tf = 0
    ortak: set[str] = set()       # yardımcılar TÜM test dosyalarından toplanır (`_helpers.py` ortak taban)
    agaclar: dict[Path, tuple[ast.AST, list[str]]] = {}
    for f in sorted((kok / "tests").glob("*.py")):
        kaynak = f.read_text(encoding="utf-8", errors="replace")
        try:
            a = ast.parse(kaynak)
        except SyntaxError:
            continue
        sat = kaynak.splitlines()
        agaclar[f] = (a, sat)
        ortak |= yardimcilar(a, sat)

    for f, (agac, satirlar) in agaclar.items():
        if not f.name.startswith("test_"):
            continue
        df += 1
        for d in ast.walk(agac):
            if not isinstance(d, ast.FunctionDef) or not d.name.startswith("test"):
                continue
            tf += 1
            gov = "\n".join(satirlar[d.lineno - 1:(d.end_lineno or d.lineno)])
            # ⛔ İMZA SATIRI GÖVDEYE DAHİL EDİLMEZ. Edilirse testin ADI gövdesinin içinde olur ve
            # her test kendi vaadini KENDİ ADIYLA kanıtlar ⇒ AD-GÖVDE boyutu tümden körleşir,
            # üstelik çıktı "0 bulgu" diye sağlıklı görünür (ölçüldü 2026-09-18).
            govl = " ".join(satirlar[d.lineno:(d.end_lineno or d.lineno)]).lower()

            assert_var = bool(ASSERT_RE.search(gov)) or any(
                re.search(r"self\." + re.escape(y) + r"\s*\(", gov) for y in ortak)
            if not assert_var:
                bulgular.append((f.name, d.lineno, "ASSERT-YOK", d.name))
                continue

            for parca in re.split(r"[_\W]+", d.name):
                if parca == "test" or not KOD_SIMGE.match(parca):
                    continue
                p = parca.lower()
                # Sınır sınıfına `_` DAHİL EDİLMEZ: simge bir bileşik adın parçası olarak geçse de
                # (`s3` → `s3_cekirdek`) vaat ÖLÇÜLMÜŞ sayılır. Ama alfanümerik sınır KORUNUR:
                # `V6d` geçmesi `V6` vaadini KARŞILAMAZ — ayrı vaka kodlarıdır.
                if not re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", govl):
                    bulgular.append((f.name, d.lineno, "AD-GOVDE",
                                     f"{d.name}  ->  ad'da '{parca}' var, govdede YOK"))

            if RC_BEKLE.search(gov) and not ICERIK.search(gov):
                bulgular.append((f.name, d.lineno, "RC-AYIRT-EDILEMEZ",
                                 f"{d.name}  ->  rc!=0 bekleniyor, hangi hata dogrulanmiyor"))
    return df, tf, bulgular


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("kullanim: python maintenance/vakum_tara.py <repo-koku>")
        return 0                      # gate degil: hatali kullanimda bile akisi bloklamaz
    df, tf, b = tara(Path(argv[1]))
    tur: dict[str, int] = {}
    for _, _, t, _ in b:
        tur[t] = tur.get(t, 0) + 1
    print(f"Taranan: {df} test dosyasi, {tf} test fonksiyonu")
    print(f"Bulgu: {len(b)}" + ("  ->  " + " · ".join(f"{k}={v}" for k, v in sorted(tur.items())) if b else ""))
    print()
    for dosya, satir, t, m in b:
        print(f"  [{t}] {dosya}:{satir}  {m}")
    if b:
        print()
    # KAPSAM BEYANI her kosumda basilir - en kritik an SIFIR-BULGU anidir (bulgu varken zaten okunur).
    print(f"KAPSAM — bakilanlar: {BAKILANLAR}")
    print(f"KAPSAM — bakilmayanlar: {BAKILMAYANLAR}")
    print("NOT: bu bir DARALTMA aracidir, kanit degildir. Kusur kararini yalniz MUTASYON verir")
    print("     (kurali urunden tamamen kaldir -> test hala yesilse bulgu). Cikis kodu DAIMA 0.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
