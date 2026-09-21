#!/usr/bin/env python3
"""Yayın provası: aday yayını GERÇEK public geçmişin üstüne kurar ve gerçek `%guncelle` motorunu
temiz tüketici klonlarında baştan sona koşar (Z28, 2026-09-21).

⛔ NEDEN: birim testleri kuralları küçük yapay girdilerle tek tek dener; kullanıcının yaşadığı akışı
(gerçek eski yayın → gerçek aday, gerçek içerik) hiçbiri koşmuyordu. Ölçüldü (2026-09-21): iki yayın
kusuru bu boşluktan geçti — v0.4.0'da public ağaçta 20 kırmızı test (Z27) ve v0.4.1'de kapanışın
ürün dosyalarındaki `# =====` ayraçlarını "çakışma işareti" sanması. İkisini de kullanıcı buldu.

Ne yapar (sırayla):
  1. public depoyu geçici dizine klonlar, o klonda PUSH'u kapatır (push URL'si geçersiz yapılır);
  2. `yayin_hazirla` ile aday yayın commit'ini + etiketini YALNIZ o geçici klona kurar;
  3. her eski etiket için temiz bir tüketici klonu açar (`origin` = geçici public klon);
  4. motoru adayın `skills/guncelle/SKILL.md` MOTOR-CIKAR komutlarını AYNEN koşarak çıkarır ve
     GUNCELLE.md adım 2-14'ü
     etkileşimsiz koşar: onkontrol · hazirla · plan · sec --hepsi · olc once · uygula --otomatik ·
     ozel-adim · olc sonra · butunluk · kapanis;
  5. her adımın çıkış kodunu ve süresini basar; kapanış 0 değilse PROVA FAIL.

Bu araç geliştirme reposunu DEĞİŞTİRMEZ, hiçbir yere PUSH ETMEZ; kullanıcının global config'ine
dokunmaz (USERPROFILE/HOME/APPDATA/LOCALAPPDATA/XDG_CONFIG_HOME geçici dizinlere yönlendirilir).

CI kipi (varsayılan): yayının `ci-durum.json` kaydı SENTETİK "hepsi yeşil" yazılır — gerçek kullanıcının
yürüdüğü yol budur (yayın ancak CI yeşilken yapılır). `--tam-olcum` ile sentetik kayıt yazılmaz ve
motor testleri tüketici klonunda gerçekten koşar (yavaş yol).

Kullanım (template kökünden):
  python maintenance/yayin_provasi.py                          son yayın + v0.1.0'dan prova
  python maintenance/yayin_provasi.py --eski v0.3.0 --sakla    tek taban, iş dizini silinmez
Çıkış: 0 prova temiz ya da ATLANDI (aday etiket zaten yayında) · 1 prova FAIL · 2 kurulum hatası.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "maintenance"))
import yayin_hazirla as yh  # noqa: E402

ILK_ETIKET = "v0.1.0"
PUSH_KAPALI = "PROVA-PUSH-KAPALI"
PROVA_KIMLIGI = {"GIT_AUTHOR_NAME": "aXet prova", "GIT_COMMITTER_NAME": "aXet prova",
                 "GIT_AUTHOR_EMAIL": "0+prova" + yh.NOREPLY_SONEK,
                 "GIT_COMMITTER_EMAIL": "0+prova" + yh.NOREPLY_SONEK}


class ProvaHatasi(Exception):
    """Prova KURULAMADI (2) — ürün hakkında hüküm yok."""


def _git(*args: str, cwd: Path, kontrol: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if kontrol and r.returncode != 0:
        raise ProvaHatasi(f"git {' '.join(args)} (rc={r.returncode}): {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def sentetik_ci(kaynak_sha: str, etiket: str, mevcut: dict | None, kapali: bool) -> dict:
    """`yayin_hazirla.ci_durum_uret` yerine: asgari takımların hepsi yeşil (PROVA — gerçek CI değil)."""
    kayit = dict(mevcut or {})
    kayit[etiket] = {
        "kaynak_commit": kaynak_sha, "olcum_zamani": yh._simdi_iso(), "hepsi_yesil": True,
        "takimlar": [{"ad": t, "sonuc": "success"} for t in yh.CI_ASGARI_TAKIMLAR],
        "isletim_sistemi": "SENTETIK", "python": ["SENTETIK"],
        "not": "yayın provası — sentetik kayıt, gerçek CI hükmü DEĞİL (maintenance/yayin_provasi.py).",
    }
    return kayit


def aday_etiket() -> str:
    veri, hata = yh.yayinlar_oku(KOK / yh.YAYINLAR_YOLU)
    if hata or not veri.get("yayinlar"):
        raise ProvaHatasi(f"yayın kataloğu okunamadı: {hata or 'boş'}")
    return veri["yayinlar"][-1]["etiket"]


def public_klonla(kaynak: str, hedef: Path) -> None:
    _git("clone", "-q", kaynak, str(hedef), cwd=hedef.parent)
    _git("remote", "set-url", "--push", "origin", PUSH_KAPALI, cwd=hedef)


def adayi_kur(pub: Path, kaynak: str, tam_olcum: bool) -> int:
    """`yayin_hazirla`yı SÜREÇ İÇİNDE koşar (CI kaydını sentetikleştirebilmek için)."""
    eski_argv, eski_env, eski_ci = sys.argv, dict(os.environ), yh.ci_durum_uret
    sys.argv = ["yayin_hazirla.py", "--hedef", str(pub), "--origin", kaynak]
    if tam_olcum:
        sys.argv.append("--ci-durum-yok")
    else:
        yh.ci_durum_uret = sentetik_ci
    os.environ.update(PROVA_KIMLIGI)
    try:
        return yh.main()
    finally:
        sys.argv, yh.ci_durum_uret = eski_argv, eski_ci
        os.environ.clear()
        os.environ.update(eski_env)


def korumali_ortam(kum: Path) -> dict:
    """Motor ve alt süreçleri kullanıcının global durumuna DOKUNAMASIN."""
    env = dict(os.environ)
    for ad in ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME", "TMP", "TEMP",
               "TMPDIR"):
        d = kum / ad.lower()
        d.mkdir(parents=True, exist_ok=True)
        env[ad] = str(d)
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "GIT_TERMINAL_PROMPT": "0"})
    env.update(PROVA_KIMLIGI)
    return env


MOTOR_CIKAR = ("<!-- MOTOR-CIKAR:BASLA -->", "<!-- MOTOR-CIKAR:BITIR -->")

# Güncellenmiş klonun KENDİ `sap_stamp.denetle`si ile proje AGENTS.md damgası (doctor'ın check_stamp'ı
# da bunu çağırır, scripts/doctor.py). 0 = guncel · 1 = başka her durum (durum + ayrıntı basılır).
DAMGA_OLC = ("import sys; sys.path.insert(0, sys.argv[1]); import sap_stamp; "
             "st, ay = sap_stamp.denetle(open(sys.argv[2], encoding='utf-8').read()); "
             "print('damga:', st, ay); sys.exit(0 if st == 'guncel' else 1)")


def motor_komutlari(pub: Path) -> list[str]:
    """ADAYIN `skills/guncelle/SKILL.md` MOTOR-CIKAR bloğu — aXet'in çalıştırdığı komutların ta kendisi.

    Prova motoru kendi yöntemiyle çıkarmaz: belgedeki komutlar bozulursa (yanlış yol, eksik
    klasör) kullanıcının `%guncelle`si ilk adımda düşer ⇒ prova da aynı yerde düşmelidir.
    """
    r = subprocess.run(["git", "show", "HEAD:skills/guncelle/SKILL.md"], cwd=pub,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or MOTOR_CIKAR[0] not in r.stdout or MOTOR_CIKAR[1] not in r.stdout:
        raise ProvaHatasi("adayda skills/guncelle/SKILL.md MOTOR-CIKAR bloğu okunamadı")
    blok = r.stdout.split(MOTOR_CIKAR[0], 1)[1].split(MOTOR_CIKAR[1], 1)[0]
    return [x.strip() for x in blok.splitlines()
            if x.strip() and not x.strip().startswith("```")]


def prova_kos(pub: Path, eski: str, is_dizini: Path) -> dict:
    """Tek taban etiketinden tam güncelleme akışı. Dönen kayıt: adımlar + hüküm.

    Her taban KENDİ kum ortamını alır: iki klon aynı global config'e kurulursa `doctor` ikisini
    birbirinin "yabancı klonu" sayar (ölçüldü, prova #2)."""
    env = korumali_ortam(is_dizini / f"kum-{eski}")
    kon = is_dizini / f"tuketici-{eski}"
    _git("clone", "-q", str(pub), str(kon), cwd=is_dizini)
    _git("reset", "-q", "--hard", eski, cwd=kon)
    proje = is_dizini / f"proje-{eski}"
    adimlar: list[dict] = []

    def kos(ad: str, argv: list[str], beklenen=(0,)) -> int:
        bas = time.monotonic()
        r = subprocess.run([sys.executable, *argv], cwd=kon, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=3600)
        sure = time.monotonic() - bas
        cikti = (r.stdout or "") + (r.stderr or "")
        adimlar.append({"ad": ad, "rc": r.returncode, "sure": round(sure, 1),
                        "tamam": r.returncode in beklenen, "cikti": cikti})
        isaret = "OK  " if r.returncode in beklenen else "FAIL"
        print(f"  [{isaret}] {ad:<22} rc={r.returncode}  {sure:6.1f} sn")
        for satir in cikti.splitlines():
            if satir.startswith(("[İKAME]", "[ÖLÇ]", "[KAPSANDI]", "DUR", "FAIL", "[FAIL]", "damga:")):
                print(f"         {satir[:220]}")
        return r.returncode

    def adim(ad: str, *argv: str, beklenen=(0,)) -> int:
        return kos(ad, [str(motor), "--klon", str(kon), "--beklenen-origin", str(pub), *argv],
                   beklenen)

    def proje_adim(ad: str, *argv: str, beklenen=(0,)) -> int:
        return kos(ad, [str(kon / "scripts" / "guncelle_proje.py"), "--proje", str(proje), *argv],
                   beklenen)

    print(f"\n== PROVA {eski} → aday ==")
    # Kullanıcının yolu: projeyi ESKİ sürümle açmış, sonra `%guncelle` + `%guncelle-proje` (Z29 —
    # iki araç ayrı ayrı test ediliyordu, ARKA ARKAYA hiç koşmamışlardı).
    # Gerçek kullanıcı `kur.ps1` ile KURULMUŞTUR (install.py global config yazar); kurulmamış klonda
    # bütünlük turundaki `doctor` "context_paths yok" diye FAIL verir (ölçüldü, prova #2) ⇒ bu
    # ürün kusuru değil, provanın temsil boşluğuydu.
    if kos("kurulum (eski sürüm)", [str(kon / "scripts" / "install.py")]) != 0:
        return {"eski": eski, "adimlar": adimlar, "hukum": "FAIL",
                "neden": "eski sürüm kurulamadı (install.py)"}
    # Motor, skill'in MOTOR-CIKAR komutlarıyla AYNEN çıkarılır (Z32).
    tmp = is_dizini / f"motor-{eski}"
    tmp.mkdir()
    for i, satir in enumerate(motor_komutlari(pub), 1):
        argv = shlex.split(satir.replace("<KLON>", kon.as_posix()).replace("<TMP>", tmp.as_posix()))
        if argv[0] == "python":
            argv = argv[1:]
        else:
            argv = ["-c", "import subprocess,sys; sys.exit(subprocess.call(sys.argv[1:]))", *argv]
        if kos(f"motor-cikar {i}", argv) != 0:
            return {"eski": eski, "adimlar": adimlar, "hukum": "FAIL",
                    "neden": f"skill MOTOR-CIKAR komutu {i} başarısız: {satir}"}
    motor = tmp / "scripts" / "guncelle.py"
    proje.mkdir()
    _git("init", "-q", "-b", "main", cwd=proje)
    if kos("yeni proje (eski sürüm)", [str(kon / "scripts" / "new_project.py"), str(proje),
                                        "--name", "PROVA", "--sap", "--no-next-steps"]) != 0:
        return {"eski": eski, "adimlar": adimlar, "hukum": "FAIL",
                "neden": "eski sürümle proje açılamadı"}
    akis = [("onkontrol", ("onkontrol",)), ("hazirla", ("hazirla",)), ("plan", ("plan",)),
            ("sec --hepsi", ("sec", "--hepsi")), ("olc once", ("olc", "--asama", "once")),
            ("uygula --otomatik", ("uygula", "--otomatik"))]
    for ad, argv in akis:
        if adim(ad, *argv) != 0:
            return {"eski": eski, "adimlar": adimlar, "hukum": "FAIL", "neden": f"{ad} başarısız"}

    plan = json.loads((kon / ".axet-guncelleme" / "plan.json").read_text(encoding="utf-8"))
    yargi = sorted({f["yol"] for k in plan.get("kalemler", []) for f in k.get("dosyalar", [])
                    if f.get("vaka") not in ("V1", "V2", "V5", "V6", "V1R")
                    and f.get("vaka") not in ("V0", "V3", "V2e", "V4e", "V5s", "V6x", "VKD")})
    if yargi:
        # Temiz (yerel değişikliksiz) tüketicide yargı vakası BEKLENMEZ: çıktıysa sınıflandırma kusuru.
        return {"eski": eski, "adimlar": adimlar, "hukum": "FAIL",
                "neden": f"temiz tüketicide {len(yargi)} yargı vakası: {', '.join(yargi[:8])}"}
    ozel = sorted({a for k in plan.get("kalemler", []) for a in k.get("ozel_adimlar", [])})
    for ad in ozel:
        adim(f"ozel-adim {ad}", "ozel-adim", ad)
    adim("olc sonra", "olc", "--asama", "sonra")
    adim("butunluk", "butunluk")
    rc = adim("kapanis", "kapanis")
    if rc == 0:
        proje_adim("proje onkontrol", "onkontrol")
        proje_adim("proje onay", "onay", "--kabul", "PROVA")
        # Z55: plan 1 ("güncel") dönse bile damga AŞAĞIDA ayrıca ölçülür — v0.5.0'da şablon güncelken
        # plan 1 dönüyor ve eski damga sessizce kalıyordu; prova yalnız plan rc'sine bakıyordu.
        if proje_adim("proje plan", "plan", beklenen=(0, 1)) == 0:
            proje_adim("proje uygula", "uygula", "--otomatik")
            proje_adim("proje kapanis", "kapanis")
        kos("proje damga = kanonik", ["-c", DAMGA_OLC, str(kon / "scripts"), str(proje / "AGENTS.md")])
    rapor = kon / ".axet-guncelleme" / "RAPOR.md"
    kalan = [a["ad"] for a in adimlar if not a["tamam"]]
    hukum = "TEMİZ" if rc == 0 and not kalan else "FAIL"
    return {"eski": eski, "adimlar": adimlar, "hukum": hukum, "rapor": rapor,
            "neden": ", ".join(kalan) if kalan else "",
            "sure": round(sum(a["sure"] for a in adimlar), 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kaynak", default=yh.RESMI_ORIGIN, help="public depo adresi (ya da yerel yol)")
    ap.add_argument("--eski", action="append",
                    help="taban etiket(ler)i; varsayılan: son yayınlanmış etiket + v0.1.0")
    ap.add_argument("--tam-olcum", action="store_true",
                    help="sentetik CI kaydı YAZMA ⇒ motor testleri tüketicide gerçekten koşar (yavaş)")
    ap.add_argument("--is-dizini", type=Path, help="varsayılan: sistem TMP altında yeni dizin")
    ap.add_argument("--sakla", action="store_true", help="iş dizinini silme (teşhis için)")
    a = ap.parse_args()

    is_dizini = (a.is_dizini or Path(tempfile.mkdtemp(prefix="axet-prova-"))).resolve()
    if is_dizini == KOK or KOK in is_dizini.parents:
        print("HATA: iş dizini geliştirme reposunun içinde olamaz.", file=sys.stderr)
        return 2
    is_dizini.mkdir(parents=True, exist_ok=True)
    try:
        etiket = aday_etiket()
        pub = is_dizini / "public"
        print(f"Public klon: {a.kaynak} → {pub}")
        public_klonla(a.kaynak, pub)
        if _git("tag", "-l", etiket, cwd=pub):
            print(f"PROVA ATLANDI: aday etiket `{etiket}` public'te ZATEN VAR — kataloğa yeni yayın "
                  "eklenmemiş, prova edilecek aday yok. (Ürün hakkında hüküm YOK.)")
            return 0
        yayinli = sorted(_git("tag", "-l", "v*", cwd=pub).split(), key=yh._surum_anahtari)
        if not yayinli:
            raise ProvaHatasi("public depoda yayın etiketi yok")
        tabanlar = a.eski or list(dict.fromkeys([yayinli[-1], ILK_ETIKET]))
        eksik = [t for t in tabanlar if t not in yayinli]
        if eksik:
            raise ProvaHatasi(f"taban etiket(ler) public'te yok: {', '.join(eksik)}")

        print(f"Aday: {etiket} · tabanlar: {', '.join(tabanlar)} · "
              f"CI kaydı: {'YOK (tam ölçüm)' if a.tam_olcum else 'SENTETİK yeşil'}")
        bas = time.monotonic()
        if adayi_kur(pub, a.kaynak, a.tam_olcum) != 0:
            print("PROVA FAIL: aday yayın kurulamadı (yayin_hazirla çıktısı yukarıda).")
            return 1
        print(f"Aday yayın commit'i kuruldu (yalnız {pub}, push KAPALI) · "
              f"{time.monotonic() - bas:.1f} sn")
        sonuclar = [prova_kos(pub, t, is_dizini) for t in tabanlar]
    except ProvaHatasi as e:
        print(f"PROVA KURULAMADI: {e}", file=sys.stderr)
        return 2
    finally:
        if a.sakla:
            print(f"İş dizini SAKLANDI: {is_dizini}")
        else:
            shutil.rmtree(is_dizini, ignore_errors=True)

    print("\n== PROVA SONUCU ==")
    for s in sonuclar:
        print(f"  {s['eski']} → {etiket}: {s['hukum']}"
              + (f" · {s['sure']} sn" if s.get("sure") is not None else "")
              + (f" · {s['neden']}" if s["neden"] else ""))
        if s["hukum"] != "TEMİZ":
            for adm in s["adimlar"]:
                if not adm["tamam"]:
                    print(f"\n--- {s['eski']} · {adm['ad']} çıktısı (son 60 satır) ---")
                    print("\n".join(adm["cikti"].splitlines()[-60:]))
    print("KAPSAM — bakılan: aday yayının public geçmişe kurulabilmesi (yayin_hazirla: tarama + "
          "kalem-diff kapsamı), her tabandan TEMİZ bir tüketici klonunda motorun adım 2-14'ü, "
          "kapanış hükmü = 0, temiz klonda yargı vakası çıkmaması; ardından eski sürümle açılmış "
          "bir SAP projesinde `guncelle_proje` onkontrol + onay + plan (+ plan 0 ise uygula --otomatik "
          "+ kapanış) ve SONRA proje AGENTS.md damgasının güncel klonun kanonik metniyle eşleşmesi "
          "(`sap_stamp.denetle`; Z55).")
    print("KAPSAM — bakılmayan: YEREL DEĞİŞİKLİKLİ tüketici (yargı vakaları, kartlar, isaretle), "
          "aXet modelinin GUNCELLE.md'yi doğru izlemesi, kur.ps1 ile kurulmuş gerçek makine durumu "
          "(global config, gerçek axet-code), `%guncelle-proje`de yargı vakaları (temiz projede beklenmez), "
          "`behavior_manifest.py generate` (kullanıcının terminalinde koşar; prova koşmaz), "
          + ("CI ikamesi yolu (--tam-olcum verildi)." if a.tam_olcum else
             "testlerin tüketicide gerçekten koşulması (sentetik CI kaydı ⇒ ölçümler İKAME edilir; "
             "o yol için --tam-olcum)."))
    return 0 if all(s["hukum"] == "TEMİZ" for s in sonuclar) else 1


if __name__ == "__main__":
    raise SystemExit(main())
