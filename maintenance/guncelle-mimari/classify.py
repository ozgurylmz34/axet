#!/usr/bin/env python3
"""aXet template dosya sinifllandirma - GUNCELLE-MIMARI asama 1.
Girdi: `git ls-files` ciktisi (repo kokunden, C:\\axet).
Cikti: sinif -> dosya listesi + sayim; 0-sinif ve coklu-sinif dosyalari ayri raporlanir.
Kurallar SIRALI regex; ILK eslesen kural kazanir (tek-sinif garantisi icin).
Ayrica coklu-eslesme denetimi icin TUM kurallari da ayrica test edip >1 eslesirse raporluyoruz.
"""
import re
import sys
import json
from collections import OrderedDict, defaultdict

FILES_TXT = sys.argv[1] if len(sys.argv) > 1 else "axet_files.txt"

with open(FILES_TXT, encoding="utf-8") as f:
    files = [ln.strip() for ln in f if ln.strip()]

# (sinif_adi, regex) sirali liste - ILK eslesen kazanir.
RULES = [
    ("lisans", r'^(LICENSE|NOTICE|THIRD_PARTY_NOTICES\.md|LICENSES/.*)$'),
    ("config-izin-kok", r'^(\.axetcode-denylist|\.gitattributes|\.gitignore|config/permissions\.json)$'),
    ("kurulum-araci-kok", r'^(kur\.cmd|kur\.ps1|yeni-proje\.cmd)$'),
    ("bakim-repo-agents", r'^AGENTS\.md$'),
    ("belge-kok", r'^README\.md$'),
    ("belge-docs", r'^docs/.*\.md$'),
    ("bakim-ic", r'^maintenance/.*$'),
    ("cekirdek-kural", r'^core/.*\.md$'),
    ("ders-memory", r'^memory/.*\.md$'),
    ("ders-memory-proje-sablon", r'^templates/project/\.axet-code/memory/.*\.md$'),
    ("proje-sablon-config", r'^templates/project/(\.axet-code\.json|\.axet-code/\.gitignore|\.axetcode-denylist|\.gitattributes|\.gitignore|\.githooks/.*)$'),
    ("proje-sablon-diger", r'^templates/project/.*$'),
    ("proje-sablon-sap-json", r'^templates/project-sap/.*$'),
    ("paket-sablon", r'^templates/package/.*$'),
    ("kurulum-araci-script", r'^scripts/(install|new_project|new_package|yeni_proje)\.py$'),
    ("bakim-script-kok", r'^scripts/(doctor|session_brief|sap_stamp|behavior_manifest|check_package_naming|project_precommit)\.py$'),
    ("test-kok", r'^tests/.*\.py$'),
    ("skill-govde", r'^skills(-sap)?/[^/]+/SKILL\.md$'),
    ("skill-index-belge", r'^skills-sap/README\.md$'),
    ("skill-fixture-sample", r'^skills(-sap)?/[^/]+/tests/(samples|fixtures)/.*$'),
    ("skill-test", r'^skills(-sap)?/[^/]+/tests/.*\.(py|ts)$'),
    ("skill-test-diger", r'^skills(-sap)?/[^/]+/tests/.*$'),
    ("validator-zincir-map", r'^skills-sap/sap-code-review/references/validator-map\.md$'),
    ("validator-gate-motor", r'^skills-sap/sap-adt-foundation/scripts/sapadt/(gate|_reviewer|_gate_status)\.py$'),
    ("validator-runner", r'^skills-sap/sap-adt-foundation/scripts/sapadt/lib/validators/run_review\.py$'),
    ("validator", r'^skills-sap/sap-adt-foundation/scripts/sapadt/lib/validators/check_.*\.py$'),
    ("validator-ui5", r'^skills-sap/sap-ui5-fiori/scripts/check_.*\.py$'),
    ("validator-diger-skill", r'^skills-sap/[^/]+/scripts/(check_[a-z_]+\.py|doc_equivalence_check\.py)$'),
    ("bilinen-hata-referans", r'^skills(-sap)?/[^/]+/references/known-errors.*\.md$'),
    ("skill-referans", r'^skills(-sap)?/[^/]+/references/.*\.md$'),
    ("skill-referans-modul", r'^skills-sap/sap-intake-triage/references/modules/.*\.md$'),
    ("skill-asset-template", r'^skills(-sap)?/[^/]+/(assets|templates)/.*$'),
    ("skill-implementation-belge", r'^skills-sap/sap-adt-foundation/IMPLEMENTATION\.md$'),
    ("skill-script", r'^skills(-sap)?/[^/]+/scripts/.*$'),
    ("skill-scratch-cmd", r'^(yeni-proje\.cmd)$'),
]

def classify(path):
    matches = []
    for name, pat in RULES:
        if re.match(pat, path):
            matches.append(name)
    return matches

by_class = defaultdict(list)
zero = []
multi = []

for p in files:
    m = classify(p)
    if len(m) == 0:
        zero.append(p)
    elif len(m) > 1:
        multi.append((p, m))
        by_class[m[0]].append(p)  # ilk kazanir (raporda ayrica coklu listeleniyor)
    else:
        by_class[m[0]].append(p)

print("=" * 70)
print(f"TOPLAM DOSYA: {len(files)}")
print("=" * 70)
total_check = 0
for name, _ in RULES:
    lst = by_class.get(name, [])
    if lst:
        print(f"{name:32s} {len(lst):4d}")
        total_check += len(lst)
print("-" * 70)
print(f"SINIFLANDIRILAN TOPLAM: {total_check}")
print(f"SIFIR-SINIF (hic eslesmeyen): {len(zero)}")
for z in zero:
    print(f"  UNMATCHED: {z}")
print(f"COKLU-SINIF (birden fazla kurala uyan): {len(multi)}")
for p, m in multi:
    print(f"  MULTI: {p} -> {m}")

# Detay dump JSON
out = {
    "total_files": len(files),
    "classes": {k: v for k, v in by_class.items()},
    "unmatched": zero,
    "multi": [{"file": p, "classes": m} for p, m in multi],
}
with open("classify_output.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print()
print("Detay: classify_output.json yazildi")
