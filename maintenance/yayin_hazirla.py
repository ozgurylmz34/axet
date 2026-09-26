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
  python maintenance/yayin_hazirla.py --depo-tara                                      GELİŞTİRME deposunu yerinde tara
                                                                                       (maintenance/ dahil; PR/push öncesi)
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
                    "README.md", "AGENTS.md", "kur.cmd", "kur.ps1", "yeni-proje.cmd", "aXet-Kur.cmd"]

# Yayın anında ÜRETİLEN / normalize edilen dosyalar. 2026-09-20'den beri (Z17) kalem-diff kapsamına DAHİLdirler:
# her yayında bir kaleme beyan edilirler, edilmezlerse yayın durur (bkz. `kapsam_dogrula`).
URETILEN_DOSYALAR = ("CHANGELOG.md", "guncelle/yayinlar.json", "guncelle/ci-durum.json")
YAYINLAR_YOLU = "guncelle/yayinlar.json"
CHANGELOG_YOLU = "CHANGELOG.md"
CI_DURUM_YOLU = "guncelle/ci-durum.json"
# README'nin sürüm satırı yayın anında katalogdaki son etiketle yazılır (2026-09-25: public README "Sürüm: 0.3.0"
# satırını v0.4.0'dan v0.5.8'e kadar bayat taşıdı — elle yazılan sayı hiç güncellenmedi). Satır yoksa ya da birden
# çoksa BLOCKER: sessizce damgasız yayın çıkmaz. Kalem-diff MUAFİYETİ YOK: README her yayında bir kaleme beyan
# edilir, çünkü tüketici `%guncelle` motoru kalemsiz değişen dosyayı uygulamaz. Yalnız sürüm satırı değiştiyse
# (`yalniz_surum_satiri_degisti`) araç ne yapılacağını söyleyen bir İPUCU basar; yayın yine durur.
README_YOLU = "README.md"
SURUM_SATIRI = re.compile(r"^(> Sürüm: )(\S+)( · )", re.M)
# `%guncelle`nin `once` turunu ikame edebilmesi için gereken ASGARİ takım adları. Bir yayın
# bunlardan birini taşımıyorsa `hepsi_yesil` YAZILMAZ ⇒ tüketici normal ölçer (fail-safe).
CI_ASGARI_TAKIMLAR = ("Testler (kok · Python 3.12)", "Testler (foundation · Python 3.12)",
                      # Z27: tüketicinin testleri PUBLIC ağaçta koşar; CI hükmü o ağacı da kapsamalı.
                      "Testler (kok-public · Python 3.12)")
# Z23 — bu sürenin altında biten `failure` iş hiç başlamamış sayılır (ölçüldü 2026-09-20:
# kota duvarında işler 2-4 sn'de `steps: 0` ile döndü; en kısa gerçek iş ~25 sn ön koşul koşar).
CI_BASLAMADI_ESIK_SN = 15
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
    # C:\Users\ (D16): gerçek kullanıcı adı = en az 3 karakter + yer tutucu DEĞİL. Muaf olanlar: `<...>`
    # biçimi, 1-2 karakterlik adlar (`C:\Users\u`) ve yer-tutucu sözcükler (örnek/kullanıcı/user/example...).
    # İki körlük 2026-09-17'de ÖLÇÜLEREK kapatıldı (ikisi de `tests/test_kur.py` fixture'ında gerçek bir ad
    # taşıyordu): (1) harf sınıfı artık UNICODE ([^\W\d_]) — eski `[A-Za-z]` ASCII olduğu için `C:\Users\Özgür`
    # gibi Türkçe karakterli adlar görünmüyordu (2) her iki bölü işareti ([\\/]) — `C:/Users/...` biçimi kaçıyordu.
    (BLOCKER, "iç kullanıcı/dizin",
     r"tr\d{5}\b|C:[\\/]Users[\\/](?!<)"
     r"(?!(?:örnek|ornek|kullanıcı|kullanici|user|username|example|sample)\b)[^\W\d_][\w.-]{2,}", re.I),
    (BLOCKER, "iç repo adı", r"DEV_CORE|\bPROVA\b|ix-works|ix_doctor", 0),
    (BLOCKER, "oturum bağlantısı", r"claude\.ai/code/session_", 0),
    (BLOCKER, "gerçek alan adı örneği", r"your-sap-server\.com|//server\.com", 0),
    # Yalnız MARKDOWN LİNK biçimindeki atıf (D16): tüketici klonunda dangling olan şey linktir; yorum
    # satırındaki kaynak atfı, ters-tırnaklı dosya adı ya da bir sınıf globu tüketiciyi hiçbir yere götürmez.
    (WARNING, "dışlanan dosyaya atıf",
     r"\]\([^)\s]*(?:maintenance/|agentic-connectors|axet-davranis-olcumleri)", 0),
]
# Müşteri / kurum adları KODDA DURMAZ (2026-09-25, kullanıcı kararı): bu depo da public'tir; adı yakalayan desen
# adın kendisini yayınlar. Liste iki kaynaktan okunur, ikisi birleştirilir: git'e GİRMEYEN yerel dosya (satır başına
# bir regex, `#` yorum; `.gitignore`'da) ve CI gizli değişkeni için ortam değişkeni (satır ya da `;` ayrımlı).
# Liste yoksa tarama bunu KAPSAM satırında ÖLÇÜLEMEDİ diye söyler; GERÇEK YAYIN listesiz başlamaz (fail-closed).
YEREL_LISTE_YOLU = "maintenance/sizinti-yerel.txt"
YEREL_LISTE_ORTAM = "AXET_SIZINTI_EK"
YEREL_LISTE_ADI = "yerel liste (müşteri/kurum)"
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


def yerel_desenler(kok: Path = KOK, ortam: dict | None = None) -> tuple[list[tuple], str]:
    """(desenler, kaynak beyanı). Desenler DESENLER biçimindedir (BLOCKER, büyük/küçük harf duyarsız).

    Hata (SystemExit): liste dosyası git'te İZLENİYORSA (ad public'e gider — amacın tersi) ya da bir satır geçersiz
    regex ise. Mesaj desenin kendisini BASMAZ; yalnız kaynağı ve satır numarasını söyler."""
    ortam = os.environ if ortam is None else ortam
    satirlar: list[tuple[str, str]] = []
    kaynaklar = []
    dosya = kok / YEREL_LISTE_YOLU
    if dosya.is_file():
        rc, _ = git_sessiz("ls-files", "--error-unmatch", YEREL_LISTE_YOLU, cwd=kok)
        if rc == 0:
            raise SystemExit(f"HATA: {YEREL_LISTE_YOLU} git'te izleniyor — içindeki adlar bu depoyla yayınlanır. "
                             f"`git rm --cached {YEREL_LISTE_YOLU}` ve `.gitignore` satırını kontrol et.")
        n = 0
        for no, satir in enumerate(dosya.read_text(encoding="utf-8").splitlines(), 1):
            satir = satir.strip()
            if satir and not satir.startswith("#"):
                satirlar.append((f"{YEREL_LISTE_YOLU}:{no}", satir))
                n += 1
        kaynaklar.append(f"dosya {n}")
    ham = ortam.get(YEREL_LISTE_ORTAM, "")
    if ham.strip():
        parcalar = [p.strip() for p in re.split(r"[;\n]", ham) if p.strip()]
        for i, p in enumerate(parcalar, 1):
            satirlar.append((f"${YEREL_LISTE_ORTAM}[{i}]", p))
        kaynaklar.append(f"ortam {len(parcalar)}")
    desenler = []
    for yer, desen in satirlar:
        try:
            re.compile(desen, re.I)
        except re.error as e:
            raise SystemExit(f"HATA: {yer} geçersiz regex ({e.msg}) — desen basılmadı.") from e
        desenler.append((BLOCKER, YEREL_LISTE_ADI, desen, re.I))
    return desenler, (" + ".join(kaynaklar) if kaynaklar else "")


def tara(hedef: Path, yollar: list[str], ek: list[tuple] | None = None) -> list[tuple[str, str]]:
    """(şiddet, metin) çiftleri döner. Yapısal eksikler (zorunlu dosya, NOTICE yolu, okunamayan dosya) BLOCKER'dır.
    `ek` = `yerel_desenler()` çıktısı (müşteri/kurum adları; DESENLER'le aynı biçim)."""
    desenler = DESENLER + list(ek or [])
    bulgular = [(BLOCKER, f"EKSİK zorunlu dosya: {z}") for z in ZORUNLU_DOSYALAR if not (hedef / z).is_file()]
    notice = hedef / "NOTICE"
    if notice.is_file():
        for satir in notice.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s+- (\S+)", satir)
            if m and not list(hedef.glob(m.group(1).rstrip("/"))):
                bulgular.append((BLOCKER, f"NOTICE listesindeki yol yok: {m.group(1)}"))
    return bulgular + desen_tara(hedef, yollar, desenler)


def desen_tara(hedef: Path, yollar: list[str], desenler: list[tuple]) -> list[tuple[str, str]]:
    """Metin dosyalarında satır satır desen araması (yayın ve depo taraması ortak). utf-8 okunamayan = BLOCKER."""
    bulgular: list[tuple[str, str]] = []
    for y in yollar:
        if Path(y).suffix.lower() in IKILI_UZANTI:
            continue
        try:
            metin = (hedef / y).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bulgular.append((BLOCKER, f"OKUNAMADI (utf-8 değil, taranmadı): {y}"))
            continue
        # split("\n"), splitlines() DEĞİL: splitlines U+2028/U+0085/\f gibi ayraçlarda da böler, git bölmez ⇒
        # raporlanan `dosya:satır` git'teki satırdan kayardı (Z133). Tespit etkilenmez, yalnız numara.
        for no, satir in enumerate(metin.split("\n"), 1):
            satir = satir.removesuffix("\r")
            for siddet, ad, desen, bayrak in desenler:
                if re.search(desen, satir, bayrak):
                    bulgular.append((siddet, f"{ad}: {y}:{no}: {satir.strip()[:140]}"))
    return bulgular


# =====================================================================================================
# DEPO TARAMASI — geliştirme deposunun KENDİSİ (Z145ⓑ, 2026-09-26)
# =====================================================================================================
# Geliştirme deposu da public'tir, ama yayın taraması yalnız YAYIN kopyasını görür (maintenance/ dışlanır). Ölçülen
# vaka: yerel listedeki bir müşteri adı maintenance/IS-LISTESI.md üzerinden birçok PR'la main'e girdi. Bu kip depoyu
# YERİNDE (kopya yok) tarar: izlenen + izlenmeyen dosyalar, `.gitignore`'lular hariç, maintenance/ DAHİL.
#   BLOCKER (çıkış 1) = yerel liste (müşteri/kurum). Liste yoksa kip fail-closed (çıkış 1, ÖLÇÜLEMEDİ).
#   UYARI (çıkışı etkilemez) = DESENLER'in BLOCKER sınıfları; "iç repo adı" yalnız SAYILIR: geliştirme deposu
#   maintenance/ altında iç repo adlarını bilerek taşır (ölçüldü 2026-09-26: 768 satır, 589'u sync-rules.json) —
#   bu kipte onları BLOCKER yapmak kipi kalıcı kırmızıya çevirir, yani kör eder.
# Muafiyet YALNIZ listenin kendi TAM yoludur (`YEREL_LISTE_YOLU`; desenlerin kaynağı kendini yakalar). Başka klasördeki
# aynı adlı dosya taranır. `.gitignore` dışlaması git'in kendi kararıdır (`--exclude-standard`).
DEPO_YALNIZ_SAYI = ("iç repo adı",)


def depo_yollari(kok: Path = KOK) -> list[str]:
    """İzlenen + izlenmeyen (gitignore'lu olmayan) dosyalar; listenin kendi yolu hariç."""
    yollar = git("ls-files", "--cached", "--others", "--exclude-standard", "-z", cwd=kok).decode("utf-8").split("\0")
    return sorted({y for y in yollar if y and y != YEREL_LISTE_YOLU and (kok / y).is_file()})


def depo_tara(kok: Path = KOK) -> int:
    ek_desenler, ek_kaynak = yerel_desenler(kok)
    print(f"Depo taraması (yerinde, kopya yok): {kok}")
    if not ek_desenler:
        print(f"HATA: müşteri/kurum ad listesi yok ({YEREL_LISTE_YOLU} ya da ${YEREL_LISTE_ORTAM}) — depo taraması "
              "müşteri adlarına bakamadı: ÖLÇÜLEMEDİ, temiz DEĞİL. Listeyi kur, sonra tekrar çalıştır "
              "(biçim: maintenance/UPDATE-PROCEDURE.md).", file=sys.stderr)
        return 1
    yollar = depo_yollari(kok)
    bulgular = desen_tara(kok, yollar, ek_desenler)
    uyari_desenleri = [d for d in DESENLER if d[0] == BLOCKER]
    uyarilar = [b for _, b in desen_tara(kok, yollar, uyari_desenleri)]
    liste_var = (kok / YEREL_LISTE_YOLU).is_file()
    liste_ignore = git_sessiz("check-ignore", "-q", YEREL_LISTE_YOLU, cwd=kok)[0] == 0

    print(f"Taranan dosya: {len(yollar)} (izlenen + izlenmeyen; .gitignore'lular hariç; maintenance/ DAHİL)")
    print(f"KAPSAM — BLOCKER (çıkış 1): {YEREL_LISTE_ADI}: {len(ek_desenler)} desen ({ek_kaynak}; içerik basılmaz) · "
          "utf-8 okunamayan metin dosyası (taranmadı = temiz sayılmaz)")
    print("KAPSAM — UYARI (çıkışı etkilemez): " + ", ".join(d[1] for d in uyari_desenleri)
          + f" — {', '.join(DEPO_YALNIZ_SAYI)} yalnız SAYILIR (geliştirme deposu maintenance/ altında bunları bilerek taşır)")
    print(f"KAPSAM — dışlanan: {YEREL_LISTE_YOLU} (listenin kendisi — yalnız bu TAM yol) · .gitignore'lu yollar · "
          "ikili dosyalar (" + ", ".join(sorted(IKILI_UZANTI)) + ")")
    print("KAPSAM — bakılmayan: git geçmişi (eski commit içerikleri ve commit mesajları) · PR başlığı/gövdesi · "
          "yayın taramasının WARNING sınıfları (dışlanan dosyaya atıf: yalnız yayın kopyasında anlamlı) · kişi adları "
          "sözlüğü · SAP host/SID/client serbest metni.")
    if liste_var and not liste_ignore:
        print(f"UYARI: {YEREL_LISTE_YOLU} .gitignore'da DEĞİL — `git add -A` listeyi (adları) depoya sokar.")
    sayilan: dict[str, dict[str, int]] = {}
    listelenen = []
    for u in uyarilar:
        sinif, _, kalan = u.partition(": ")
        if sinif in DEPO_YALNIZ_SAYI:
            dosya = kalan.split(":", 1)[0]
            sayilan.setdefault(sinif, {})
            sayilan[sinif][dosya] = sayilan[sinif].get(dosya, 0) + 1
        else:
            listelenen.append(u)
    if sayilan or listelenen:
        print(f"\nUYARI: {len(listelenen) + sum(sum(v.values()) for v in sayilan.values())} (çıkış kodunu etkilemez)")
        for sinif, dosyalar in sayilan.items():
            sirali = sorted(dosyalar.items(), key=lambda x: (-x[1], x[0]))
            print(f"  {sinif}: {sum(dosyalar.values())} satır (yalnız sayı — dosya başına: "
                  + " · ".join(f"{d} {n}" for d, n in sirali[:10]) + (" · …" if len(sirali) > 10 else "") + ")")
        for u in listelenen:
            print("  " + u)
    engelleyen = [b for s, b in bulgular if s == BLOCKER]
    if engelleyen:
        print(f"\nBULGU: {len(engelleyen)} (BLOCKER)")
        for b in engelleyen:
            print("  " + b)
        print("\nBu içerik public geliştirme deposuna girmemeli: satırı nötrleştir (placeholder), sonra tekrar tara.")
        return 1
    print("BULGU: 0 (BLOCKER yok · yalnız yukarıdaki kapsamda)")
    return 0


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


def capraz_yayin_uyarilari(veri) -> list[str]:
    """Z57: ÖNCEKİ bir yayının kalemine işaret eden `gerektirir` bağları — WARNING, çıkışı ETKİLEMEZ.

    Bağ şemaca geçerlidir (`sema_dogrula`: daha önce tanımlı kalem). Uyarı yalnız bakımcıya bağın
    tüketicide NASIL çözüleceğini hatırlatır. Tüketici motoru klondan değil bu yayının
    `origin/main` kopyasından koşar (K4: `skills/guncelle/SKILL.md` MOTOR-CIKAR bloğu,
    `maintenance/yayin_provasi.py` de adayın motorunu böyle çıkarır) ⇒ bağı değerlendiren motor
    BU yayının motorudur. v0.5.3 (Z57) motoru önceki turda uygulanmış (`uygulanan.json`) ya da
    içerilmiş (etiket HEAD'in atası) kalemi karşılanmış sayar; v0.5.2 ve öncesi saymıyordu
    (v0.5.2 CI yayın provası: `sec --hepsi` DUR). Kalan davranış: bağlı kalem tüketicide hâlâ
    bekliyorsa (hiç uygulanmamış) `sec --hepsi` onu da seçer, `sec --kalem <yeni>` ise DUR eder.
    Şema bozuksa sessizce boş döner — şema hükmü `sema_dogrula`nındır.
    """
    if not isinstance(veri, dict) or not isinstance(veri.get("yayinlar"), list):
        return []
    kalem_yayini: dict[str, str] = {}
    for y in veri["yayinlar"]:
        if isinstance(y, dict):
            for k in y.get("kalemler", []) or []:
                if isinstance(k, dict) and isinstance(k.get("id"), str):
                    kalem_yayini.setdefault(k["id"], str(y.get("etiket")))
    out: list[str] = []
    for y in veri["yayinlar"]:
        if not isinstance(y, dict):
            continue
        etiket = str(y.get("etiket"))
        for k in y.get("kalemler", []) or []:
            if not isinstance(k, dict) or not isinstance(k.get("gerektirir"), list):
                continue
            for bag in k["gerektirir"]:
                hedef = kalem_yayini.get(bag) if isinstance(bag, str) else None
                if hedef is not None and hedef != etiket:
                    out.append(
                        f"WARNING çapraz-yayın `gerektirir`: {k.get('id')} ({etiket}) → {bag} ({hedef}). "
                        f"Tüketici motoru bu yayının origin/main kopyasından koşar (K4); Z57 (v0.5.3+) "
                        f"motoru {bag} önceki turda uygulanmış/içerilmişse bağı karşılanmış sayar. "
                        f"{bag} tüketicide hâlâ bekliyorsa `sec --hepsi` onu da seçer, "
                        f"`sec --kalem {k.get('id')}` DUR eder. Bu yayının motoru Z57 öncesiyse "
                        f"(v0.5.2 ve eskisi) `sec --hepsi` de DUR eder.")
    return out


def kapsam_dogrula(yayin: dict, degisen: set[str]) -> list[str]:
    """TASARIM §11: diff'teki HER dosya en az 1 kaleme ait · kalemdeki her dosya gerçekten değişmiş.

    ⛔ ÜRETİLEN DOSYALAR DA KAPSAMA DAHİLDİR (Z17 düzeltmesi, 2026-09-20). Eskiden
    `URETILEN_DOSYALAR` bu denetimden TÜMDEN muaftı; gerekçe *"zaten her yayında değişirler,
    elle kalem yazmak gürültü olur"*du. Ama muafiyet gerekçesinden GENİŞ yazılmıştı ve iki
    sonucu vardı: ⓐ beyan edilmedikleri için tüketici klonuna **hiç ulaşmadılar** (ölçüldü:
    v0.1.0 · v0.2.0 · v0.3.0 → üçünde de `%guncelle plan` *"kapsamda ama hiçbir kalemin
    dosyalar listesinde geçmiyor — UYGULANMAYACAK"* dedi) ⓑ ikinci kural onları `olculen`
    dışında gördüğü için, beyan etmeye ÇALIŞAN biri *"bu yayında DEĞİŞMEMİŞ"* hatası alırdı
    — yani kapı düzeltmenin kendisini de engelliyordu.
    `degisen` bu noktada hedef ağaç `git add -A`'dan SONRA ölçülür ⇒ üretilen dosyalar
    gerçekten değişmiş görünür, beyan etmek ikinci kuralı ihlal etmez.
    """
    beyan: dict[str, list[str]] = {}
    for kalem in yayin.get("kalemler", []):
        for yol in kalem.get("dosyalar", []):
            beyan.setdefault(yol, []).append(kalem.get("id", "?"))
    olculen = set(degisen)
    s = []
    for yol in sorted(olculen - set(beyan)):
        ek = ("  ⛔ ÜRETİLEN DOSYA: beyan edilmezse tüketici klonuna HİÇ ULAŞMAZ (Z17)."
              if yol in URETILEN_DOSYALAR else "")
        s.append(f"kapsam: eşlemesiz dosya (hiçbir kaleme ait değil): {yol}{ek}")
    for yol in sorted(set(beyan) - olculen):
        s.append(f"kapsam: kalemde bildirilen dosya bu yayında DEĞİŞMEMİŞ: {yol} "
                 f"(kalem: {', '.join(beyan[yol])})")
    return s


def ci_durum_uret(kaynak_sha: str, etiket: str, mevcut: dict | None, kapali: bool) -> dict:
    """Kaynak commit'in CI hükmünü `gh` ile okur; yayına taşınacak kaydı üretir (Z16).

    ⛔ NEDEN: tüketici klonunda `%guncelle` `once` turunu ancak GÜVENİLİR bir tabanla ikame
    edebilir. O taban CI'dır — yeni testleri yeni ürüne karşı TEMİZ ortamda ölçmüştür; yerel
    `once` turu ise ESKİ test koduyla ölçtüğü için karşılaştırılabilir bir taban üretmiyordu.

    ⛔ FAIL-SAFE: ölçemezsek `hepsi_yesil` **True yazılmaz** ve `not` alanına sebebi yazılır.
    Tüketici `hepsi_yesil is not True` gördüğü an normal ölçüme döner (`guncelle.py::_ci_tabani`).
    "Ölçemedim" asla "yeşil say" demek değildir.

    ⛔ HEDEF AÇIK: `gh api repos/<ORG>/<REPO>/...` tam yolla çağrılır; `{owner}`/`{repo}`
    yer tutucusu cwd'den çözüleceği için KULLANILMAZ.
    """
    kayit = dict(mevcut or {})
    temel = {"kaynak_commit": kaynak_sha, "olcum_zamani": _simdi_iso(), "hepsi_yesil": False}
    if kapali:
        temel["not"] = "--ci-durum-yok verildi: CI hükmü SORULMADI (ölçülemedi ≠ yeşil)."
        kayit[etiket] = temel
        return kayit
    depo = _kaynak_depo()
    if not depo:
        temel["not"] = "kaynak deponun origin'i GitHub deposu olarak çözülemedi."
        kayit[etiket] = temel
        return kayit
    temel["depo"] = depo
    kod, cikti, hata = git_sessiz_komut(
        ["gh", "api", f"repos/{depo}/commits/{kaynak_sha}/check-runs",
         "--jq", ".check_runs[] | \"\\(.name)\\t\\(.conclusion)\\t"
                 "\\(if .started_at and .completed_at then "
                 "((.completed_at|fromdate) - (.started_at|fromdate)) else \"\" end)\""])
    if kod != 0:
        temel["not"] = f"gh check-runs okunamadi (rc={kod}): {(hata or '').strip()[:200]}"
        kayit[etiket] = temel
        return kayit
    takimlar = []
    sureler = {}
    for satir in (cikti or "").splitlines():
        if "\t" not in satir:
            continue
        parca = satir.split("\t")
        ad, sonuc = parca[0].strip(), parca[1].strip()
        takimlar.append({"ad": ad, "sonuc": sonuc})
        if len(parca) > 2 and parca[2].strip().lstrip("-").isdigit():
            sureler[ad] = int(parca[2].strip())
    temel["takimlar"] = takimlar
    eksik = [t for t in CI_ASGARI_TAKIMLAR if not any(x["ad"] == t for x in takimlar)]
    if not takimlar:
        temel["not"] = "commit icin hic check-run yok (CI kosmamis olabilir)."
    elif eksik:
        temel["not"] = "asgari takimlar eksik: " + ", ".join(eksik)
    elif any(t["sonuc"] in ("", "None", "null") for t in takimlar):
        # `conclusion` null = is HALA KOSUYOR. Bunu "kirmizi" diye raporlamak yanlis teshistir:
        # yayinci "CI kirildi" sanip kod arar, oysa yalnizca beklemesi gerekiyordu.
        temel["not"] = ("CI hala kosuyor (conclusion bos) — yayindan ONCE bitmesini bekle, "
                        "sonra bu araci yeniden calistir.")
    elif any(t["sonuc"] != "success" for t in takimlar):
        kirmizi = [t["ad"] for t in takimlar if t["sonuc"] != "success"]
        # Z23 — kota/ödeme duvarında işler HİÇ BAŞLAMAZ: saniyeler içinde `failure`, 0 adım.
        # En kısa gerçek iş bile checkout + setup-python ile bu eşiği aşar ⇒ eşiğin altındaki
        # failure "kırmızı takım" DEĞİL, "ölçülmedi"dir. Süresi bilinmeyen iş gerçek kırmızı sayılır.
        if all(t["sonuc"] == "failure" and sureler.get(t["ad"], CI_BASLAMADI_ESIK_SN + 1)
               <= CI_BASLAMADI_ESIK_SN for t in takimlar if t["sonuc"] != "success"):
            temel["not"] = ("CI isleri BASLAMADI (kota/odeme duvari olabilir; "
                            f"{', '.join(kirmizi)} <= {CI_BASLAMADI_ESIK_SN} sn) — "
                            "kod hakkinda hukum YOK.")
        else:
            temel["not"] = "yesil olmayan takim(lar): " + ", ".join(kirmizi)
    else:
        temel["hepsi_yesil"] = True
        temel["isletim_sistemi"] = _ci_os()
        temel["python"] = _ci_python(takimlar)
    kayit[etiket] = temel
    return kayit


def _simdi_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def _kaynak_depo() -> str | None:
    kod, cikti, _ = git_sessiz_komut(["git", "-C", str(KOK), "remote", "get-url", "origin"])
    if kod != 0:
        return None
    m = re.search(r"github\.com[:/]([^/]+/[^/\s.]+)", (cikti or "").strip())
    return m.group(1) if m else None


def _ci_os() -> str:
    """CI matrisinin `runs-on` değeri — workflow'dan OKUNUR, sabit yazılmaz (bayatlamasın)."""
    for wf in sorted((KOK / ".github" / "workflows").glob("*.yml")):
        m = re.search(r"^\s*runs-on:\s*(\S+)", wf.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return "OLCULEMEDI"


def _ci_python(takimlar: list[dict]) -> list[str]:
    """Takım adlarından Python sürümlerini çıkarır (ad biçimi workflow'un `name:` alanından)."""
    return sorted({m.group(1) for t in takimlar
                   if (m := re.search(r"Python\s+(\d+\.\d+)", t["ad"]))})


def git_sessiz_komut(argv: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


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


def readme_surum_damgala(yol: Path, etiket: str) -> str | None:
    """README'deki `> Sürüm: <x> · …` satırının <x>'ini `etiket` yapar. Sorun varsa metnini, yoksa None döner."""
    try:
        metin = yol.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return f"{README_YOLU} okunamadı ({e.__class__.__name__}: {e})"
    adet = len(SURUM_SATIRI.findall(metin))
    if adet != 1:
        return (f"{README_YOLU}'de `> Sürüm: <etiket> · …` satırı {adet} kez var (tam 1 olmalı) — "
                "yayın sürümü README'ye yazılamaz")
    yeni = SURUM_SATIRI.sub(lambda m: m.group(1) + etiket + m.group(3), metin)
    if yeni != metin:
        yol.write_bytes(yeni.encode("utf-8"))
    return None


def yalniz_surum_satiri_degisti(hedef: Path) -> bool:
    """Staged README ile HEAD'deki README, sürüm satırındaki etiket dışında bayt bayt aynı mı."""
    rc_eski, _ = git_sessiz("cat-file", "-e", f"HEAD:{README_YOLU}", cwd=hedef)
    rc_yeni, _ = git_sessiz("cat-file", "-e", f":{README_YOLU}", cwd=hedef)
    if rc_eski != 0 or rc_yeni != 0:
        return False

    def notr(ref: str) -> str:
        metin = git("show", ref, cwd=hedef).decode("utf-8", errors="replace")
        return SURUM_SATIRI.sub(lambda m: m.group(1) + "<etiket>" + m.group(3), metin)

    eski, yeni = notr(f"HEAD:{README_YOLU}"), notr(f":{README_YOLU}")
    return eski == yeni and SURUM_SATIRI.search(eski) is not None


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
    ap.add_argument("--ci-durum-yok", action="store_true",
                    help="CI hükmünü `gh` ile SORMA (çevrimdışı/otomatik testler). "
                         "Kayıt yine yazılır ama `hepsi_yesil: false` olur ⇒ tüketici normal ölçer.")
    ap.add_argument("--depo-tara", action="store_true",
                    help="GELİŞTİRME deposunu yerinde tara (maintenance/ dahil; yayın kopyası yok) — Z145")
    a = ap.parse_args()

    # --- geliştirme deposu taraması: kopya/hedef yok, başka kiple birleşmez -------------------------
    if a.depo_tara:
        if a.hedef is not None or a.ilk or a.yalniz_tara or a.calisma_agaci or a.yalniz_dogrula:
            print("HATA: --depo-tara tek başına kullanılır (--hedef/--ilk/--yalniz-tara/--calisma-agaci/"
                  "--yalniz-dogrula ile birlikte kullanılmaz).", file=sys.stderr)
            return 2
        return depo_tara()

    # --- yalnız şema doğrulama: hedef gerekmez ---------------------------------------------------
    if a.yalniz_dogrula:
        veri, hata = yayinlar_oku(KOK / YAYINLAR_YOLU)
        if hata:
            print(f"HATA: {hata}", file=sys.stderr)
            return 1
        sorunlar = sema_dogrula(veri)
        print(f"Doğrulanan: {KOK / YAYINLAR_YOLU}")
        print("KAPSAM — bakılan: şema (alan adları/tipleri), kalem id tekilliği, tur=guvenlik ise kritik "
              "kuralı, `gerektirir` çözünürlüğü ve sırası (+ çapraz-yayın bağı WARNING, Z57), yayın sürüm sırası, dışlanan yol beyanı. (Üretilen dosyaların beyanı 2026-09-20'den beri SERBEST ve gerçek yayında ZORUNLU — Z17.)")
        print("KAPSAM — bakılmayan: kalem-diff kapsamı (yalnız gerçek yayında ölçülür), `baslik`/`neden` "
              "metinlerinin doğruluğu, `test` kimliklerinin gerçekten koştuğu.")
        for s in sorunlar:
            print("  " + s)
        uyarilar = capraz_yayin_uyarilari(veri)
        for u in uyarilar:
            print("  " + u)
        print(f"SORUN: {len(sorunlar)}" + (f" · UYARI: {len(uyarilar)} (çıkışı etkilemez)" if uyarilar else ""))
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
    ek_desenler, ek_kaynak = yerel_desenler()
    if yayin_kipi and not ek_desenler:
        print(f"HATA: müşteri/kurum ad listesi yok ({YEREL_LISTE_YOLU} ya da ${YEREL_LISTE_ORTAM}) — liste olmadan "
              "sızıntı taraması müşteri adlarına bakmaz ve public yayın GERİ ALINAMAZ. Listeyi kur, sonra tekrar "
              "çalıştır (biçim: maintenance/UPDATE-PROCEDURE.md).", file=sys.stderr)
        return 1
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
    readme_hatasi = None
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
        for u in capraz_yayin_uyarilari(veri):
            print("  " + u)
        miras_uygula(veri)
        (hedef / YAYINLAR_YOLU).write_text(
            json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        (hedef / CHANGELOG_YOLU).write_text(changelog_uret(veri), encoding="utf-8", newline="\n")
        if CHANGELOG_YOLU not in yollar:
            yollar.append(CHANGELOG_YOLU)
        if veri.get("yayinlar"):
            readme_hatasi = readme_surum_damgala(hedef / README_YOLU, veri["yayinlar"][-1]["etiket"])
        # --- ci-durum.json (Z16): tüketicinin `once` turunu ikame edebilmesi için CI hükmü ----
        if veri.get("yayinlar"):
            _etiket = veri["yayinlar"][-1]["etiket"]
            _sha = ("CALISMA-AGACI" if a.calisma_agaci
                    else git("rev-parse", a.ref).decode().strip())
            _eski = None
            _var = hedef / CI_DURUM_YOLU
            if _var.is_file():
                try:
                    _eski = (json.loads(_var.read_text(encoding="utf-8")) or {}).get("yayinlar")
                except ValueError:
                    _eski = None
            _kayitlar = ci_durum_uret(_sha, _etiket, _eski, bool(a.ci_durum_yok))
            _var.parent.mkdir(parents=True, exist_ok=True)
            _var.write_text(json.dumps(
                {"surum": 1,
                 "aciklama": ("Yayin basina CI hukmu. `%guncelle` bunu `origin/main` uzerinden "
                              "okur ve YARGI VAKASI YOKKEN `olc --asama once` turunu ikame eder "
                              "(scripts/guncelle.py::_ci_tabani). `hepsi_yesil` True DEGILSE "
                              "tuketici normal olcer — olculemedi != yesil."),
                 "yayinlar": _kayitlar}, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8", newline="\n")
            if CI_DURUM_YOLU not in yollar:
                yollar.append(CI_DURUM_YOLU)
            _y = _kayitlar[_etiket]
            print(f"CI durumu: {_etiket} · hepsi_yesil={_y['hepsi_yesil']}"
                  + (f" · NOT: {_y['not']}" if _y.get("not") else
                     f" · {len(_y.get('takimlar', []))} takim · {_y.get('isletim_sistemi')}"))
        if veri.get("yayinlar"):
            yayin = veri["yayinlar"][-1]
        elif yayin_kipi:
            print("HATA: guncelle/yayinlar.json boş — yayınlanacak kalem yok.", file=sys.stderr)
            return 1

    bulgular = tara(hedef, yollar, ek_desenler)
    if readme_hatasi:
        bulgular.append((BLOCKER, f"README sürüm satırı: {readme_hatasi}"))

    print(f"Kaynak: {kaynak} -> {hedef}")
    print(f"Kopyalanan dosya: {len(yollar)} · dışlananlar: {', '.join(DISLANANLAR)}")
    if yayin:
        print(f"Yayın: {yayin['etiket']} ({yayin.get('tarih')}) · {len(yayin.get('kalemler', []))} kalem · "
              f"kritik: {sum(1 for k in yayin.get('kalemler', []) if k.get('kritik'))} · CHANGELOG.md üretildi")
    print("KAPSAM — bakılan (BLOCKER = çıkış 1): zorunlu dosyalar, NOTICE yolları, utf-8 metin dosyalarında "
          "şu sınıflar: " + ", ".join(d[1] for d in DESENLER if d[0] == BLOCKER))
    if ek_desenler:
        print(f"KAPSAM — {YEREL_LISTE_ADI}: {len(ek_desenler)} desen ({ek_kaynak}; içerik basılmaz)")
    else:
        print(f"KAPSAM — {YEREL_LISTE_ADI}: YÜKLENMEDİ ({YEREL_LISTE_YOLU} ve ${YEREL_LISTE_ORTAM} yok) — "
              "müşteri/kurum adları TARANMADI: ÖLÇÜLEMEDİ, temiz değil. Gerçek yayın listesiz başlamaz.")
    print("KAPSAM — bakılan (WARNING = yalnız listelenir, çıkışı etkilemez): "
          + ", ".join(d[1] for d in DESENLER if d[0] == WARNING))
    print("KAPSAM — bakılan (yayın kalemleri): guncelle/yayinlar.json şeması" +
          (" + kalem-diff kapsamı (eşlemesiz dosya = FAIL)" if sonraki_yayin
           else " (kalem-diff kapsamı bu kipte ÖLÇÜLMEZ: karşılaştırılacak önceki yayın yok)"))
    print("KAPSAM — bakılmayan: ikili dosyalar (" + ", ".join(sorted(IKILI_UZANTI)) + "), kişi adları sözlüğü, "
          "SAP host/SID/client serbest metni, anlamsal iç bilgi (ör. aXet iç davranış anlatımı), lisans uyumu. "
          "Bu tarama tam sızıntı denetiminin yerine geçmez.")
    print(f"KAPSAM — üretilen dosyalar ({', '.join(URETILEN_DOSYALAR)}) 2026-09-20'den beri "
          "kalem-diff kapsamına DAHİL: beyan edilmezlerse yayın durur (Z17 — eskiden muaftılar "
          "ve tüketici klonuna hiç ulaşmıyorlardı).")
    if yayin:
        print(f"KAPSAM — README sürüm satırı: {'yazılamadı (BLOCKER)' if readme_hatasi else yayin['etiket']} "
              "(yalnız `> Sürüm: … · ` biçimli tek satır; README'nin başka yerindeki sürüm anmalarına bakılmaz).")
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
        ipucu = None
        if (any(s.endswith(f": {README_YOLU}") for s in kapsam_sorunlari)
                and yalniz_surum_satiri_degisti(hedef)):
            ipucu = (f"İPUCU: {README_YOLU} yalnız sürüm satırında değişti (bu aracın yazdığı) — onu her yayının "
                     "yayın kaydı kalemine (\"Yayın kataloğu, README sürüm satırı ve CI kaydı\") ekle. Muafiyet YOK: "
                     "kalemsiz değişen dosyayı tüketici `%guncelle` motoru uygulamaz "
                     "(scripts/guncelle.py 'beyansız EYLEM vakası').")
        print(f"KALEM-DİFF KAPSAMI: {len(degisen)} değişen yol · {len(kapsam_sorunlari)} sorun")
        if kapsam_sorunlari:
            for s in kapsam_sorunlari + ([ipucu] if ipucu else []):
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
