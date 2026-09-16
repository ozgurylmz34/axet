#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PR birlestirme yardimcisi — CI'yi KENDI dogrular, sonra squash-merge eder.

    python scripts/merge_pr.py --repo <ORG>/<REPO> --pr <N> [--squash] [--admin] [--deneme]

NEDEN VAR: `gh pr merge --admin` kirmizi CI'yi de SESSIZCE birlestirir ve merge GERI
ALINAMAZ. Bu arac, birlestirmeden once statusCheckRollup'i okur; bekleyen ya da basarisiz
kontrol varsa DURUR. `--admin` yalnizca "onaylayan yok" sartini asmak icindir — CI'yi
atlatmak icin DEGIL, ve bu arac onu atlatmaya izin vermez.

KAPSAM BEYANI — bu arac NEYE BAKMAZ:
  * PR icerigi: diff'i okumaz, inceleme yapmaz (bug gate'in isi).
  * Dal korumasi kurallari: GitHub'in kendi kurallarini sorgulamaz; yalnizca kontrol
    sonuclarina bakar. Koruma yanlis yapilandirilmissa bunu GORMEZ.
  * Merge sonrasi durum: birlestirmeden sonra dalin silinip silinmedigini denetlemez.
  * Hic kontrol TANIMLANMAMIS bir repoda "0 kontrol" cikar — bu arac bunu BOSLUK sayar
    ve durur (bkz. --kontrolsuz-devam).

Cikis: 0 birlestirildi (ya da --deneme ile dogrulandi) · 1 durduruldu · 2 kullanim hatasi.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

BEKLEYEN = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "EXPECTED", ""}
BASARILI = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def gh(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def kontrol_ozeti(rollup: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """statusCheckRollup -> (basarili, bekleyen, basarisiz) ad listeleri.

    Iki bicim vardir: CheckRun (`status` + `conclusion`) ve StatusContext (`state`).
    Ikisi de karsilanir; taninmayan bicim BASARISIZ sayilir (fail-closed) — cunku
    "taninmadi" ile "gecti" ayni sey degildir.
    """
    ok: list[str] = []
    bekleyen: list[str] = []
    kotu: list[str] = []
    for c in rollup or []:
        ad = c.get("name") or c.get("context") or "<adsiz>"
        if "conclusion" in c or "status" in c:
            durum = (c.get("status") or "").upper()
            sonuc = (c.get("conclusion") or "").upper()
            if durum and durum != "COMPLETED":
                bekleyen.append(ad)
            elif sonuc in BASARILI:
                ok.append(ad)
            else:
                kotu.append(f"{ad} ({sonuc or 'sonucsuz'})")
        elif "state" in c:
            st = (c.get("state") or "").upper()
            if st in BEKLEYEN:
                bekleyen.append(ad)
            elif st in BASARILI:
                ok.append(ad)
            else:
                kotu.append(f"{ad} ({st})")
        else:
            kotu.append(f"{ad} (taninmayan kontrol bicimi)")
    return ok, bekleyen, kotu


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CI'yi dogrulayip PR birlestirir")
    ap.add_argument("--repo", required=True, help="<ORG>/<REPO> — ZORUNLU (cwd'den tahmin YOK)")
    ap.add_argument("--pr", required=True, help="PR numarasi")
    ap.add_argument("--squash", action="store_true", default=True, help="squash merge (varsayilan)")
    ap.add_argument("--merge", action="store_true", help="squash yerine duz merge")
    ap.add_argument("--admin", action="store_true", help="yalnizca 'onaylayan yok' sartini asar")
    ap.add_argument("--deneme", action="store_true", help="yalnizca dogrula, BIRLESTIRME")
    ap.add_argument("--kontrolsuz-devam", action="store_true",
                    help="repoda hic kontrol tanimli degilse yine de birlestir (bilincli)")
    a = ap.parse_args(argv)

    if "/" not in a.repo:
        print("HATA: --repo <ORG>/<REPO> bicimindedir.", file=sys.stderr)
        return 2

    rc, out, err = gh(["pr", "view", a.pr, "--repo", a.repo,
                       "--json", "number,title,state,isDraft,mergeable,statusCheckRollup"])
    if rc != 0:
        print(f"HATA: PR okunamadi — {err.strip()}", file=sys.stderr)
        return 1
    pr = json.loads(out)

    print(f"PR #{pr.get('number')} — {pr.get('title')}")
    if pr.get("state") != "OPEN":
        print(f"DURDU: PR durumu {pr.get('state')} (acik degil).")
        return 1
    if pr.get("isDraft"):
        print("DURDU: PR taslak (draft).")
        return 1

    ok, bekleyen, kotu = kontrol_ozeti(pr.get("statusCheckRollup") or [])
    print(f"Kontroller: {len(ok)} basarili · {len(bekleyen)} bekleyen · {len(kotu)} basarisiz")
    for ad in kotu:
        print(f"  BASARISIZ: {ad}")
    for ad in bekleyen:
        print(f"  BEKLIYOR:  {ad}")

    if kotu:
        print("DURDU: basarisiz kontrol var. --admin bunu ASMAZ (bilincli).")
        return 1
    if bekleyen:
        print("DURDU: bekleyen kontrol var; bitmesini bekle.")
        return 1
    if not ok and not a.kontrolsuz_devam:
        print("DURDU: repoda hic kontrol tanimli degil — '0 kontrol' YESIL DEGILDIR. "
              "Bilincliyse --kontrolsuz-devam ver.")
        return 1

    mergeable = pr.get("mergeable")
    if mergeable == "CONFLICTING":
        print("DURDU: PR CONFLICTING — once dali main uzerine guncelle.")
        return 1
    if mergeable != "MERGEABLE":
        print(f"NOT: mergeable = {mergeable!r} (OLCULEMEDI sayiliyor; gh yine de reddedebilir).")

    if a.deneme:
        print("DENEME: dogrulama gecti, birlestirilmedi.")
        return 0

    komut = ["pr", "merge", a.pr, "--repo", a.repo, "--merge" if a.merge else "--squash"]
    if a.admin:
        komut.append("--admin")
    rc, out, err = gh(komut)
    print(out.strip() or err.strip())
    if rc != 0:
        print("DURDU: birlestirme basarisiz.", file=sys.stderr)
        return 1
    print("Birlestirildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
