# sinif-validator-ailesi — validator'lar, zincir ve gate motoru (kritik yol)

## Tetik
Plandaki dosya bir `check_*.py`, `run_review.py`, `_reviewer.py`, `gate.py` ya da `validator-map.md`. Bu sınıfın çoğu üyesi `kritik_yol`'dur.

## Zorunlu ek adımlar
1. Eş dosyalar aynı pakette gelmeli: plan onları birlikte seçer — seçimi bozma.
2. Testler: `python skills-sap/sap-adt-foundation/tests/run_tests.py` ve
   `python -m unittest discover -s skills-sap/sap-code-review/tests -t skills-sap/sap-code-review/tests`
   (zincir ↔ tablo eşitliği burada ölçülür).
3. **Akış adım 11 zorunlu:** aynı örnek girdiyle güncelleme ÖNCESİ ve SONRASI hükmü karşılaştır
   (PASS/WARNING/BLOCKER değişti mi?). Fark varsa açıklanmadan kapanışa geçilmez.
4. Yerelde gevşetilmiş bir kontrol varsa asgari güvence raporuna satır olarak girer.

## DUR
Eşlerden biri yerelde değişmiş (V3, yeni sürüm gelmiyor) diğeri güncelleniyorsa (V1) zincir
ayrışabilir: kullanıcıya göster, kendi başına "nasılsa çalışır" deme. Açıklanamayan hüküm farkı =
DUR.
