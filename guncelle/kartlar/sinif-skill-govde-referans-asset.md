# sinif-skill-govde-referans-asset — skill gövdesi, referansı ve örnek dosyaları

## Tetik
Plandaki dosya bir `SKILL.md`, skill `references/**` ya da `templates/**`/`assets/**` dosyası.

## Kapsam (harita.json)
| Alt sınıf | `etkin` | Özel adım | Ne demek |
|---|---|---|---|
| `skill-govde` | `skill-cagrisi` | komut | skill klasörü YENİ eklendiyse python scripts/install.py |
| `bilinen-hata-referans` | `skill-cagrisi` | yok | skill'in bir sonraki çağrısında |
| `skill-referans` | `skill-cagrisi` | yok | skill'in bir sonraki çağrısında |
| `skill-asset-template` | `skill-cagrisi` | yok | skill'in bir sonraki çağrısında |

## Zorunlu ek adımlar
1. Dosyayı al/birleştir.
2. `python scripts/doctor.py --skills` koş: ad çakışması, bozuk frontmatter, eksik referans
   buradan görünür.
3. Skill klasörü YENİ eklendiyse `guncelle.py ozel-adim <sinif>` ile `scripts/install.py` koşulur
   (plan bunu listeler).
4. Etkinleşme: skill bir sonraki çağrısında yeni gövdeyi okur — aXet'i kapatıp açmak gerekmez.

## DUR
Örnek dosyalar (`.conn_adt.example` gibi) YALNIZ örnektir: gerçek `.conn_adt` dosyasına
dokunma, okuma, içeriğini isteme.
