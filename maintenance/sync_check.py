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
Çıkış kodu: 0 temiz · 1 KURALSIZ dosya ya da eksik 'tamam' hedefi var · 2 kural dosyası hatası · 3 kullanım/git hatası.
Hash satır sonundan bağımsızdır (CRLF -> LF normalize edilir).
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
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


def main() -> int:
    ap = argparse.ArgumentParser(description="IX -> aXet aktarım haritası denetimi")
    ap.add_argument("--source", action="append", default=[], metavar="AD=YOL", help="kaynak repo (tekrarlanabilir)")
    ap.add_argument("--update-lock", action="store_true", help="güncel hash'leri kilit dosyasına yaz")
    ap.add_argument("--ayrinti", action="store_true", help="değişmeyen dosyaları da listele")
    ap.add_argument("--json", action="store_true", help="JSON çıktı")
    args = ap.parse_args()
    if not args.source:
        print("HATA: en az bir --source AD=YOL ver (ör. --source DEV_CORE=D:/repos/DEV_CORE).")
        return 3

    data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
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

    if problems:
        return 2
    if args.update_lock:
        if kuralsiz_total:
            print(f"\n--update-lock YAPILMADI: {kuralsiz_total} KURALSIZ dosya var.")
            return 1
        merged = {"_aciklama": "sync_check.py --update-lock üretir; elle düzenleme. Hash CRLF->LF normalize sha256.",
                  "sources": {**(lock.get("sources") or {}), **new_lock_sources}}
        LOCK_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        if not args.json:
            print(f"\nKilit güncellendi: {LOCK_FILE} ({', '.join(new_lock_sources)})")
    return 1 if (kuralsiz_total or missing_targets) else 0


if __name__ == "__main__":
    sys.exit(main())
