#!/usr/bin/env python3
"""IX (DEV_CORE / PROVA) -> aXet template aktarım haritası denetimi.

Ne yapar:
  1. Kaynak repoların git'te izlenen dosyalarını listeler (git ls-files) ve her dosyayı
     maintenance/sync-rules.json'daki İLK eşleşen kurala bağlar.
  2. maintenance/sync-lock.json'daki son kilitli hash'lerle karşılaştırır:
     KURALSIZ (hiçbir kurala düşmeyen) · YENİ · DEĞİŞEN · SİLİNEN · DEĞİŞMEYEN.
  3. Kural hijyenini denetler: geçersiz karar/durum, gerekçesiz 'alinmaz', hiç dosya eşlemeyen
     kural, durumu 'tamam' olup hedefi diskte olmayan kural.

Kullanım (template kökünden):
  python maintenance/sync_check.py --source DEV_CORE=<DEV_CORE klonu> --source PROVA=<PROVA klonu>
  python maintenance/sync_check.py ... --ayrinti          değişmeyenler dahil tüm eşleşmeleri yaz
  python maintenance/sync_check.py ... --json              makinece okunur çıktı
  python maintenance/sync_check.py ... --update-lock       aktarım bittikten SONRA: hash'leri kilitle
                                                           (KURALSIZ=0 ve kural hatası yokken çalışır)
        --update-lock çekirdek kimlik kaydını da yeniden yazar; ikisi BİRLİKTE yazılır ya da hiçbiri. Kayıt
        üretilemezse ya da CEKIRDEK_KAYNAK kural dosyasının 'sources' anahtarlarında yoksa çıkış 3, kilit yazılmaz.
        Yazma sırası: önce kayıt, sonra kilit (ikisi de geçici dosya + os.replace); kayıt yazılamazsa kilit eski kalır.
Çıkış kodu: 0 temiz · 1 KURALSIZ dosya ya da eksik 'tamam' hedefi var · 2 kural dosyası hatası · 3 kullanım/git
hatası, kimlik kaydı üretilemedi/yazılamadı ya da kilit yazılamadı.
Hash satır sonundan bağımsızdır (CRLF -> LF normalize edilir).

KİMLİK HİZASI (Z206, 2026-10-19) — çekirdek ailelerinde kontrol listesi numarasını YALNIZ çekirdek verir:
  python maintenance/sync_check.py --source DEV_CORE=<yol> --kimlik-kaydi
        çekirdeğin kimlik tanımlarından maintenance/kimlik-kaydi.json üretir (--update-lock da yeniden üretir).
  python maintenance/sync_check.py --kimlik-denetle [--kok <aXet kökü>] [--kayit <json>]
        aXet tanımlarını KAYIT DOSYASIYLA denetler — çekirdeğe ERİŞMEZ (tests/test_kimlik_hizasi.py bunu koşar).
        Çıkış: 0 temiz · 1 ihlal (kayıtta olmayan önekli olmayan kimlik · AX- çift tanım · AX- biçim) · 2 ÖLÇÜLEMEDİ.
  DEV_CORE kaynağı verilen her normal koşum KİMLİK UYUMU uyarı listesi basar; çıkış kodunu DEĞİŞTİRMEZ.
  aXet'e özgü kural `AX-<aile>-<nn>` alır. Eski → yeni eşleme: maintenance/kimlik-eslemesi.md.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import difflib
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
AXET_HOME = HERE.parent
RULES_FILE = HERE / "sync-rules.json"
LOCK_FILE = HERE / "sync-lock.json"
DECISIONS = {"al", "uyarla", "telafi", "alinmaz", "bekliyor"}
STATUSES = {"tamam", "kismi", "yapiliyor", "planli", "bekliyor", "-"}
ACTIONABLE = {"al", "uyarla", "telafi", "bekliyor"}


def git(src: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True, stdin=subprocess.DEVNULL).stdout


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate(data: dict) -> list[str]:
    problems = []
    sources = set((data.get("sources") or {}).keys())
    for i, r in enumerate(data.get("rules") or []):
        tag = f"kural #{i} ({r.get('source')}:{r.get('pattern')})"
        for key in ("source", "pattern", "decision", "status", "targets"):
            if key not in r:
                problems.append(f"{tag}: '{key}' alanı yok")
        if r.get("source") not in sources:
            problems.append(f"{tag}: bilinmeyen kaynak")
        if r.get("decision") not in DECISIONS:
            problems.append(f"{tag}: geçersiz karar {r.get('decision')!r}")
        if r.get("status") not in STATUSES:
            problems.append(f"{tag}: geçersiz durum {r.get('status')!r}")
        if r.get("decision") == "alinmaz" and not (r.get("note") or "").strip():
            problems.append(f"{tag}: 'alinmaz' kararının gerekçesi (note) boş")
    for c in data.get("capabilities") or []:
        tag = f"yetenek {c.get('id')!r}"
        if c.get("decision") not in DECISIONS or c.get("status") not in STATUSES:
            problems.append(f"{tag}: geçersiz karar/durum")
        if c.get("decision") == "alinmaz" and not (c.get("note") or "").strip():
            problems.append(f"{tag}: 'alinmaz' kararının gerekçesi boş")
    return problems


def first_rule(rules: list[dict], source: str, path: str) -> int | None:
    for i, r in enumerate(rules):
        if r["source"] == source and fnmatch.fnmatchcase(path, r["pattern"]):
            return i
    return None


def target_missing(target: str) -> bool:
    return not (AXET_HOME / target.rstrip("/")).exists()


# ── Kimlik hizası (Z206) ────────────────────────────────────────────────────────────────────────────────────
# Kök neden (ölçüldü 2026-10-19): aXet aynı ailelere (BE, FE, DOC-*, UI-*) çekirdekten habersiz "sıradaki boş
# numara" veriyordu ⇒ aynı numara iki depoda farklı kurala gitti (FE-42..47 kayması, DOC-TS-06..08 …).
KIMLIK_KAYDI = HERE / "kimlik-kaydi.json"
# Çekirdek kaynağının sync-rules.json / --source adı TEK yerde: public depoya giden dosyalar (tests/) bu adı düz
# yazmaz, buradan okur (iç repo adı maintenance/ dışında yayın taramasında BLOCKER).
CEKIRDEK_KAYNAK = "DEV_CORE"
AX_ONEK = "AX-"
# Tanım biçimleri — KAPSAM BEYANI bu sabitlerden basılır (elle tutulan ikinci liste yok).
TABLO_BASLIKLARI = ("ID", "#", "Kimlik")          # tablonun BAŞLIK satırındaki ilk hücre bunlardan biri olmalı
_ID_TABLO = re.compile(r"^(?:AX-)?[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+[a-z]?$")   # harf sonekli dahil: CLC-ATC2, CDS-DUP
_ID_NUMARALI = r"(?:AX-)?[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+[a-z]?"
# Başlık tanımı: `### CDS-DCL-01 · …` / `## ⛔ CDS-DCL-01 — …`. Kimlikten hemen sonra ayraç ya da satır sonu gelmeli:
# `### CDS-NSDM-01 ek · …` bir ALT BÖLÜMDÜR, ikinci tanım değil (çekirdek kimlik-tekilliği aracındaki `B0-X` emsali).
_BASLIK_TANIM = re.compile(rf"^#{{1,6}}[ \t]+(?:[^\w\s`*]+[ \t]*)*\**({_ID_NUMARALI})\**[ \t]*(?:[·—–:|]|$)")
_AX_BICIM = re.compile(r"^AX-[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d{2}$")
_FENCE = re.compile(r"^[ \t]*(```|~~~)")
_AYRAC = re.compile(r"^\|[\s:|-]+\|?$")
TANIM_BICIMLERI = (f"tablo satırının ilk hücresi (tablo başlığının ilk hücresi ∈ {{{', '.join(TABLO_BASLIKLARI)}}}; "
                   "harf sonekli kimlik dahil)",
                   "başlık `#… <KİMLİK>` + ayraç (· — – : |) ya da satır sonu (`<KİMLİK> ek ·` alt bölümdür)")
AXET_TANIM_DIZINLERI = ("skills-sap", "skills", "core", "docs")
AXET_HARIC_PARCALAR = ("templates", "tests", "__pycache__", "node_modules")
# DAR muafiyet: (dosya, aile) ÇİFTİ — ailenin başka dosyadaki tanımı ve bu dosyadaki başka aileler yine denetlenir.
# Gerekçe: bilinen-hata kataloğu indeksidir, kontrol listesi değildir; çekirdekte `K-` ailesi yoktur (ölçüldü 254134f).
# Tekillik burada da zorlanır (aynı K- iki kez = FAIL). Çekirdek bir gün bu aileyi açarsa muafiyetin gerekçesi düşer:
# `muaf_aile_cekirdekte()` bunu hem --kimlik-denetle kapsam beyanında hem ④ uyum raporunda UYARI olarak basar.
KIMLIK_MUAF = {("skills-sap/sap-adt-foundation/references/known-errors-adt.md", "K"):
               "bilinen ADT hata kataloğu indeksi (kontrol listesi değil; numarayı aXet verir)"}


def _aile(kimlik: str) -> str:
    return re.sub(r"-?\d+[a-z]?$", "", kimlik) or kimlik


def muaf_aile_cekirdekte(kayit: dict) -> list[str]:
    """Muaf tutulan aile çekirdek kaydında da tanımlıysa muafiyetin gerekçesi düşmüştür — [(aile: kimlikler)]."""
    kayitli = (kayit or {}).get("kimlikler") or {}
    out = []
    for aile in sorted({a for _, a in KIMLIK_MUAF}):
        ortak = sorted(k for k in kayitli if _aile(k) == aile)
        if ortak:
            out.append(f"{aile}-: {', '.join(ortak[:8])}{' …' if len(ortak) > 8 else ''}")
    return out


# Çekirdek kayıt kaynağı: iki dizin + aXet'in aynaladığı aileleri tanımlayan EK dosyalar (AÇIK liste; yeni bir aile
# aynalanınca buraya eklenir — kayıtta yoksa test KAYITTA-YOK ile söyler).
CEKIRDEK_KAYIT_DIZINLERI = ("playbook/checklists", "standards")
CEKIRDEK_EK_DOSYALAR = ("playbook/howto-belge-canli-teyit-turu.md",   # C-1..C-n (canlı teyit turu)
                        "playbook/modules/sd.md",                     # SD-K*, T-SD-*
                        "playbook/adt-cds.md")                        # CDS-DCL-*, CDS-NSDM-*
# DAR dışlama (dosya, aile): FS/TS belge standardının ÖRNEK tabloları (`RPT-001`, `EXC-001`, `D-01`, `S-01`) kural
# değil, şablon içi satır kimliğidir — aXet tarafında `templates/` ve FR-/KR-/TC- belge içi kimlikleriyle aynı sınıf.
# Ölçüldü (254134f): bu dosya kayda YALNIZ bu 6 kimliği veriyordu ve uyum raporunda 4 sahte "eksik aile" üretiyordu.
# Aynı aile başka bir çekirdek dosyasında tanımlanırsa yine kayda girer (dışlama dosyaya bağlı).
CEKIRDEK_ORNEK_HARIC = {("standards/04-documentation-fs-ts.md", aile): "FS/TS şablonunun örnek tablo kimliği (kural değil)"
                        for aile in ("D", "EXC", "RPT", "S")}
KIMLIK_BAKILMAYAN = ("düz cümle içi tanım · kod bloğu (```/~~~) içi · ŞABLON/ÖRNEK kimlikleri ÖLÇÜLMEDİ: `templates/` "
                     "ve `tests/` dışlanır, başlığı listede olmayan tablolar sayılmaz (FR-/KR-/TC-/SCR-/UT-/IT-… belge "
                     "içi kimliktir, her belgede meşru tekrar eder) · `memory/` · `maintenance/` (iş listesi ve yayın "
                     "kayıtları tanım değil KAYITTIR) · .md dışı dosyalar (scriptlerdeki kimlik dizgeleri) · ANLAM "
                     "eşliği (aynı numara farklı kural ise bu denetim GÖRMEZ — uyum raporundaki başlık benzerliği "
                     "yalnız ipucudur)")


def _md_satirlari(p: Path):
    """(satır_no, satır) — kod bloğu İÇİ atlanır. `split('\\n')`: splitlines U+2028'de de böler, satır no kayar."""
    fence = False
    for i, satir in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
        satir = satir.rstrip("\r")
        if _FENCE.match(satir):
            fence = not fence
            continue
        if not fence:
            yield i, satir


_KALIN = re.compile(r"^\s*(?:[^\w\s`*]+\s*)?\*\*(.+?)\*\*")
_ETIKET = re.compile(r"^[A-ZÇĞİÖŞÜ]{2,12}:?$")   # kalın ETİKET (MUST, EKSİK:, HATA) başlık değildir


def _temiz(metin: str, uzunluk: int = 90) -> str:
    m = _KALIN.match(metin)
    if m and _ETIKET.match(m.group(1).strip()) and metin[m.end():].strip(" \t—–:-"):
        metin = metin[m.end():].lstrip(" \t—–:-")   # `**MUST** — asıl cümle` → asıl cümle
        m = _KALIN.match(metin)
    metin = m.group(1) if m else metin
    metin = re.sub(r"[`*]", "", metin)
    return re.sub(r"\s+", " ", metin).strip()[:uzunluk]


def kimlik_tanimlari(kok: Path, dosyalar: list[Path]) -> tuple[list[tuple[str, str, str]], collections.Counter]:
    """Tanımlar [(kimlik, 'yol:satır', başlık)] + bakılmayan tablo sayacı (kimlik biçimli ilk hücre, başlık listede yok)."""
    tanimlar: list[tuple[str, str, str]] = []
    bakilmayan: collections.Counter = collections.Counter()
    for p in dosyalar:
        rel = p.relative_to(kok).as_posix()
        satirlar = list(_md_satirlari(p))
        baslik_hucresi = None
        for j, (i, satir) in enumerate(satirlar):
            s = satir.strip()
            if not s.startswith("|"):
                # Tablo başlığı dosyada bir SONRAKİ başlık satırına kadar geçerli kalır: çekirdek listelerinde satır
                # grupları boş satır ya da alıntı bloğuyla bölünüp başlıksız sürüyor (ölçüldü: backend 25, frontend 13).
                m = _BASLIK_TANIM.match(satir)
                if m:
                    tanimlar.append((m.group(1), f"{rel}:{i}", _temiz(satir[m.end():])))
                continue
            hucreler = [h.strip() for h in re.split(r"(?<!\\)\|", s.strip("|"))]
            sonraki = satirlar[j + 1][1].strip() if j + 1 < len(satirlar) else ""
            if _AYRAC.match(sonraki) and not _AYRAC.match(s):   # başlık satırı = ardından ayraç gelen satır
                baslik_hucresi = hucreler[0].strip("*` ")
                continue
            if _AYRAC.match(s):
                continue
            ilk = hucreler[0].strip().strip("*`").strip()
            if not _ID_TABLO.match(ilk):
                continue
            if baslik_hucresi in TABLO_BASLIKLARI:
                tanimlar.append((ilk, f"{rel}:{i}", _temiz(hucreler[1] if len(hucreler) > 1 else "")))
            else:
                bakilmayan[f"{rel} (başlık {baslik_hucresi!r})"] += 1
    return tanimlar, bakilmayan


def _md_dosyalari(kok: Path, dizinler: tuple[str, ...], haric: tuple[str, ...] = (),
                  ek: tuple[str, ...] = ()) -> tuple[list[Path], list[str]]:
    """(dosyalar, eksik_kaynaklar) — eksik dizin/ek dosya sessizce atlanmaz, çağırana bildirilir."""
    out: list[Path] = []
    eksik: list[str] = []
    for d in dizinler:
        taban = kok / d
        if not taban.is_dir():
            eksik.append(d + "/")
            continue
        out += [p for p in sorted(taban.rglob("*.md"))
                if p.is_file() and not any(h in p.relative_to(kok).parts for h in haric)]
    for e in ek:
        p = kok / e
        if p.is_file():
            out.append(p)
        else:
            eksik.append(e)
    return out, eksik


def axet_tanimlari(kok: Path):
    dosyalar, _ = _md_dosyalari(kok, AXET_TANIM_DIZINLERI, AXET_HARIC_PARCALAR)
    tanimlar, bakilmayan = kimlik_tanimlari(kok, dosyalar)
    return dosyalar, tanimlar, bakilmayan


def kimlik_kaydi_uret(cekirdek: Path, commit: str, kirli: bool = False) -> dict:
    """Bellek içi kayıt — `baslik` alanı uyum raporu içindir, DİSKE YAZILMAZ (bkz. `kayit_dosya_bicimi`)."""
    dosyalar, eksik = _md_dosyalari(cekirdek, CEKIRDEK_KAYIT_DIZINLERI, ek=CEKIRDEK_EK_DOSYALAR)
    tanimlar, _ = kimlik_tanimlari(cekirdek, dosyalar)
    haric = [(k, yer) for k, yer, _ in tanimlar if (yer.rsplit(":", 1)[0], _aile(k)) in CEKIRDEK_ORNEK_HARIC]
    tanimlar = [t for t in tanimlar if (t[1].rsplit(":", 1)[0], _aile(t[0])) not in CEKIRDEK_ORNEK_HARIC]
    if eksik or not tanimlar:
        raise ValueError(f"ÖLÇÜLEMEDİ: çekirdek kayıt kaynağı eksik {eksik} ya da 0 tanım ({len(tanimlar)})")
    kimlikler: dict = {}
    cekirdek_ici_cift: dict = {}
    for k, yer, baslik in tanimlar:
        dosya = yer.rsplit(":", 1)[0]
        if k in kimlikler:
            cekirdek_ici_cift.setdefault(k, [kimlikler[k]["yer"]]).append(dosya)
            continue
        kimlikler[k] = {"baslik": baslik, "yer": dosya}
    return {"_aciklama": ("sync_check.py --kimlik-kaydi üretir; ELLE DÜZENLEME. Çekirdeğin kontrol listesi kimlik "
                          "tanımlarının anlık görüntüsü: aXet önekli olmayan (AX- dışı) bir kimliği ancak burada varsa "
                          "tanımlayabilir (tests/test_kimlik_hizasi.py zorlar). Eski → yeni eşleme: kimlik-eslemesi.md. "
                          "Çekirdek kural METNİ (başlık) bilerek YAZILMAZ: serbest metin public depoya taşınmaz; uyum "
                          "raporu başlığı çekirdekten canlı okur."),
            "kaynak": CEKIRDEK_KAYNAK, "commit": commit, "kirli": kirli,
            "taranan": [f"{d}/**/*.md" for d in CEKIRDEK_KAYIT_DIZINLERI] + list(CEKIRDEK_EK_DOSYALAR),
            "tanim_bicimleri": list(TANIM_BICIMLERI),
            "sablon_haric": {"kural": sorted({f"{d} [{a}-]: {g}" for (d, a), g in CEKIRDEK_ORNEK_HARIC.items()}),
                             "dislanan": [f"{k} ({yer})" for k, yer in haric]},
            "dosya_sayisi": len(dosyalar), "tanim_sayisi": len(tanimlar),
            "cekirdek_ici_cift": cekirdek_ici_cift,
            "kimlikler": dict(sorted(kimlikler.items()))}


def kayit_dosya_bicimi(kayit: dict) -> dict:
    """Diske yazılan biçim: kimlik + çekirdek dosyası; çekirdeğin SERBEST METNİ (başlık) taşınmaz.

    Kök neden (Z206 inceleme F1, 2026-10-19): başlık çekirdek metnini olduğu gibi kopyalıyordu ve yerel sızıntı
    listesindeki bir kurum adı public depoya girdi (`yayin_hazirla.py --depo-tara` BLOCKER). Dosyadan başlık okuyan
    kod yoktu (denetim yalnız anahtara bakar, uyum raporu canlı kaydı kullanır) ⇒ alanı maskelemek yerine kaldırmak
    sızıntı sınıfını tümden kapatır. Kalan alanlar kimlik ve çekirdek dosya yoludur."""
    out = {k: v for k, v in kayit.items() if k != "kimlikler"}
    out["kimlikler"] = {k: {"yer": v["yer"]} for k, v in kayit["kimlikler"].items()}
    return out


def kimlik_denetle(kok: Path, kayit: dict) -> dict:
    """aXet tanımlarını kayda karşı denetler. Dönüş: {hatalar, olculemedi, kapsam, tanimlar}."""
    dosyalar, tanimlar, bakilmayan = axet_tanimlari(kok)
    kayitli = (kayit or {}).get("kimlikler") or {}
    olculemedi = []
    if not dosyalar:
        olculemedi.append(f"aXet tarama kümesinde .md dosyası YOK ({', '.join(AXET_TANIM_DIZINLERI)})")
    elif not tanimlar:
        olculemedi.append("aXet'te 0 kimlik tanımı — biçim değişti mi? ('0 tanım' ≠ 'temiz')")
    if not kayitli:
        olculemedi.append("kimlik kaydı boş ya da okunamadı — 'kayıt yok' ≠ 'ihlal yok'")
    if not (kayit or {}).get("commit"):
        olculemedi.append("kimlik kaydında kaynak 'commit' alanı yok")
    hatalar = []
    yerler: dict = collections.defaultdict(list)
    muaf: dict = collections.defaultdict(list)
    for k, yer, _ in tanimlar:
        if (yer.rsplit(":", 1)[0], _aile(k)) in KIMLIK_MUAF:
            muaf[k].append(yer)
        else:
            yerler[k].append(yer)
    for k in sorted(muaf):
        if len(muaf[k]) > 1:
            hatalar.append(f"[MUAF-ÇİFT-TANIM] {k}: {' · '.join(muaf[k])} — muaf katalogda da kimlik tekil olmalı")
    cok_yerli = []
    for k in sorted(yerler):
        if k.startswith(AX_ONEK):
            if len(yerler[k]) > 1:
                hatalar.append(f"[AX-ÇİFT-TANIM] {k}: {' · '.join(yerler[k])} — AX- kimliği tek yerde tanımlanır")
            if not _AX_BICIM.match(k):
                hatalar.append(f"[AX-BİÇİM] {k}: beklenen `AX-<AİLE>-<nn>` (iki haneli numara) — {yerler[k][0]}")
        elif kayitli and k not in kayitli:
            hatalar.append(f"[KAYITTA-YOK] {k}: çekirdek kaydında yok — aXet'e özgüyse `AX-` önekli aile kullan, "
                           f"çekirdekteyse kaydı yenile (--kimlik-kaydi) — {' · '.join(yerler[k])}")
        elif len(yerler[k]) > 1:
            cok_yerli.append(f"{k} ({len(yerler[k])})")
    kapsam = [f"aXet: {', '.join(d + '/**/*.md' for d in AXET_TANIM_DIZINLERI)} · hariç parçalar "
              f"{', '.join(AXET_HARIC_PARCALAR)} · {len(dosyalar)} dosya · {len(tanimlar)} tanım · "
              f"{len(yerler)} tekil kimlik ({sum(1 for k in yerler if k.startswith(AX_ONEK))} AX-) + {len(muaf)} muaf",
              f"kayıt: {len(kayitli)} kimlik · kaynak commit {(kayit or {}).get('commit') or 'YOK'} · taranan "
              f"{', '.join((kayit or {}).get('taranan') or ['?'])}"
              + (" · ⚠ UYARI: kayıt KİRLİ çekirdek ağacından üretildi (commit içeriği temsil etmeyebilir — temiz "
                 "ağaçta --kimlik-kaydi)" if (kayit or {}).get("kirli") else ""),
              "çekirdek kaydında dışlanan şablon kimlikleri: "
              + ("; ".join(((kayit or {}).get("sablon_haric") or {}).get("kural") or []) or "yok") + " — "
              + str(len(((kayit or {}).get("sablon_haric") or {}).get("dislanan") or [])) + " kimlik",
              *[f"tanım biçimi: {b}" for b in TANIM_BICIMLERI],
              f"çok-yerli çekirdek kimliği (aynı çekirdek kuralı birden çok skill'de — serbest): {len(cok_yerli)}"
              + (f" — {', '.join(cok_yerli)}" if cok_yerli else ""),
              f"DAR MUAFİYET (dosya + aile; kayıt eşliği aranmaz, tekillik aranır): {len(muaf)} kimlik — "
              + "; ".join(f"{d} [{a}-] {g}" for (d, a), g in KIMLIK_MUAF.items()),
              f"muaf aile çekirdekte de tanımlı (UYARI — muafiyet gözden geçirilmeli): "
              f"{'; '.join(muaf_aile_cekirdekte(kayit)) or 'yok'}",
              f"BAKILMAYAN: {KIMLIK_BAKILMAYAN}",
              f"bakılmayan tablo satırı (kimlik biçimli ilk hücre, başlık listede yok): {sum(bakilmayan.values())}"
              + "".join(f"\n      - {y}: {n}" for y, n in sorted(bakilmayan.items()))]
    return {"hatalar": hatalar, "olculemedi": olculemedi, "kapsam": kapsam, "tanimlar": tanimlar}


def kimlik_uyumu(kok: Path, kayit: dict, esik: float = 0.35) -> dict:
    """④ UYARI listesi: çekirdekte olup aXet'te olmayan kimlikler + aynı numarada başlık benzerliği düşük olanlar."""
    _, tanimlar, _ = axet_tanimlari(kok)
    kayitli = (kayit or {}).get("kimlikler") or {}
    axet: dict = {}
    for k, _, baslik in tanimlar:
        axet.setdefault(k, baslik)
    eksik = sorted(k for k in kayitli if k not in axet)
    aile: dict = collections.defaultdict(list)
    for k in eksik:
        aile[re.sub(r"-?\d+[a-z]?$", "", k) or k].append(k)
    dusuk = []
    for k in sorted(set(axet) & set(kayitli)):
        cekirdek_baslik = kayitli[k].get("baslik") or ""   # disk biçiminde başlık yok — çağıran canlı kaydı verir
        oran = difflib.SequenceMatcher(None, cekirdek_baslik.lower(), axet[k].lower()).ratio()
        if oran < esik:
            dusuk.append({"kimlik": k, "benzerlik": round(oran, 2), "cekirdek": cekirdek_baslik[:70],
                          "axet": axet[k][:70]})
    return {"eksik_aileler": dict(sorted(aile.items())), "eksik_sayi": len(eksik),
            "muaf_aile_cekirdekte": muaf_aile_cekirdekte(kayit),
            "sablon_haric": len(((kayit or {}).get("sablon_haric") or {}).get("dislanan") or []),
            "dusuk_benzerlik": dusuk, "esik": esik}


def _kimlik_uyumu_yaz(u: dict) -> None:
    print("\n=== KİMLİK UYUMU (UYARI — çıkış kodunu değiştirmez; içerik aktarımı ayrı iştir)")
    print(f"    çekirdekte olup aXet'te tanımı olmayan: {u['eksik_sayi']} kimlik, {len(u['eksik_aileler'])} aile")
    for a, v in u["eksik_aileler"].items():
        print(f"    [UYARI-EKSİK] {a}: {len(v)} — {', '.join(v[:12])}{' …' if len(v) > 12 else ''}")
    print(f"    aynı numara, başlık benzerliği < {u['esik']}: {len(u['dusuk_benzerlik'])} "
          "(ipucu — kısa aXet başlığı da düşük çıkar; anlam elle karşılaştırılır)")
    for d in u["dusuk_benzerlik"]:
        print(f"    [UYARI-BENZERLİK] {d['kimlik']} {d['benzerlik']}: çekirdek «{d['cekirdek']}» ↔ aXet «{d['axet']}»")
    for m in u.get("muaf_aile_cekirdekte") or []:
        print(f"    [UYARI-MUAF] muaf tutulan aile çekirdekte de tanımlı → KIMLIK_MUAF gerekçesi düştü: {m}")
    print("    KAPSAM: yalnız kimlik varlığı + başlık metni benzerliği; kural anlamı ve önem derecesi karşılaştırılmaz."
          f" Dışlanan şablon kimliği (CEKIRDEK_ORNEK_HARIC): {u.get('sablon_haric', 0)}.")


def _atomik_yaz(yol: Path, metin: str) -> None:
    """Geçici dosyaya yaz + `os.replace`: yarım yazılmış dosya kalmaz; hata olursa hedef ESKİ hâliyle durur."""
    gecici = yol.with_name(yol.name + ".yaziliyor")
    try:
        gecici.write_text(metin, encoding="utf-8", newline="\n")   # *.json eol=lf (.gitattributes)
        os.replace(gecici, yol)
    finally:
        if gecici.exists():
            gecici.unlink()


def _kimlik_kaydi_yaz_ve_bildir(kayit: dict, cekirdek_rapor: dict, sessiz: bool) -> None:
    # Kirli ağaç: kilit dosyasıyla AYNI desen (yaz + uyar) — reddetmek `--update-lock` akışında kilit ile kaydı
    # ayrıştırırdı. Fark: kayıt bunu `kirli: true` olarak TAŞIR, `--kimlik-denetle` kapsam beyanında UYARI basar.
    _atomik_yaz(KIMLIK_KAYDI, json.dumps(kayit_dosya_bicimi(kayit), ensure_ascii=False, indent=1) + "\n")
    if not sessiz:
        print(f"\nKimlik kaydı yazıldı: {KIMLIK_KAYDI} ({len(kayit['kimlikler'])} kimlik, commit "
              f"{kayit['commit'][:10]})" + (" · ⚠ çekirdek çalışma ağacı temiz değil — kayda `kirli: true` yazıldı; "
                                             "temiz ağaçta yeniden üret" if cekirdek_rapor["dirty"] else ""))


def _yazilmadi(mesaj: str, json_kipi: bool) -> None:
    """Yazılmadı/üretilemedi mesajı: --json kipinde stdout yalnız JSON taşır ⇒ mesaj stderr'e."""
    print(("" if json_kipi else "\n") + mesaj, file=sys.stderr if json_kipi else sys.stdout)


def kimlik_denetle_cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="aXet kimlik hizası denetimi (kayıt dosyasına karşı; çekirdeğe erişmez)")
    ap.add_argument("--kimlik-denetle", action="store_true")
    ap.add_argument("--kok", default=str(AXET_HOME), help="aXet kökü (fixture için)")
    ap.add_argument("--kayit", default=str(KIMLIK_KAYDI), help="kimlik kaydı JSON")
    a = ap.parse_args(argv)
    kok = Path(a.kok).resolve()
    try:
        kayit = json.loads(Path(a.kayit).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[ÖLÇÜLEMEDİ] kimlik kaydı okunamadı ({a.kayit}): {exc}")
        return 2
    s = kimlik_denetle(kok, kayit)
    print(f"sync_check --kimlik-denetle · kök: {kok}")
    print("KAPSAM BEYANI:")
    for satir in s["kapsam"]:
        print(f"  {satir}")
    rc = 0
    if s["hatalar"]:
        print(f"[FAIL] {len(s['hatalar'])} kimlik ihlali:")
        for h in s["hatalar"]:
            print(f"  - {h}")
        rc = 1
    if s["olculemedi"]:
        print(f"[ÖLÇÜLEMEDİ] {len(s['olculemedi'])}:")
        for o in s["olculemedi"]:
            print(f"  - {o}")
        rc = rc or 2
    if rc == 0:
        print(f"[OK] {len(s['tanimlar'])} tanım — kayıt dışı önekli olmayan kimlik yok, AX- çift tanım yok")
    return rc


def main() -> int:
    if "--kimlik-denetle" in sys.argv[1:]:
        return kimlik_denetle_cli(sys.argv[1:])
    ap = argparse.ArgumentParser(description="IX -> aXet aktarım haritası denetimi")
    ap.add_argument("--source", action="append", default=[], metavar="AD=YOL", help="kaynak repo (tekrarlanabilir)")
    ap.add_argument("--update-lock", action="store_true", help="güncel hash'leri kilit dosyasına yaz")
    ap.add_argument("--ayrinti", action="store_true", help="değişmeyen dosyaları da listele")
    ap.add_argument("--json", action="store_true", help="JSON çıktı")
    ap.add_argument("--kimlik-kaydi", action="store_true",
                    help="DEV_CORE kaynağından maintenance/kimlik-kaydi.json üret (Z206)")
    args = ap.parse_args()
    if not args.source:
        print("HATA: en az bir --source AD=YOL ver (ör. --source DEV_CORE=D:/repos/DEV_CORE).")
        return 3
    if args.kimlik_kaydi and not any(s.partition("=")[0] == CEKIRDEK_KAYNAK for s in args.source):
        print(f"HATA: --kimlik-kaydi için --source {CEKIRDEK_KAYNAK}=<yol> gerekir.")
        return 3

    data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    if args.update_lock and CEKIRDEK_KAYNAK not in (data.get("sources") or {}):
        # Sabit ile kural dosyası ayrışırsa çekirdek raporu hiç bulunmaz ⇒ kilit yazılır, kayıt sessizce yazılmazdı.
        _yazilmadi(f"--update-lock YAPILMADI: çekirdek kaynak adı ({CEKIRDEK_KAYNAK}) {RULES_FILE.name} 'sources' "
                   "içinde yok — CEKIRDEK_KAYNAK ile kural dosyası ayrışmış; kilit ve kimlik kaydı yazılmadı.", args.json)
        return 3
    problems = validate(data)
    rules = data["rules"]
    lock = json.loads(LOCK_FILE.read_text(encoding="utf-8")) if LOCK_FILE.exists() else {"sources": {}}

    report: dict = {"sources": {}, "rule_problems": problems}
    new_lock_sources: dict = {}
    used_rules: set[int] = set()
    checked_sources: set[str] = set()

    for spec in args.source:
        name, sep, raw = spec.partition("=")
        if not sep or name not in (data.get("sources") or {}):
            print(f"HATA: --source biçimi AD=YOL olmalı ve AD sync-rules.json 'sources' içinde olmalı: {spec!r}")
            return 3
        src = Path(raw).resolve()
        try:
            files = [f for f in git(src, "ls-files").splitlines() if f]
            commit = git(src, "rev-parse", "HEAD").strip()
            dirty = bool(git(src, "status", "--porcelain").strip())
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"HATA: {name} git okunamadı ({src}): {exc}")
            return 3
        checked_sources.add(name)
        locked = (lock.get("sources") or {}).get(name) or {}
        locked_files = locked.get("files") or {}
        buckets = {"kuralsiz": [], "yeni": [], "degisen": [], "silinen": [], "degismeyen": []}
        lock_files: dict = {}
        for rel in files:
            path = src / rel
            if not path.is_file():
                continue
            h = file_hash(path)
            idx = first_rule(rules, name, rel)
            if idx is None:
                buckets["kuralsiz"].append({"path": rel})
                continue
            used_rules.add(idx)
            r = rules[idx]
            item = {"path": rel, "rule": r["pattern"], "decision": r["decision"], "status": r["status"],
                    "targets": r.get("targets") or [], "party": r.get("party")}
            lock_files[rel] = {"sha256": h, "rule": r["pattern"], "decision": r["decision"], "status": r["status"]}
            old = locked_files.get(rel)
            if old is None:
                buckets["yeni"].append(item)
            elif old.get("sha256") != h:
                item["lock_status"] = old.get("status")
                buckets["degisen"].append(item)
            else:
                buckets["degismeyen"].append(item)
        current = set(files)
        for rel, old in locked_files.items():
            if rel not in current:
                buckets["silinen"].append({"path": rel, "rule": old.get("rule"), "decision": old.get("decision"),
                                           "status": old.get("status")})
        report["sources"][name] = {"path": str(src), "commit": commit, "lock_commit": locked.get("commit"),
                                   "dirty": dirty, "file_count": len(files), **buckets}
        new_lock_sources[name] = {"commit": commit, "locked_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                  "files": lock_files}

    unused = [f"{r['source']}:{r['pattern']}" for i, r in enumerate(rules)
              if r["source"] in checked_sources and i not in used_rules]
    missing_targets = [f"{r['source']}:{r['pattern']} -> {t}" for r in rules if r["status"] == "tamam"
                       for t in r.get("targets") or [] if target_missing(t)]
    missing_targets += [f"yetenek {c['id']} -> {t}" for c in data.get("capabilities") or [] if c["status"] == "tamam"
                        for t in c.get("targets") or [] if target_missing(t)]
    summary: dict = {}
    for r in rules:
        summary.setdefault(r["decision"], {}).setdefault(r["status"], 0)
        summary[r["decision"]][r["status"]] += 1
    waiting = {}
    for r in rules + (data.get("capabilities") or []):
        if r["decision"] == "bekliyor" or r["status"] in ("bekliyor", "planli", "yapiliyor", "kismi"):
            waiting.setdefault(str(r.get("party")), 0)
            waiting[str(r.get("party"))] += 1
    report.update({"unused_rules": unused, "missing_targets": missing_targets, "rule_summary": summary,
                   "open_by_party": waiting, "capabilities": data.get("capabilities") or []})
    kuralsiz_total = sum(len(s["kuralsiz"]) for s in report["sources"].values())

    # Z206: çekirdek kimlik kaydı canlı üretilir (yazma yalnız --kimlik-kaydi / --update-lock), uyum raporu her koşumda.
    kimlik_kaydi_canli = None
    cekirdek_rapor = report["sources"].get(CEKIRDEK_KAYNAK)
    if cekirdek_rapor:
        try:
            kimlik_kaydi_canli = kimlik_kaydi_uret(Path(cekirdek_rapor["path"]), cekirdek_rapor["commit"],
                                                   kirli=cekirdek_rapor["dirty"])
            report["kimlik_uyumu"] = kimlik_uyumu(AXET_HOME, kimlik_kaydi_canli)
        except ValueError as exc:
            report["kimlik_uyumu"] = {"olculemedi": str(exc)}
    if args.kimlik_kaydi and kimlik_kaydi_canli is None:
        _yazilmadi(f"HATA: kimlik kaydı üretilemedi — {report['kimlik_uyumu']['olculemedi']}", args.json)
        return 3

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, s in report["sources"].items():
            print(f"=== {name}  {s['path']}")
            print(f"    commit {s['commit'][:10]} · kilit {(s['lock_commit'] or 'YOK')[:10]} · {s['file_count']} dosya"
                  + (" · ⚠ çalışma ağacı temiz değil (git status)" if s["dirty"] else ""))
            print("    " + " · ".join(f"{k.upper()}: {len(s[k])}" for k in ("kuralsiz", "yeni", "degisen", "silinen", "degismeyen")))
            for it in s["kuralsiz"]:
                print(f"    [KURALSIZ] {it['path']}  → sync-rules.json'a kural ekle")
            for it in s["degisen"]:
                flag = "AKTARILMIŞTI" if it.get("lock_status") in ("tamam", "kismi", "yapiliyor") else "henüz aktarılmamıştı"
                act = "hedefi güncelle" if it["decision"] in ACTIONABLE else "bilgi"
                print(f"    [DEĞİŞEN] {it['path']}  ({it['decision']}/{it['status']}, {flag}) → {act}: {', '.join(it['targets']) or '-'}")
                print(f"              fark: git -C \"{s['path']}\" diff {(s['lock_commit'] or '<kilit>')[:10]}..HEAD -- \"{it['path']}\"")
            for it in s["silinen"]:
                print(f"    [SİLİNEN] {it['path']}  (kural {it['rule']}, {it['decision']}/{it['status']}) → hedefte karşılığını gözden geçir")
            for it in s["yeni"]:
                if it["decision"] != "alinmaz" or args.ayrinti:
                    print(f"    [YENİ] {it['path']}  → {it['decision']}/{it['status']} (kural {it['rule']})")
            hidden = sum(1 for it in s["yeni"] if it["decision"] == "alinmaz")
            if hidden and not args.ayrinti:
                print(f"    (YENİ ama 'alinmaz' kuralına düşen {hidden} dosya gizlendi; --ayrinti ile görünür)")
            if args.ayrinti:
                for it in s["degismeyen"]:
                    print(f"    [AYNI] {it['path']}  → {it['decision']}/{it['status']}")
        print("\n=== Kural özeti (karar → durum sayısı)")
        for dec, st in sorted(summary.items()):
            print(f"    {dec}: " + ", ".join(f"{k}={v}" for k, v in sorted(st.items())))
        print("    açık kalem (bekliyor/planli/yapiliyor/kismi) parti bazında: "
              + ", ".join(f"parti {k}={v}" for k, v in sorted(waiting.items())))
        print("\n=== Claude/aXet yetenekleri (dosya dışı kaynaklar)")
        for c in data.get("capabilities") or []:
            print(f"    {c['id']}{(' ' + c['version']) if c.get('version') else ''}: {c['decision']}/{c['status']} → {', '.join(c.get('targets') or []) or '-'}")
        if problems:
            print("\n=== KURAL DOSYASI HATALARI"); [print(f"    {p}") for p in problems]
        if unused:
            print("\n=== Hiç dosya eşlemeyen kurallar (kaynak dosya silinmiş/taşınmış olabilir)"); [print(f"    {u}") for u in unused]
        if missing_targets:
            print("\n=== Durumu 'tamam' ama hedefi diskte olmayanlar"); [print(f"    {m}") for m in missing_targets]
        print("\nKAPSAM — bakılanlar: git'te izlenen dosyalar, hash farkı, kural eşlemesi, 'tamam' hedeflerinin varlığı."
              "\nBAKILMAYANLAR: izlenmeyen/gitignore'lu dosyalar · hedef İÇERİĞİNİN kaynağa uygunluğu · Claude plugin"
              " sürümlerinin güncelliği (capabilities elle tutulur) · aXet.code yeni sürümünün davranış değişiklikleri"
              " (docs/axet-davranis-olcumleri.md yeniden ölçülmeli).")
        ku = report.get("kimlik_uyumu")
        if ku and "olculemedi" in ku:
            print(f"\n=== KİMLİK UYUMU [ÖLÇÜLEMEDİ] {ku['olculemedi']}")
        elif ku:
            _kimlik_uyumu_yaz(ku)
        else:
            print(f"\n=== KİMLİK UYUMU ÖLÇÜLMEDİ: {CEKIRDEK_KAYNAK} kaynağı verilmedi.")

    # Yazma ilkesi: kilit ve kimlik kaydı aynı çekirdek commit'ini anlatır ⇒ İKİSİ BİRLİKTE yazılır ya da hiçbiri.
    # (Önce: yalnız --update-lock'ta kayıt üretilemezse kilit yeni commit'e geçip kayıt eski kalıyordu, rc 0; KURALSIZ
    # varken --update-lock --kimlik-kaydi kaydı yazıp kilidi yazmıyordu.)
    if problems:   # kural dosyası hatalıyken HİÇBİR çıktı dosyası yazılmaz (kilit de kayıt da)
        if args.kimlik_kaydi or args.update_lock:
            _yazilmadi("Kilit / kimlik kaydı YAZILMADI: kural dosyası hatalı (KURAL DOSYASI HATALARI).", args.json)
        return 2
    if args.update_lock:
        if kuralsiz_total:
            _yazilmadi(f"--update-lock YAPILMADI: {kuralsiz_total} KURALSIZ dosya var"
                       + (" — kimlik kaydı da YAZILMADI (kilitle birlikte yazılır)." if args.kimlik_kaydi else "."),
                       args.json)
            return 1
        if cekirdek_rapor and kimlik_kaydi_canli is None:
            _yazilmadi("--update-lock YAPILMADI: çekirdek kimlik kaydı üretilemedi — "
                       f"{report['kimlik_uyumu']['olculemedi']} (kilit kayıtsız ilerlerse kayıt eski commit'te kalır).",
                       args.json)
            return 3
    # SIRA: önce kayıt, sonra kilit. Kayıt yazılamazsa kilit ESKİ kalır ⇒ sonraki koşum aynı farkı DEĞİŞEN olarak
    # yine gösterir (güvenli yön). Ters sırada kilit yeni / kayıt eski kalıyor ve fark bir daha görünmüyordu.
    kayit_yazildi = False
    if kimlik_kaydi_canli is not None and (args.kimlik_kaydi or args.update_lock):
        kayit_yazildi = True
        try:
            _kimlik_kaydi_yaz_ve_bildir(kimlik_kaydi_canli, cekirdek_rapor, args.json)
        except OSError as exc:
            _yazilmadi(f"Kimlik kaydı YAZILAMADI ({exc})"
                       + (" — kilit de YAZILMADI (eski hâliyle duruyor)." if args.update_lock else "."), args.json)
            return 3
    if args.update_lock:
        merged = {"_aciklama": "sync_check.py --update-lock üretir; elle düzenleme. Hash CRLF->LF normalize sha256.",
                  "sources": {**(lock.get("sources") or {}), **new_lock_sources}}
        try:
            _atomik_yaz(LOCK_FILE, json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        except OSError as exc:
            _yazilmadi(f"--update-lock: kilit YAZILAMADI ({exc}) — "
                       + ("kimlik kaydı yeni, kilit eski: " if kayit_yazildi else "kilit eski hâliyle duruyor: ")
                       + "sonraki koşum farkı DEĞİŞEN olarak yine gösterir; --update-lock'u yinele.", args.json)
            return 3
        if not args.json:
            print(f"\nKilit güncellendi: {LOCK_FILE} ({', '.join(new_lock_sources)})")
    return 1 if (kuralsiz_total or missing_targets) else 0


if __name__ == "__main__":
    sys.exit(main())
