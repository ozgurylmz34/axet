#!/usr/bin/env python3
"""Public yayın kopyası hazırlar: dışlananları çıkarır, sızıntı taraması yapar, tek commit'lik yeni geçmiş kurar.

Bu araç geliştirme reposunu DEĞİŞTİRMEZ ve hiçbir yere PUSH ETMEZ. Push komutunu yalnız yazar.
Push geri alınamaz (public repo önbelleğe girer) ve ayrı kullanıcı onayı ister (IS-LISTESI Y2a / F).

Kullanım (template kökünden):
  python maintenance/yayin_hazirla.py --hedef <boş ya da olmayan klasör>              HEAD'in commit'li içeriği
  python maintenance/yayin_hazirla.py --hedef <klasör> --ref <dal|sha>                 başka bir commit
  python maintenance/yayin_hazirla.py --hedef <klasör> --calisma-agaci --yalniz-tara   commit'siz hâli dene (git kurmaz)
Çıkış kodu: 0 temiz ve (istenirse) commit kuruldu · 1 tarama bulgusu var (git kurulmadı) · 2 kullanım/git hatası.
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

# Public sürüme girmeyenler (IS-LISTESI Y2a kararı). Klasörler "/" ile biter.
DISLANANLAR = ["maintenance/", "docs/agentic-connectors.md", "docs/axet-davranis-olcumleri.md", "_lab/"]

ZORUNLU_DOSYALAR = ["LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "LICENSES/Apache-2.0.txt",
                    "README.md", "AGENTS.md", "kur.cmd", "kur.ps1", "yeni-proje.cmd"]

# (ad, desen, bayraklar). Sızıntı taraması 2026-09-14 raporundaki sınıflar + dışlanan dosya atıfları.
DESENLER = [
    ("şirket adı", r"ntt\s*data|nttdata|\bNTT\b", re.I),
    ("iç kullanıcı/dizin", r"tr\d{5}\b|C:\\Users\\(?!<)[A-Za-z]", re.I),
    ("iç repo adı", r"DEV_CORE|\bPROVA\b|ix-works|ix_doctor|TrakyaDokum", 0),
    ("müşteri izi", r"trakya", re.I),
    ("oturum bağlantısı", r"claude\.ai/code/session_", 0),
    ("dışlanan dosyaya atıf", r"maintenance/|agentic-connectors|axet-davranis-olcumleri", 0),
    ("gerçek alan adı örneği", r"your-sap-server\.com|//server\.com", 0),
]
IKILI_UZANTI = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".exe"}


def git(*args: str, cwd: Path = KOK, girdi: bytes | None = None) -> bytes:
    sonuc = subprocess.run(["git", *args], cwd=cwd, input=girdi, capture_output=True)
    if sonuc.returncode != 0:
        raise SystemExit(f"HATA: git {' '.join(args)}: {sonuc.stderr.decode(errors='replace').strip()}")
    return sonuc.stdout


def dislanan_mi(yol: str) -> bool:
    return any(yol == d or (d.endswith("/") and yol.startswith(d)) for d in DISLANANLAR)


def kopyala(hedef: Path, ref: str, calisma_agaci: bool) -> list[str]:
    if calisma_agaci:
        yollar = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
        yollar = sorted({y for y in yollar if y and (KOK / y).is_file()})
        for y in yollar:
            if not dislanan_mi(y):
                (hedef / y).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(KOK / y, hedef / y)
        return [y for y in yollar if not dislanan_mi(y)]
    arsiv = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", ref)))
    alinan = []
    for uye in arsiv.getmembers():
        if uye.isfile() and not dislanan_mi(uye.name):
            arsiv.extract(uye, hedef)
            alinan.append(uye.name)
    return sorted(alinan)


def tara(hedef: Path, yollar: list[str]) -> list[str]:
    bulgular = [f"EKSİK zorunlu dosya: {z}" for z in ZORUNLU_DOSYALAR if not (hedef / z).is_file()]
    notice = hedef / "NOTICE"
    if notice.is_file():
        for satir in notice.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s+- (\S+)", satir)
            if m and not list(hedef.glob(m.group(1).rstrip("/"))):
                bulgular.append(f"NOTICE listesindeki yol yok: {m.group(1)}")
    for y in yollar:
        if Path(y).suffix.lower() in IKILI_UZANTI:
            continue
        try:
            metin = (hedef / y).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bulgular.append(f"OKUNAMADI (utf-8 değil, taranmadı): {y}")
            continue
        for no, satir in enumerate(metin.splitlines(), 1):
            for ad, desen, bayrak in DESENLER:
                if re.search(desen, satir, bayrak):
                    bulgular.append(f"{ad}: {y}:{no}: {satir.strip()[:140]}")
    return bulgular


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hedef", required=True, type=Path)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--calisma-agaci", action="store_true", help="commit'siz çalışma ağacını kopyala (yalnız deneme)")
    ap.add_argument("--yalniz-tara", action="store_true", help="kopyala + tara; git geçmişi kurma")
    ap.add_argument("--mesaj", default="İlk public sürüm")
    a = ap.parse_args()

    hedef = a.hedef.resolve()
    if hedef == KOK or KOK in hedef.parents:
        print("HATA: hedef geliştirme reposunun içinde olamaz.", file=sys.stderr)
        return 2
    if hedef.exists() and any(hedef.iterdir()):
        print(f"HATA: hedef boş değil: {hedef} (üzerine yazılmaz)", file=sys.stderr)
        return 2
    if a.calisma_agaci and not a.yalniz_tara:
        print("HATA: --calisma-agaci yalnız --yalniz-tara ile kullanılır (commit'siz içerik yayınlanmaz).", file=sys.stderr)
        return 2
    hedef.mkdir(parents=True, exist_ok=True)

    kaynak = "çalışma ağacı" if a.calisma_agaci else f"{a.ref} ({git('rev-parse', '--short', a.ref).decode().strip()})"
    yollar = kopyala(hedef, a.ref, a.calisma_agaci)
    bulgular = tara(hedef, yollar)

    print(f"Kaynak: {kaynak} → {hedef}")
    print(f"Kopyalanan dosya: {len(yollar)} · dışlananlar: {', '.join(DISLANANLAR)}")
    print("KAPSAM — bakılan: zorunlu dosyalar, NOTICE yolları, utf-8 metin dosyalarında şu sınıflar: "
          + ", ".join(d[0] for d in DESENLER))
    print("KAPSAM — bakılmayan: ikili dosyalar (" + ", ".join(sorted(IKILI_UZANTI)) + "), kişi adları sözlüğü, "
          "SAP host/SID/client serbest metni, anlamsal iç bilgi (ör. aXet iç davranış anlatımı), lisans uyumu. "
          "Bu tarama tam sızıntı denetiminin yerine geçmez.")
    if bulgular:
        print(f"\nBULGU: {len(bulgular)}")
        for b in bulgular:
            print("  " + b)
        print("\nGit geçmişi kurulmadı.")
        return 1
    print("BULGU: 0 (yalnız yukarıdaki kapsamda)")
    if a.yalniz_tara:
        return 0

    git("init", "-q", "-b", "main", cwd=hedef)
    git("add", "-A", cwd=hedef)
    git("commit", "-q", "-F", "-", cwd=hedef, girdi=a.mesaj.encode("utf-8"))
    print(f"Tek commit'lik geçmiş kuruldu: {git('log', '--oneline', cwd=hedef).decode().strip()}")
    print("PUSH YAPILMADI. Ayrı onaydan sonra kullanıcının kendi terminalinde:\n"
          f"  git -C \"{hedef}\" remote add origin https://github.com/ozgurylmz34/axet-template.git\n"
          f"  git -C \"{hedef}\" push -u origin main")
    return 0


if __name__ == "__main__":
    sys.exit(main())
