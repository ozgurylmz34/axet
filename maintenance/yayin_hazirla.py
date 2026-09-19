#!/usr/bin/env python3
"""Public yayın kopyası hazırlar: dışlananları çıkarır, sızıntı taraması yapar, yayın kalemlerini doğrular,
CHANGELOG.md üretir, tek commit + etiket atar.

Bu araç geliştirme reposunu DEĞİŞTİRMEZ ve hiçbir yere PUSH ETMEZ. Push komutunu yalnız yazar.
Push geri alınamaz (public repo önbelleğe girer) ve ayrı kullanıcı onayı ister (IS-LISTESI Y2a / F).

Kullanım (template kökünden):
  python maintenance/yayin_hazirla.py --hedef <klasör> --calisma-agaci --yalniz-tara   commit'siz hâli dene (git kurmaz)
  python maintenance/yayin_hazirla.py --hedef <klasör> --yalniz-tara                   HEAD'in commit'li içeriğini tara
  python maintenance/yayin_hazirla.py --yalniz-dogrula                                 yalnız guncelle/yayinlar.json şeması
  python maintenance/yayin_hazirla.py --hedef <boş klasör> --ilk                       İLK yayın: git init + commit + etiket
  python maintenance/yayin_hazirla.py --hedef <public klon>                            SONRAKİ yayın: var olan klona yaz
Çıkış kodu: 0 temiz (ve istenirse commit kuruldu) · 1 BLOCKER bulgu ya da yayın doğrulaması FAIL (git kurulmadı) ·
2 kullanım/git hatası.

Tarama iki şiddet üretir (D16, 2026-09-17): BLOCKER = bilgi sızıntısı, çıkışı düşürür · WARNING = tüketici
klonunda kırık kalacak işaretçi, yalnız listelenir. Şiddet tablosu DESENLER'dedir.

Yayın kalemleri (TASARIM §11, P7): `guncelle/yayinlar.json` yapısal değişiklik listesidir; tüketici motoru
(`scripts/guncelle.py:361`) onu `origin/main:guncelle/yayinlar.json` olarak okur ve kalem-dosya eşlemesini
oradan alır. Bu araç o dosyayı ŞEMA + DİFF KAPSAMI olarak doğrular: yayın diff'indeki her dosya en az bir
kaleme ait olmalı, kalemdeki her dosya gerçekten değişmiş olmalı. Değilse commit yok.
"""
from __future__ import annotations

import argparse
import io
import json
import os
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

# Yayın anında ÜRETİLEN / normalize edilen dosyalar: kalem-dosya eşlemesinden MUAFtırlar, çünkü
# bakımcının elle dokunduğu bir değişiklik değil, bu aracın çıktısıdırlar. Muafiyet KAPSAM'da basılır.
URETILEN_DOSYALAR = ("CHANGELOG.md", "guncelle/yayinlar.json")
YAYINLAR_YOLU = "guncelle/yayinlar.json"
CHANGELOG_YOLU = "CHANGELOG.md"
RESMI_ORIGIN = "https://github.com/ozgurylmz34/axet-template.git"

TURLER = ("duzeltme", "yetenek", "kural", "guvenlik")
TUR_ETIKETI = {"duzeltme": "düzeltme", "yetenek": "yetenek", "kural": "kural", "guvenlik": "güvenlik"}
ETIKET_BICIMI = re.compile(r"^v\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?$")
TARIH_BICIMI = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SURUM_BICIMI = re.compile(r"^\d+(?:\.\d+)*$")
KALEM_TRAILER = "Guncelleme-Kalemi"

BLOCKER, WARNING = "BLOCKER", "WARNING"

# (şiddet, ad, desen, bayraklar). Sınıflar 2026-09-14 sızıntı raporundan; şiddet ayrımı D16 (2026-09-17).
#   BLOCKER = bilgi sızıntısı -> çıkış 1, git geçmişi kurulmaz.
#   WARNING = tüketici klonunda kırık kalacak işaretçi (belge kalitesi sorunu) -> listelenir, ÇIKIŞI DEĞİŞTİRMEZ.
DESENLER = [
    (BLOCKER, "şirket adı", r"ntt\s*data|nttdata|\bNTT\b", re.I),
    # C:\Users\ (D16): gerçek kullanıcı adı = en az 3 karakter + yer tutucu DEĞİL. Muaf olanlar: `<...>`
    # biçimi, 1-2 karakterlik adlar (`C:\Users\u`) ve yer-tutucu sözcükler (örnek/kullanıcı/user/example...).
    # İki körlük 2026-09-17'de ÖLÇÜLEREK kapatıldı (ikisi de `tests/test_kur.py` fixture'ında gerçek bir ad
    # taşıyordu): (1) harf sınıfı artık UNICODE ([^\W\d_]) — eski `[A-Za-z]` ASCII olduğu için `C:\Users\Özgür`
    # gibi Türkçe karakterli adlar görünmüyordu (2) her iki bölü işareti ([\\/]) — `C:/Users/...` biçimi kaçıyordu.
    (BLOCKER, "iç kullanıcı/dizin",
     r"tr\d{5}\b|C:[\\/]Users[\\/](?!<)"
     r"(?!(?:örnek|ornek|kullanıcı|kullanici|user|username|example|sample)\b)[^\W\d_][\w.-]{2,}", re.I),
    (BLOCKER, "iç repo adı", r"DEV_CORE|\bPROVA\b|ix-works|ix_doctor|TrakyaDokum", 0),
    (BLOCKER, "müşteri izi", r"trakya", re.I),
    (BLOCKER, "oturum bağlantısı", r"claude\.ai/code/session_", 0),
    (BLOCKER, "gerçek alan adı örneği", r"your-sap-server\.com|//server\.com", 0),
    # Yalnız MARKDOWN LİNK biçimindeki atıf (D16): tüketici klonunda dangling olan şey linktir; yorum
    # satırındaki kaynak atfı, ters-tırnaklı dosya adı ya da bir sınıf globu tüketiciyi hiçbir yere götürmez.
    (WARNING, "dışlanan dosyaya atıf",
     r"\]\([^)\s]*(?:maintenance/|agentic-connectors|axet-davranis-olcumleri)", 0),
]
IKILI_UZANTI = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".exe"}


def git(*args: str, cwd: Path = KOK, girdi: bytes | None = None) -> bytes:
    sonuc = subprocess.run(["git", *args], cwd=cwd, input=girdi, capture_output=True)
    if sonuc.returncode != 0:
        raise SystemExit(f"HATA: git {' '.join(args)}: {sonuc.stderr.decode(errors='replace').strip()}")
    return sonuc.stdout


def git_sessiz(*args: str, cwd: Path = KOK) -> tuple[int, str]:
    """Başarısızlığı SystemExit'e çevirmez — varlık sorgularında kullanılır."""
    s = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    return s.returncode, s.stdout.decode(errors="replace").strip()


def dislanan_mi(yol: str) -> bool:
    return any(yol == d or (d.endswith("/") and yol.startswith(d)) for d in DISLANANLAR)


NOREPLY_SONEK = "@users.noreply.github.com"


def kimlik_sorunlari(cwd: Path) -> list[str]:
    """Yayın commit'inin ETKİN yazar/committer e-postası noreply değilse sorun listesi (yayın ⓐ, ölçüldü 2026-09-18:
    yayın provasında commit yazarı kurumsal adres çıktı; tarama yalnız dosya İÇERİĞİNE bakıyordu).

    `git var` ortam değişkenlerini (GIT_AUTHOR_EMAIL …) ve config'i birlikte çözer — commit'in kullanacağı kimliğin
    ta kendisi. GIT_CEILING_DIRECTORIES: `--ilk`te hedef henüz depo değil; üst dizindeki başka bir deponun yerel
    config'i okunmasın. E-posta ÇIKTIYA BASILMAZ (kimlik izi log'a da düşmesin); yalnız 'noreply değil' denir."""
    ortam = dict(os.environ, GIT_CEILING_DIRECTORIES=str(cwd.parent))
    sorunlar = []
    for ad in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        r = subprocess.run(["git", "var", ad], cwd=cwd, env=ortam, capture_output=True)
        if r.returncode != 0:
            sorunlar.append(f"{ad}: okunamadı ({r.stderr.decode(errors='replace').strip()})")
            continue
        m = re.search(r"<([^>]*)>", r.stdout.decode(errors="replace"))
        if not (m and m.group(1).lower().endswith(NOREPLY_SONEK)):
            sorunlar.append(f"{ad}: e-posta GitHub noreply adresi değil")
    return sorunlar


def kopya_hatasi(yol: Path, e: OSError) -> SystemExit:
    """Kopyalama OSError'ını ham traceback yerine anlamlı bir HATA'ya çevirir (yayın ⓑ, ölçüldü 2026-09-18:
    uzun hedef yolunda ham FileNotFoundError basılıyordu; sebebin MAX_PATH olduğu okunamıyordu)."""
    ipucu = ""
    if len(str(yol)) >= 260:
        ipucu = (f" Yol {len(str(yol))} karakter: Windows'un 260 karakter sınırı (MAX_PATH) aşılmış olabilir —"
                 " hedefi kısa bir klasöre ver (örn. C:\\yayin).")
    return SystemExit(f"HATA: kopyalanamadı: {yol} ({type(e).__name__}: {e}).{ipucu}")


def kopyala(hedef: Path, ref: str, calisma_agaci: bool) -> list[str]:
    if calisma_agaci:
        yollar = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
        yollar = sorted({y for y in yollar if y and (KOK / y).is_file()})
        for y in yollar:
            if not dislanan_mi(y):
                try:
                    (hedef / y).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(KOK / y, hedef / y)
                except OSError as e:
                    raise kopya_hatasi(hedef / y, e) from e
        return [y for y in yollar if not dislanan_mi(y)]
    arsiv = tarfile.open(fileobj=io.BytesIO(git("archive", "--format=tar", ref)))
    alinan = []
    for uye in arsiv.getmembers():
        if uye.isfile() and not dislanan_mi(uye.name):
            try:
                arsiv.extract(uye, hedef)
            except OSError as e:
                raise kopya_hatasi(hedef / uye.name, e) from e
            alinan.append(uye.name)
    return sorted(alinan)


def tara(hedef: Path, yollar: list[str]) -> list[tuple[str, str]]:
    """(şiddet, metin) çiftleri döner. Yapısal eksikler (zorunlu dosya, NOTICE yolu, okunamayan dosya) BLOCKER'dır."""
    bulgular = [(BLOCKER, f"EKSİK zorunlu dosya: {z}") for z in ZORUNLU_DOSYALAR if not (hedef / z).is_file()]
    notice = hedef / "NOTICE"
    if notice.is_file():
        for satir in notice.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s+- (\S+)", satir)
            if m and not list(hedef.glob(m.group(1).rstrip("/"))):
                bulgular.append((BLOCKER, f"NOTICE listesindeki yol yok: {m.group(1)}"))
    for y in yollar:
        if Path(y).suffix.lower() in IKILI_UZANTI:
            continue
        try:
            metin = (hedef / y).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bulgular.append((BLOCKER, f"OKUNAMADI (utf-8 değil, taranmadı): {y}"))
            continue
        for no, satir in enumerate(metin.splitlines(), 1):
            for siddet, ad, desen, bayrak in DESENLER:
                if re.search(desen, satir, bayrak):
                    bulgular.append((siddet, f"{ad}: {y}:{no}: {satir.strip()[:140]}"))
    return bulgular


# =====================================================================================================
# YAYIN KALEMLERİ — guncelle/yayinlar.json (TASARIM §11)
# =====================================================================================================
def miras_uygula(veri: dict) -> dict:
    """Yayın düzeyindeki `min_axet`'i kalemlere MİRAS ettirir (kalemdeki açık değer kazanır).

    Neden: tüketici motoru yalnız KALEM düzeyini okur (`scripts/guncelle.py:601`
    `kalem.get("min_axet")`). Yayın düzeyine yazılmış bir değer normalize edilmezse motorda
    SESSİZCE düşerdi. Kanonik düzey kalemdir; yayın düzeyi yalnız o yayının varsayılanıdır.
    Normalizasyon PUBLIC KOPYADA yapılır — geliştirme reposu değiştirilmez.
    """
    for yayin in veri.get("yayinlar", []):
        varsayilan = yayin.get("min_axet")
        if varsayilan is None:
            continue
        for kalem in yayin.get("kalemler", []):
            kalem.setdefault("min_axet", varsayilan)
    return veri


def _metin_mi(x) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _liste_mi(x, bos_olabilir: bool = True) -> bool:
    return isinstance(x, list) and all(_metin_mi(e) for e in x) and (bos_olabilir or bool(x))


def _kalem_bul(yayinlar: list, kid: str) -> dict | None:
    for y in yayinlar:
        if isinstance(y, dict):
            for k in y.get("kalemler", []) or []:
                if isinstance(k, dict) and k.get("id") == kid:
                    return k
    return None


def _surum_anahtari(etiket: str) -> tuple:
    return tuple(int(p) for p in re.findall(r"\d+", etiket or "")) or (0,)


def sema_dogrula(veri) -> list[str]:
    """`yayinlar.json` şeması. Alan adları `scripts/guncelle.py`'nin OKUDUĞU adlardır (koddan doğrulandı)."""
    s: list[str] = []
    if not isinstance(veri, dict):
        return ["şema: kök nesne bir JSON object olmalı"]
    if veri.get("surum") != 1:
        s.append(f"şema: kök `surum` 1 olmalı (bulunan: {veri.get('surum')!r})")
    yayinlar = veri.get("yayinlar")
    if not isinstance(yayinlar, list):
        return s + ["şema: kök `yayinlar` bir liste olmalı"]

    tum_kalemler: dict[str, str] = {}      # kalem id -> etiket
    kalem_sirasi: list[str] = []
    gorulen_etiket: list[str] = []
    for i, yayin in enumerate(yayinlar):
        yer = f"yayinlar[{i}]"
        if not isinstance(yayin, dict):
            s.append(f"şema: {yer} bir object olmalı")
            continue
        etiket = yayin.get("etiket")
        if not _metin_mi(etiket) or not ETIKET_BICIMI.match(etiket):
            s.append(f"şema: {yer}.etiket `vX.Y.Z` biçiminde olmalı (bulunan: {etiket!r})")
            etiket = str(etiket)
        if etiket in gorulen_etiket:
            s.append(f"şema: {yer}.etiket yinelenmiş: {etiket}")
        gorulen_etiket.append(etiket)
        if not _metin_mi(yayin.get("tarih")) or not TARIH_BICIMI.match(str(yayin.get("tarih"))):
            s.append(f"şema: {yer}.tarih YYYY-MM-DD olmalı (bulunan: {yayin.get('tarih')!r})")
        if yayin.get("min_axet") is not None and not SURUM_BICIMI.match(str(yayin.get("min_axet"))):
            s.append(f"şema: {yer}.min_axet noktalı sayı olmalı (bulunan: {yayin.get('min_axet')!r})")
        if "gecmis_yeniden_yazildi" in yayin and not isinstance(yayin["gecmis_yeniden_yazildi"], bool):
            s.append(f"şema: {yer}.gecmis_yeniden_yazildi bool olmalı")
        kalemler = yayin.get("kalemler")
        if not isinstance(kalemler, list) or not kalemler:
            s.append(f"şema: {yer}.kalemler boş olmayan bir liste olmalı")
            continue
        for j, kalem in enumerate(kalemler):
            kyer = f"{yer}.kalemler[{j}]"
            if not isinstance(kalem, dict):
                s.append(f"şema: {kyer} bir object olmalı")
                continue
            kid = kalem.get("id")
            if not _metin_mi(kid):
                s.append(f"şema: {kyer}.id boş olmayan metin olmalı")
                continue
            if kid in tum_kalemler:
                s.append(f"şema: kalem id yinelenmiş: {kid} ({tum_kalemler[kid]} ve {etiket})")
            tum_kalemler[kid] = etiket
            kalem_sirasi.append(kid)
            if not _metin_mi(kalem.get("baslik")):
                s.append(f"şema: {kyer}({kid}).baslik boş olamaz")
            if not _metin_mi(kalem.get("neden")):
                s.append(f"şema: {kyer}({kid}).neden boş olamaz (CHANGELOG'un 'neden' satırı)")
            tur = kalem.get("tur")
            if tur not in TURLER:
                s.append(f"şema: {kyer}({kid}).tur {TURLER} içinden olmalı (bulunan: {tur!r})")
            if not isinstance(kalem.get("kritik"), bool):
                s.append(f"şema: {kyer}({kid}).kritik bool olmalı")
            if tur == "guvenlik" and kalem.get("kritik") is not True:
                s.append(f"şema: {kyer}({kid}) tur=guvenlik ise kritik:true zorunlu (TASARIM §11 / Q3)")
            if not _liste_mi(kalem.get("dosyalar"), bos_olabilir=False):
                s.append(f"şema: {kyer}({kid}).dosyalar boş olmayan yol listesi olmalı")
            else:
                dosyalar = kalem["dosyalar"]
                if len(set(dosyalar)) != len(dosyalar):
                    s.append(f"şema: {kyer}({kid}).dosyalar yinelenen yol içeriyor")
                for d in dosyalar:
                    if d.startswith("/") or "\\" in d or ".." in d.split("/"):
                        s.append(f"şema: {kyer}({kid}).dosyalar yolu göreli/posix olmalı: {d}")
                    if dislanan_mi(d):
                        s.append(f"şema: {kyer}({kid}).dosyalar public'e girmeyen yolu bildiriyor: {d}")
                    if d in URETILEN_DOSYALAR:
                        s.append(f"şema: {kyer}({kid}).dosyalar üretilen dosyayı bildiriyor: {d} "
                                 f"(bu dosyalar yayın aracının çıktısıdır, kaleme ait değildir)")
            if not _liste_mi(kalem.get("gerektirir")):
                s.append(f"şema: {kyer}({kid}).gerektirir metin listesi olmalı")
            if not _liste_mi(kalem.get("test")):
                s.append(f"şema: {kyer}({kid}).test metin listesi olmalı (boş olabilir)")
            if kalem.get("min_axet") is not None and not SURUM_BICIMI.match(str(kalem.get("min_axet"))):
                s.append(f"şema: {kyer}({kid}).min_axet noktalı sayı olmalı")

    # `gerektirir` ancak DAHA ÖNCE tanımlı bir kaleme işaret edebilir: bağımlılık zaten yayınlanmış
    # olmalıdır, yoksa tüketici onu hiçbir zaman seçemez (`scripts/guncelle.py:682` seçim tutarlılığı).
    for idx, kid in enumerate(kalem_sirasi):
        kalem = _kalem_bul(yayinlar, kid)
        if not isinstance(kalem, dict):
            continue
        for bag in kalem.get("gerektirir") or []:
            if bag == kid:
                s.append(f"şema: {kid}.gerektirir kendine işaret ediyor")
            elif bag not in tum_kalemler:
                s.append(f"şema: {kid}.gerektirir tanımsız kaleme işaret ediyor: {bag}")
            elif kalem_sirasi.index(bag) > idx:
                s.append(f"şema: {kid}.gerektirir SONRAKİ bir kaleme işaret ediyor: {bag} "
                         f"(bağımlılık daha önce yayınlanmış olmalı)")
    # Sürüm sırası: motor son girdiyi en yeni sayar (`scripts/guncelle.py:376-379` listeyi TERSTEN gezer).
    for a, b in zip(gorulen_etiket, gorulen_etiket[1:]):
        if _surum_anahtari(b) <= _surum_anahtari(a):
            s.append(f"şema: yayınlar eskiden yeniye sıralı olmalı — {a} sonrası {b} geliyor "
                     f"(motor son girdiyi en yeni sayar: scripts/guncelle.py:376)")
    return s


def kapsam_dogrula(yayin: dict, degisen: set[str]) -> list[str]:
    """TASARIM §11: diff'teki HER dosya en az 1 kaleme ait · kalemdeki her dosya gerçekten değişmiş."""
    beyan: dict[str, list[str]] = {}
    for kalem in yayin.get("kalemler", []):
        for yol in kalem.get("dosyalar", []):
            beyan.setdefault(yol, []).append(kalem.get("id", "?"))
    olculen = {y for y in degisen if y not in URETILEN_DOSYALAR}
    s = []
    for yol in sorted(olculen - set(beyan)):
        s.append(f"kapsam: eşlemesiz dosya (hiçbir kaleme ait değil): {yol}")
    for yol in sorted(set(beyan) - olculen):
        s.append(f"kapsam: kalemde bildirilen dosya bu yayında DEĞİŞMEMİŞ: {yol} "
                 f"(kalem: {', '.join(beyan[yol])})")
    return s


def changelog_uret(veri: dict) -> str:
    """CHANGELOG.md gövdesi: yeniden eskiye; kalem no · tür · neden · dosyalar · test · gerektirir."""
    sat = ["# Değişiklik günlüğü", "",
           "<!-- ÜRETİLEN DOSYA — elle düzenlemeyin. Kaynak: `guncelle/yayinlar.json` · "
           "üretici: `yayin_hazirla.py` (yayın anında). -->", "",
           "Her başlık bir yayın etiketidir (`git tag`). Kalem numaraları yayın commit'inin "
           f"`{KALEM_TRAILER}:` trailer'larıyla ve `%guncelle` planıyla AYNIDIR: bir kalemi seçmek, "
           "aşağıda o kalemin altında listelenen DOSYALARI almak demektir. Yayın başına tek commit "
           "atıldığı için (Q2) kalem seçimi yalnız bu eşlemeyle, dosya düzeyinde yapılabilir; "
           "aynı dosyaya dokunan kalemler birlikte alınır.", "",
           "★ = kritik kalem (`%guncelle` planında varsayılan olarak SEÇİLİ gelir).", ""]
    yayinlar = veri.get("yayinlar", [])
    if not yayinlar:
        sat += ["_Henüz yayın yok._", ""]
    for yayin in reversed(yayinlar):
        sat.append(f"## {yayin.get('etiket')} — {yayin.get('tarih')}")
        sat.append("")
        for kalem in yayin.get("kalemler", []):
            yildiz = "★ " if kalem.get("kritik") else ""
            tur = TUR_ETIKETI.get(kalem.get("tur", ""), kalem.get("tur", ""))
            sat.append(f"### {yildiz}{kalem.get('id')} · {kalem.get('baslik')} ({tur})")
            sat.append("")
            sat.append(f"- **neden:** {kalem.get('neden')}")
            sat.append("- **dosyalar:** " + ", ".join(f"`{d}`" for d in kalem.get("dosyalar", [])))
            testler = kalem.get("test") or []
            sat.append("- **test:** " + (", ".join(f"`{t}`" for t in testler) if testler else "—"))
            gerek = kalem.get("gerektirir") or []
            sat.append("- **gerektirir:** " + (", ".join(f"`{g}`" for g in gerek) if gerek else "—"))
            if kalem.get("min_axet"):
                sat.append(f"- **asgari aXet sürümü:** {kalem['min_axet']}")
            sat.append("")
    return "\n".join(sat).rstrip("\n") + "\n"


def commit_mesaji(yayin: dict, ek: str = "") -> str:
    """Q2: yayın başı TEK commit. Hangi kalemlerin bu commit'te olduğunu trailer'lar söyler."""
    kalemler = yayin.get("kalemler", [])
    govde = [f"yayin: {yayin.get('etiket')} — {len(kalemler)} kalem", ""]
    if ek.strip():
        govde += [ek.strip(), ""]
    govde += ["Kalem ayrıntısı: CHANGELOG.md", ""]
    govde += [f"{KALEM_TRAILER}: {k.get('id')}" for k in kalemler]
    return "\n".join(govde) + "\n"


def yayinlar_oku(yol: Path) -> tuple[dict | None, str | None]:
    if not yol.is_file():
        return None, f"{YAYINLAR_YOLU} yok"
    try:
        return json.loads(yol.read_text(encoding="utf-8")), None
    except ValueError as e:
        return None, f"{YAYINLAR_YOLU} ayrıştırılamadı: {e}"


def degisen_yollar(hedef: Path) -> set[str] | None:
    """Staged ağaç ile HEAD arasındaki fark. HEAD yoksa None (ilk commit)."""
    if git_sessiz("rev-parse", "--verify", "-q", "HEAD", cwd=hedef)[0] != 0:
        return None
    ham = git("diff", "--cached", "--name-status", "-M", "-z", "HEAD", cwd=hedef).decode()
    parca = [p for p in ham.split("\0") if p]
    yollar: set[str] = set()
    i = 0
    while i < len(parca):
        durum = parca[i]
        if durum.startswith("R") and i + 2 < len(parca):
            yollar.update({parca[i + 1], parca[i + 2]})
            i += 3
        elif i + 1 < len(parca):
            yollar.add(parca[i + 1])
            i += 2
        else:
            break
    return yollar


def hedef_klonu_hazirla(hedef: Path, beklenen_origin: str) -> int:
    """Sonraki yayın: hedef, origin'i doğrulanmış PUBLIC klon olmalı; `.git` dışı her şey silinir
    (silinenler public'te de silinsin — TASARIM §11 adım 2)."""
    if not (hedef / ".git").exists():
        print(f"HATA: hedef bir git klonu değil: {hedef}\n"
              "      İLK yayın için `--ilk` kullan; sonraki yayınlar var olan public klona yazılır.",
              file=sys.stderr)
        return 2
    rc, url = git_sessiz("remote", "get-url", "origin", cwd=hedef)
    if rc != 0:
        print(f"HATA: hedef klonda `origin` uzak adresi yok: {hedef}", file=sys.stderr)
        return 2
    if url.rstrip("/").removesuffix(".git") != beklenen_origin.rstrip("/").removesuffix(".git"):
        print(f"HATA: hedef klonun origin adresi beklenenden farklı.\n"
              f"      beklenen: {beklenen_origin}\n      bulunan  : {url}\n"
              "      (Yanlış depoya yayın geri alınamaz — bilerek değiştiriyorsan `--origin` ver.)",
              file=sys.stderr)
        return 2
    for oge in hedef.iterdir():
        if oge.name == ".git":
            continue
        shutil.rmtree(oge) if oge.is_dir() else oge.unlink()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hedef", type=Path)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--calisma-agaci", action="store_true", help="commit'siz çalışma ağacını kopyala (yalnız deneme)")
    ap.add_argument("--yalniz-tara", action="store_true", help="kopyala + tara; git geçmişi kurma")
    ap.add_argument("--yalniz-dogrula", action="store_true",
                    help="yalnız guncelle/yayinlar.json şemasını doğrula (kopyalama/tarama yok)")
    ap.add_argument("--ilk", action="store_true", help="İLK yayın: boş hedefte `git init` + commit + etiket")
    ap.add_argument("--origin", default=RESMI_ORIGIN, help="sonraki yayınlarda beklenen public klon adresi")
    ap.add_argument("--mesaj", default="", help="commit gövdesine eklenecek serbest not")
    a = ap.parse_args()

    # --- yalnız şema doğrulama: hedef gerekmez ---------------------------------------------------
    if a.yalniz_dogrula:
        veri, hata = yayinlar_oku(KOK / YAYINLAR_YOLU)
        if hata:
            print(f"HATA: {hata}", file=sys.stderr)
            return 1
        sorunlar = sema_dogrula(veri)
        print(f"Doğrulanan: {KOK / YAYINLAR_YOLU}")
        print("KAPSAM — bakılan: şema (alan adları/tipleri), kalem id tekilliği, tur=guvenlik ise kritik "
              "kuralı, `gerektirir` çözünürlüğü ve sırası, yayın sürüm sırası, dışlanan/üretilen yol beyanı.")
        print("KAPSAM — bakılmayan: kalem-diff kapsamı (yalnız gerçek yayında ölçülür), `baslik`/`neden` "
              "metinlerinin doğruluğu, `test` kimliklerinin gerçekten koştuğu.")
        for s in sorunlar:
            print("  " + s)
        print(f"SORUN: {len(sorunlar)}")
        return 1 if sorunlar else 0

    if a.hedef is None:
        print("HATA: --hedef zorunlu (yalnız --yalniz-dogrula ile atlanabilir).", file=sys.stderr)
        return 2
    hedef = a.hedef.resolve()
    if hedef == KOK or KOK in hedef.parents:
        print("HATA: hedef geliştirme reposunun içinde olamaz.", file=sys.stderr)
        return 2
    if a.calisma_agaci and not a.yalniz_tara:
        print("HATA: --calisma-agaci yalnız --yalniz-tara ile kullanılır (commit'siz içerik yayınlanmaz).", file=sys.stderr)
        return 2
    if a.ilk and a.yalniz_tara:
        print("HATA: --ilk ile --yalniz-tara birlikte kullanılmaz.", file=sys.stderr)
        return 2

    yayin_kipi = not a.yalniz_tara          # gerçek yayın mı (commit + etiket)
    sonraki_yayin = yayin_kipi and not a.ilk
    if sonraki_yayin:
        rc = hedef_klonu_hazirla(hedef, a.origin)
        if rc:
            return rc
    else:
        if hedef.exists() and any(hedef.iterdir()):
            print(f"HATA: hedef boş değil: {hedef} (üzerine yazılmaz)", file=sys.stderr)
            return 2
        hedef.mkdir(parents=True, exist_ok=True)

    # Kimlik kopyalamadan ÖNCE denetlenir: `--ilk` tekrar koşulabilsin diye hedef hâlâ boşken durulur.
    if yayin_kipi:
        kimlik = kimlik_sorunlari(hedef)
        if kimlik:
            print("HATA: yayın commit'inin kimliği public repoya uygun değil — commit public'te GERİ ALINAMAZ:",
                  file=sys.stderr)
            for s in kimlik:
                print("  " + s, file=sys.stderr)
            print("  Yalnız bu komut için ortam değişkeniyle ver (PowerShell), sonra tekrar çalıştır:\n"
                  "    $env:GIT_AUTHOR_NAME='<ad>'; $env:GIT_AUTHOR_EMAIL='<id>+<kullanıcı>" + NOREPLY_SONEK + "'\n"
                  "    $env:GIT_COMMITTER_NAME='<ad>'; $env:GIT_COMMITTER_EMAIL='<id>+<kullanıcı>" + NOREPLY_SONEK + "'\n"
                  "  noreply adresin: GitHub → Settings → Emails. Global git ayarına dokunulmaz.", file=sys.stderr)
            return 1

    kaynak = "çalışma ağacı" if a.calisma_agaci else f"{a.ref} ({git('rev-parse', '--short', a.ref).decode().strip()})"
    yollar = kopyala(hedef, a.ref, a.calisma_agaci)

    # --- yayın kalemleri: şema + CHANGELOG ---------------------------------------------------------
    veri, okuma_hatasi = yayinlar_oku(hedef / YAYINLAR_YOLU)
    yayin = None
    if okuma_hatasi:
        if yayin_kipi:
            print(f"HATA: {okuma_hatasi} — yayın kalemleri olmadan yayın yapılamaz "
                  "(tüketici motoru bu dosyadan plan üretir).", file=sys.stderr)
            return 1
        print(f"YAYIN KALEMLERİ: ÖLÇÜLEMEDİ — {okuma_hatasi} (tarama kipinde bu bir BLOCKER değildir)")
    else:
        sema_sorunlari = sema_dogrula(veri)
        if sema_sorunlari:
            print(f"YAYIN KALEMLERİ ŞEMA SORUNU: {len(sema_sorunlari)}")
            for s in sema_sorunlari:
                print("  " + s)
            print("Git geçmişi kurulmadı." if yayin_kipi else "(tarama kipi — git zaten kurulmuyor)")
            return 1
        miras_uygula(veri)
        (hedef / YAYINLAR_YOLU).write_text(
            json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        (hedef / CHANGELOG_YOLU).write_text(changelog_uret(veri), encoding="utf-8", newline="\n")
        if CHANGELOG_YOLU not in yollar:
            yollar.append(CHANGELOG_YOLU)
        if veri.get("yayinlar"):
            yayin = veri["yayinlar"][-1]
        elif yayin_kipi:
            print("HATA: guncelle/yayinlar.json boş — yayınlanacak kalem yok.", file=sys.stderr)
            return 1

    bulgular = tara(hedef, yollar)

    print(f"Kaynak: {kaynak} -> {hedef}")
    print(f"Kopyalanan dosya: {len(yollar)} · dışlananlar: {', '.join(DISLANANLAR)}")
    if yayin:
        print(f"Yayın: {yayin['etiket']} ({yayin.get('tarih')}) · {len(yayin.get('kalemler', []))} kalem · "
              f"kritik: {sum(1 for k in yayin.get('kalemler', []) if k.get('kritik'))} · CHANGELOG.md üretildi")
    print("KAPSAM — bakılan (BLOCKER = çıkış 1): zorunlu dosyalar, NOTICE yolları, utf-8 metin dosyalarında "
          "şu sınıflar: " + ", ".join(d[1] for d in DESENLER if d[0] == BLOCKER))
    print("KAPSAM — bakılan (WARNING = yalnız listelenir, çıkışı etkilemez): "
          + ", ".join(d[1] for d in DESENLER if d[0] == WARNING))
    print("KAPSAM — bakılan (yayın kalemleri): guncelle/yayinlar.json şeması" +
          (" + kalem-diff kapsamı (eşlemesiz dosya = FAIL)" if sonraki_yayin
           else " (kalem-diff kapsamı bu kipte ÖLÇÜLMEZ: karşılaştırılacak önceki yayın yok)"))
    print("KAPSAM — bakılmayan: ikili dosyalar (" + ", ".join(sorted(IKILI_UZANTI)) + "), kişi adları sözlüğü, "
          "SAP host/SID/client serbest metni, anlamsal iç bilgi (ör. aXet iç davranış anlatımı), lisans uyumu, "
          f"kalem-diff kapsamında üretilen dosyalar ({', '.join(URETILEN_DOSYALAR)}). "
          "Bu tarama tam sızıntı denetiminin yerine geçmez.")
    engelleyen = [b for siddet, b in bulgular if siddet == BLOCKER]
    uyari = [b for siddet, b in bulgular if siddet == WARNING]
    if uyari:
        print(f"\nUYARI: {len(uyari)} (WARNING — çıkış kodunu etkilemez, yayını durdurmaz)")
        for b in uyari:
            print("  " + b)
    if engelleyen:
        print(f"\nBULGU: {len(engelleyen)} (BLOCKER)")
        for b in engelleyen:
            print("  " + b)
        print("\nGit geçmişi kurulmadı.")
        return 1
    print(f"BULGU: 0 (BLOCKER yok · {len(uyari)} WARNING · yalnız yukarıdaki kapsamda)")
    if a.yalniz_tara:
        return 0

    assert yayin is not None
    if a.ilk:
        git("init", "-q", "-b", "main", cwd=hedef)
    if git_sessiz("tag", "-l", yayin["etiket"], cwd=hedef)[1].strip():
        print(f"HATA: `{yayin['etiket']}` etiketi hedefte ZATEN VAR — yayın etiketi yeniden kullanılamaz "
              "(tüketici tabanı o etikete bağlıdır). guncelle/yayinlar.json'a YENİ bir yayın ekle.",
              file=sys.stderr)
        return 1
    git("add", "-A", cwd=hedef)

    degisen = degisen_yollar(hedef)
    if degisen is None:
        print("KALEM-DİFF KAPSAMI: ÖLÇÜLEMEDİ (hedefte önceki commit yok — ilk yayın)")
    else:
        kapsam_sorunlari = kapsam_dogrula(yayin, degisen)
        print(f"KALEM-DİFF KAPSAMI: {len(degisen)} değişen yol · {len(kapsam_sorunlari)} sorun")
        if kapsam_sorunlari:
            for s in kapsam_sorunlari:
                print("  " + s)
            git("reset", "-q", cwd=hedef)
            print("\nGit geçmişi kurulmadı (kalem eşlemesi eksik).")
            return 1

    git("commit", "-q", "-F", "-", cwd=hedef, girdi=commit_mesaji(yayin, a.mesaj).encode("utf-8"))
    git("tag", yayin["etiket"], cwd=hedef)
    print(f"Yayın commit'i: {git('log', '-1', '--oneline', cwd=hedef).decode().strip()}  ·  "
          f"etiket: {yayin['etiket']}")
    print("PUSH YAPILMADI (force push YASAK — yayın aracı force komutu üretmez). "
          "Ayrı onaydan sonra kullanıcının kendi terminalinde:")
    if a.ilk:
        print(f"  git -C \"{hedef}\" remote add origin {a.origin}")
        print(f"  git -C \"{hedef}\" push -u origin main --tags")
    else:
        print(f"  git -C \"{hedef}\" push origin main --tags")
    return 0


if __name__ == "__main__":
    sys.exit(main())
