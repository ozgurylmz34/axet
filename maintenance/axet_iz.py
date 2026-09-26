#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aXet oturum izi — model beyanı değil, MOTORUN kaydı (Z112, 2026-09-26).

Canlı ölçüm turlarında (Z103/Z105 …) "model şunu yaptı" hükmü bu araçla verilir: aXet'in oturum veritabanı ve
logu okunur, modelin kendi anlatımı kanıt sayılmaz.

Kaynak: `<veri dizini>/axet-code.db` (sessions · messages · read_files · files) + `<veri dizini>/logs/axet-code.log`.
Veri dizini motorun kuralıyla bulunur (`docs/axet-davranis-olcumleri.md` "Veri dizini"): `--proje` dizininde
`.axet-code` klasörü yoksa üst dizinlerdeki İLK `.axet-code` kullanılır. Üst dizinden bulunduysa çıktı bunu yazar.

Kullanım:
  python maintenance/axet_iz.py [--proje <dizin>]                    son 10 kök oturumun özeti (vars. bulunulan dizin)
  python maintenance/axet_iz.py [--proje <dizin>] --oturum 1         en yeni kök oturumun tam izi (2 = bir önceki …)
  python maintenance/axet_iz.py [--proje <dizin>] --oturum <önek>    oturum kimliği önekiyle
  python maintenance/axet_iz.py … --adet 25                          özet listesinde kaç kök oturum

§0 sırası hükmü (yalnız kök oturum; alt ajan çekirdeği görmez — ölçüldü, aynı belge "Alt ajan bağlamı"):
  VAR = `session_brief` bash çağrısı ilk model metninden ÖNCE geldi VE ilk model metninin ilk satırı kanarya
  (`core/00-temel.md` §0 biçimi). Biri eksikse YOK + neden.

Çıkış kodu (GATE DEĞİLDİR — hiçbir akış bu kodu okumaz; elle koşulan teşhis aracıdır):
  0 özet basıldı · tam izde §0 sırası VAR
  1 tam izde §0 sırası YOK (bulgu)
  2 ÖLÇÜLEMEDİ: veri dizini / DB yok · beklenen şema yok · oturum bulunamadı
  3 kullanım hatası (bilinmeyen argüman · proje dizini yok · belirsiz oturum öneki)

Kaynak: PROVA canlı test turunun (2026-09-24) yerel aracı; genelleştirildi (sabit proje yolu kaldırıldı),
log eşleşmesi oturum kimliğine çevrildi, çıkış kodu ve KAPSAM beyanı eklendi. Kalibrasyonu `tests/test_axet_iz.py`
(kanaryalı / kanaryasız / sırası bozuk üç bilinen oturum). **Bu dosyayı değiştiren, o testleri koşmadan bırakmaz.**
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sqlite3
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

VERI_DIZINI = ".axet-code"
DB_ADI = "axet-code.db"
LOG_YOLU = Path("logs") / "axet-code.log"
# core/00-temel.md §0: `[AXET-CORE-<sürüm> · SAP: <..> · proje: <..> · proje hafızası: <..>]`
KANARYA = re.compile(r"^\[AXET-CORE-(\S+) · SAP: (\S+) · proje: (\S+) · proje hafızası: (\S+)\]")
RET = re.compile(r"deni|deny|reddet|blocked|permission decision", re.I)
# Aracın okuduğu kolonlar; biri yoksa fail-closed (2): sessiz yanlış iz basmaktansa "ölçülemedi".
SEMA = {"sessions": {"id", "parent_session_id", "title", "created_at"},
        "messages": {"session_id", "role", "parts", "created_at"},
        "read_files": {"session_id", "path"},
        "files": {"session_id", "path"}}
KAPSAM = ("KAPSAM — bakılanlar: oturum DB'si (sessions/messages/read_files/files) + axet-code.log izin/ret satırları.",
          "KAPSAM — bakılmayanlar: modelin düşüncesi (reasoning DB'de boş gelir) · ekrana basılıp DB'ye yazılmayan her şey · "
          "`bash cat` ile okunan dosyalar (read_files yalnız araç okumasını kaydeder) · kanarya/sıra denetiminin ANLAMI "
          "(metin eşlemesidir) · log dönmüşse eski satırlar · izin/ret dışındaki log satırları.")


class Olculemedi(Exception):
    """Çıkış 2."""


class Kullanim(Exception):
    """Çıkış 3."""


def saniye(x: float) -> float:
    # Şema yorumu "Unix timestamp in milliseconds" der; ÖLÇÜLDÜ (2026-09-26, gerçek aXet DB): sessions/messages/
    # read_files/files zaman damgaları SANİYEDİR (≈1.79e9). Milisaniye gelirse (ileride) diye iki biçim de kabul edilir.
    return x / 1000 if x > 10**11 else x


def ts(x: float) -> str:
    return datetime.datetime.fromtimestamp(saniye(x)).strftime("%H:%M:%S")


def veri_dizini_bul(proje: Path) -> tuple[Path, int]:
    """Motor kuralı: proje dizininden yukarı, ilk `.axet-code` klasörü. Döner: (veri dizini, kaç üst)."""
    for i, d in enumerate([proje, *proje.parents]):
        if (d / VERI_DIZINI).is_dir():
            return d / VERI_DIZINI, i
    raise Olculemedi(f"{proje} ve üst dizinlerinde {VERI_DIZINI} klasörü yok")


def baglan(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise Olculemedi(f"{DB_ADI} yok: {db}")
    c = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)   # salt-okur: aXet açıkken DB'ye yazılmaz
    eksik = []
    for tablo, kolonlar in SEMA.items():
        var = {r[1] for r in c.execute(f"pragma table_info({tablo})")}
        eksik += [f"{tablo}.{k}" for k in sorted(kolonlar - var)]
    if eksik:
        c.close()
        raise Olculemedi(f"beklenen şema yok (aXet sürümü değişmiş olabilir): eksik {', '.join(eksik)}")
    return c


def mesajlar(c: sqlite3.Connection, sid: str) -> list[tuple[str, str, dict, float]]:
    out = []
    # Aynı saniyede birden çok mesaj olur (zaman damgası saniye) ⇒ ikinci anahtar rowid (ekleme sırası).
    for role, parts, ca in c.execute("select role,parts,created_at from messages where session_id=? "
                                     "order by created_at, rowid", (sid,)):
        try:
            parcalar = json.loads(parts)
        except ValueError:
            parcalar = []
        for x in parcalar if isinstance(parcalar, list) else []:
            d = x.get("data") if isinstance(x, dict) else None
            out.append((role, x.get("type") if isinstance(x, dict) else None, d if isinstance(d, dict) else {}, ca))
    return out


def sifir_hukmu(c: sqlite3.Connection, sid: str) -> dict:
    """§0 sırası: session_brief bash çağrısı ilk model metninden önce mi · ilk metnin ilk satırı kanarya mı."""
    m = mesajlar(c, sid)
    ilk_metin_i = next((i for i, (r, t, d, _) in enumerate(m)
                        if r == "assistant" and t == "text" and str(d.get("text", "")).strip()), None)
    brief_i = next((i for i, (r, t, d, _) in enumerate(m)
                    if t == "tool_call" and d.get("name") == "bash" and "session_brief" in str(d.get("input", ""))),
                   None)
    once = sum(1 for r, t, d, _ in m[:ilk_metin_i if ilk_metin_i is not None else len(m)] if t == "tool_call")
    ilk_satir = str(m[ilk_metin_i][2].get("text", "")).strip().splitlines()[0] if ilk_metin_i is not None else ""
    kanarya = KANARYA.match(ilk_satir)
    nedenler = []
    if ilk_metin_i is None:
        nedenler.append("model metni yok")
    if brief_i is None:
        nedenler.append("session_brief çağrısı yok")
    elif ilk_metin_i is not None and brief_i > ilk_metin_i:
        nedenler.append("session_brief ilk metinden sonra")
    if ilk_metin_i is not None and not kanarya:
        nedenler.append("kanarya yok")
    return dict(var=not nedenler, nedenler=nedenler, once=once, ilk_satir=ilk_satir, kanarya=kanarya,
                cagri=sum(1 for _, t, _, _ in m if t == "tool_call"), mesaj=m)


def log_satirlari(veri: Path, sid: str, bas: float, bit: float) -> list[str]:
    """İzin/ret satırları. Satırda `session_id` varsa YALNIZ kimlikle eşlenir ([kimlik]); yoksa oturumun zaman
    penceresiyle ([pencere] — eşzamanlı başka oturumun satırı da düşebilir, bu yüzden işaretlenir).
    Ölçüldü (2026-09-26): izin kararı satırlarının `session_id`'si DB'deki oturum kimliğiyle 237/237 eşleşti."""
    p = veri / LOG_YOLU
    if not p.is_file():
        return ["(log yok)"]
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(j, dict) or not RET.search(json.dumps(j, ensure_ascii=False)):
            continue
        zaman = str(j.get("time", ""))
        if j.get("session_id"):
            if j["session_id"] != sid:
                continue
            etiket = "[kimlik]"
        else:
            try:
                e = datetime.datetime.fromisoformat(zaman).timestamp()
            except ValueError:
                continue
            if not (bas - 2 <= e <= bit + 5):
                continue
            etiket = "[pencere]"
        kalan = {k: j[k] for k in j if k not in ("source", "time", "level")}
        out.append(f"{zaman[11:19]} {etiket} {json.dumps(kalan, ensure_ascii=False)[:260]}")
    return out


def tam_iz(c: sqlite3.Connection, veri: Path, sid: str, girinti: str = "", kok: bool = True) -> bool:
    title, ca = c.execute("select title,created_at from sessions where id=?", (sid,)).fetchone()
    print(f"{girinti}=== OTURUM {sid[:8]} · {title} · başlangıç {ts(ca)}")
    h = sifir_hukmu(c, sid)
    if kok:
        print(f"{girinti}§0 sırası: {'VAR' if h['var'] else 'YOK (' + ' · '.join(h['nedenler']) + ')'} · "
              f"ilk metinden önce {h['once']} araç çağrısı · "
              f"kanarya: {'VAR ' + str(h['kanarya'].groups()) if h['kanarya'] else 'YOK'}")
        print(f"{girinti}ilk satır: {h['ilk_satir'][:140]!r}")
    else:
        print(f"{girinti}alt oturum — §0 uygulanmaz (alt ajan çekirdeği görmez)")
    son = saniye(ca)
    for r, t, d, cat in h["mesaj"]:
        son = max(son, saniye(cat))
        if t == "text" and str(d.get("text", "")).strip():
            etiket = "KULLANICI" if r == "user" else "MODEL"
            print(f"{girinti}{ts(cat)} {etiket}: {str(d['text']).strip()[:600]!r}")
        elif t == "tool_call":
            print(f"{girinti}{ts(cat)}   → {d.get('name')} {str(d.get('input', ''))[:300]}")
        elif t == "tool_result":
            hata = " [HATA]" if d.get("is_error") else ""
            print(f"{girinti}{ts(cat)}   ← {d.get('name')}{hata} {str(d.get('content', ''))[:220]!r}")
    okunan = [p for (p,) in c.execute("select distinct path from read_files where session_id=?", (sid,))]
    print(f"{girinti}okunan dosyalar ({len(okunan)}): {okunan[:25]}")
    yazilan = [p for (p,) in c.execute("select distinct path from files where session_id=?", (sid,))]
    print(f"{girinti}yazılan/izlenen dosyalar ({len(yazilan)}): {yazilan[:25]}")
    print(f"{girinti}log (izin/ret satırları; [kimlik] = session_id eşleşmesi · [pencere] = zaman penceresi):")
    for s in log_satirlari(veri, sid, saniye(ca), son):
        print(f"{girinti}  {s}")
    for (cid,) in c.execute("select id from sessions where parent_session_id=? order by created_at, rowid", (sid,)):
        tam_iz(c, veri, cid, girinti + "    ", kok=False)
    return h["var"]


def oturum_sec(kokler: list, secim: str) -> str:
    if secim.isdigit():
        i = int(secim)
        if not 1 <= i <= len(kokler):
            raise Olculemedi(f"{i}. kök oturum yok ({len(kokler)} kök oturum var)")
        return kokler[i - 1][0]
    aday = [s for s, _, _ in kokler if s.startswith(secim)]
    if not aday:
        raise Olculemedi(f"'{secim}' önekiyle kök oturum yok")
    if len(aday) > 1:
        raise Kullanim(f"'{secim}' öneki belirsiz ({len(aday)} oturum): önek uzat")
    return aday[0]


def calis(ns: argparse.Namespace) -> int:
    proje = Path(ns.proje).resolve() if ns.proje else Path.cwd().resolve()
    if not proje.is_dir():
        raise Kullanim(f"proje dizini yok: {proje}")
    veri, ust = veri_dizini_bul(proje)
    print(f"veri dizini: {veri}" + (f"  (ÜST DİZİN — proje dizininden {ust} üstte; motor da bunu kullanır)"
                                    if ust else ""))
    c = baglan(veri / DB_ADI)
    try:
        kokler = c.execute("select id,title,created_at from sessions where parent_session_id is null "
                           "order by created_at desc, rowid desc").fetchall()
        if not ns.oturum:
            for i, (sid, title, ca) in enumerate(kokler[:ns.adet], 1):
                h = sifir_hukmu(c, sid)
                zaman = datetime.datetime.fromtimestamp(saniye(ca)).strftime("%m-%d %H:%M")
                print(f"{i:>2} {sid[:8]} {zaman} {str(title)[:28]:28} §0={'VAR' if h['var'] else 'YOK'} "
                      f"kanarya={'VAR' if h['kanarya'] else 'YOK'} araç={h['cagri']}")
            if not kokler:
                print("(kök oturum yok)")
            return 0
        return 0 if tam_iz(c, veri, oturum_sec(kokler, ns.oturum)) else 1
    finally:
        c.close()


class _Ayristirici(argparse.ArgumentParser):
    def error(self, message: str):  # argparse varsayılanı 2 döner; sözleşmede kullanım = 3
        raise Kullanim(message)


def main(argv: list[str] | None = None) -> int:
    ap = _Ayristirici(description="aXet oturum izi: oturum DB'si + log (model beyanı değil, motorun kaydı)")
    ap.add_argument("--proje", help="aXet'in açıldığı proje dizini (vars. bulunulan dizin)")
    ap.add_argument("--oturum", help="kök oturum sıra no (1 = en yeni) ya da kimlik öneki")
    ap.add_argument("--adet", type=int, default=10, help="özet listesinde kaç kök oturum (vars. 10)")
    try:
        kod = calis(ap.parse_args(argv))
    except Kullanim as e:
        print(f"KULLANIM: {e}", file=sys.stderr)
        kod = 3
    except (Olculemedi, sqlite3.DatabaseError) as e:
        print(f"ÖLÇÜLEMEDİ: {e}", file=sys.stderr)
        kod = 2
    for s in KAPSAM:
        print(s)
    return kod


if __name__ == "__main__":
    sys.exit(main())
