<#
kur.ps1 — aXet.code template'ini bu makineye kurar, günceller ya da kaldırır (son kullanıcı aracı).

Ne yapar (sırayla):
  1. aXet (axet-code) kurulu mu bakar; yoksa durur. aXet şirket kanalından kurulur, bu betik kurmaz.
  2. Git ve Python >= 3.9 arar. Yoksa winget ile kurmayı SORAR; winget yoksa ya da hata verirse ne kurulacağını
     ve resmi indirme adresini yazıp durur. rg (ripgrep) yoksa isteğe bağlı olarak önerir.
  3. Template'i klonlar (hedef yoksa) ya da günceller (hedef bu template'in klonuysa: git pull --ff-only).
     Hedef bu template'in klonu değilse (core/00-temel.md CORE-ID + scripts/install.py + skills-sap/) DURUR ve o
     reponun hiçbir betiğini çalıştırmaz. Yerel değişiklik ya da ayrışma varsa DURUR; hiçbir yerel değişikliği silmez,
     saklamaz, geri almaz.
  4. python <Hedef>\scripts\install.py --sap   (global aXet config'ine yolları ve izin kurallarını yazar)
  5. python <Hedef>\scripts\doctor.py          (statik doğrulama)

Kullanım (kur.cmd aynı parametreleri geçirir):
  kur.cmd                          kur ya da güncelle (klon: %USERPROFILE%\axet)
  kur.cmd -Hedef D:\araclar\axet   başka klasöre kur (yolu ters bölü ile BİTİRME: "D:\araclar\axet\" sonraki
                                   parametreleri yutar)
  kur.cmd -Kaynak <URL|yerel yol>  başka kaynaktan klonla (varsayılan: GitHub)
  kur.cmd -DenemeModu              hiçbir şey yazmadan/kurmadan planı göster
  kur.cmd -Kaldir                  global config'ten bu klonun kayıtlarını kaldır; bu klonda açılmış SAP'ye yazma
                                   iznini de KAPATIR (izin dosyasını siler). Klon klasörü SİLİNMEZ.
  -Evet          soruları otomatik "evet" yanıtlar (otomatik testler için)
  -WingetKapali  winget'i hiç çağırmaz; eksik araç için yalnız tarif yazar (otomatik testler için)

Çıkış kodu: 0 tamam · 1 durduruldu/hata · 2 ön koşul eksik · 3 yeni terminal gerekli · 4 doctor FAIL gösterdi
#>
[CmdletBinding()]
param(
    [string]$Hedef = (Join-Path $env:USERPROFILE 'axet'),
    [string]$Kaynak = 'https://github.com/ozgurylmz34/axet-template.git',
    [switch]$Kaldir,
    [switch]$DenemeModu,
    [switch]$Evet,
    [switch]$WingetKapali
)

Set-StrictMode -Version 2
# Continue: git/python stderr'e ilerleme yazar; Stop olsaydı PS 5.1 bunu hata sayıp betiği keserdi.
# Başarı her native çağrıda $LASTEXITCODE ile ölçülür; çağrıdan önce $null yapılır, çünkü ölçüldü: komut hiç
# bulunamazsa (CommandNotFound) $LASTEXITCODE önceki değerinde kalır ve eski 0 "başarı" sanılır.
$ErrorActionPreference = 'Continue'

# Python G/Ç'si UTF-8. Ölçüldü (Windows-1252 ANSI, tr-TR): bu ayarlar yokken borudan yazan Python, yolunda Ğ/ş/ı
# olan sys.executable'da UnicodeEncodeError ile çöküyor (sahte "Python yok"); Ö/ü'de ise ANSI yazıp PS'nin UTF-8
# çözümünde yolu bozuyor. PYTHONUTF8 ya da PYTHONIOENCODING tek başına düzeltiyor; ikisi de bu süreç için ayarlanır.
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$script:EskiKodlama = [Console]::OutputEncoding
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }

function Yaz([string]$metin = '') { [Console]::Out.WriteLine($metin) }
function Baslik([string]$metin) { Yaz ''; Yaz "== $metin" }
function Bitir([int]$kod) {
    try { [Console]::OutputEncoding = $script:EskiKodlama } catch { }
    exit $kod
}

function Sor([string]$soru) {
    if ($Evet) { Yaz "$soru [E/h] -> E (-Evet)"; return $true }
    $yanit = Read-Host "$soru [E/h]"
    if ($null -eq $yanit) { Yaz '  (yanıt okunamadı: giriş kapalı -> hayır sayıldı)'; return $false }
    return ($yanit.Trim() -eq '' -or $yanit.Trim() -match '^(e|evet|y|yes)$')
}

function Yol-Esit([string]$a, [string]$b) {
    try {
        $x = [IO.Path]::GetFullPath($a).TrimEnd('\', '/')
        $y = [IO.Path]::GetFullPath($b).TrimEnd('\', '/')
        return ($x -ieq $y)
    } catch { return $false }
}

# Native çağrının çıkış kodu; komut çalıştırılamadıysa (LASTEXITCODE $null kaldıysa) -1.
function Son-Kod {
    if ($null -eq $global:LASTEXITCODE) { return -1 }
    return [int]$global:LASTEXITCODE
}

# Kurulumdan (winget) sonra aynı süreçte PATH yenilenmez: Machine + User Path kayıttan okunur.
function Path-Yenile {
    $m = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $u = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($m, $u) | Where-Object { $_ }) -join ';'
}

# --- araç bulma --------------------------------------------------------------------------------------------------
function Python-Dene([string]$exe, [string[]]$onArg) {
    # Gerçek yorumlayıcının sürümünü ve sys.executable yolunu döndürür; >= 3.9 değilse ya da yol diskte yoksa $null.
    $kod = "import sys;print('%d.%d|%s' % (sys.version_info[0], sys.version_info[1], sys.executable))"
    $global:LASTEXITCODE = $null
    try { $out = & $exe @onArg -c $kod 2>$null } catch { return $null }
    if ((Son-Kod) -ne 0 -or -not $out) { return $null }
    $satir = @($out)[-1].ToString().Trim()
    if ($satir -notmatch '^(\d+)\.(\d+)\|(.+)$') { return $null }
    $surum = [version]"$($Matches[1]).$($Matches[2])"
    $yol = $Matches[3]
    if ($surum -lt [version]'3.9') { Yaz "  Python $surum bulundu ama 3.9 ya da üstü gerekli: $yol"; return $null }
    if (-not (Test-Path -LiteralPath $yol -PathType Leaf)) {
        Yaz "  UYARI: Python'un bildirdiği yol diskte bulunamadı, aday atlandı: $yol"
        return $null
    }
    return [pscustomobject]@{ Yol = $yol; Surum = $surum }
}

function Python-Bul([switch]$BilinenYerler) {
    foreach ($ad in 'python', 'python3') {
        foreach ($c in @(Get-Command $ad -CommandType Application -All -ErrorAction SilentlyContinue)) {
            # Boyuta bakılmaz: WindowsApps alias'ları 0 bayt görünür ama bir kısmı gerçek yorumlayıcıya çıkar (ölçüldü:
            # py.exe/pythonw.exe rc 0). Store yönlendirmesi (python.exe/python3.exe) `-c` ile rc 9009 döner, 0 baytlık
            # geçersiz dosya hiç çalışmaz; ikisi de Python-Dene'de elenir.
            $p = Python-Dene $c.Source @()
            if ($p) { return $p }
        }
    }
    $py = Get-Command py -CommandType Application -ErrorAction SilentlyContinue
    if ($py) {
        $global:LASTEXITCODE = $null
        $liste = & $py.Source -0p 2>$null
        $adaylar = foreach ($s in @($liste)) {
            if ("$s" -match '^\s*-(?:V:)?(\d+)\.(\d+)\S*\s+(?:\*\s+)?(\S.*?\.exe)\s*$') {
                [pscustomobject]@{ Surum = [version]"$($Matches[1]).$($Matches[2])"; Yol = $Matches[3] }
            }
        }
        foreach ($a in @($adaylar | Sort-Object Surum -Descending)) {
            if ($a.Surum -ge [version]'3.9') { $p = Python-Dene $a.Yol @(); if ($p) { return $p } }
        }
        $p = Python-Dene $py.Source @('-3')
        if ($p) { return $p }
    }
    if ($BilinenYerler) {
        $kokler = @((Join-Path "$env:LOCALAPPDATA" 'Programs\Python'), $env:ProgramFiles) | Where-Object { $_ }
        foreach ($k in $kokler) {
            foreach ($d in @(Get-ChildItem -LiteralPath $k -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue |
                             Sort-Object Name -Descending)) {
                $exe = Join-Path $d.FullName 'python.exe'
                if (Test-Path -LiteralPath $exe) { $p = Python-Dene $exe @(); if ($p) { return $p } }
            }
        }
    }
    return $null
}

function Git-Bul([switch]$BilinenYerler) {
    $adaylar = @(Get-Command git -CommandType Application -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    if ($BilinenYerler) {
        $adaylar += @((Join-Path "$env:ProgramFiles" 'Git\cmd\git.exe'), (Join-Path "$env:LOCALAPPDATA" 'Programs\Git\cmd\git.exe'))
    }
    # Diskte olup `git --version` ile çalışmayan adaylar (yol, çıkış kodu, git'in mesajı): 2. adım bunu "bulunamadı"dan
    # ayırır. Ölçüldü (Git 2.55): XDG_CONFIG_HOME'da < ya da | varsa git config yolunu okuyamaz, rc 128 verir.
    $script:GitCalismayan = @()
    foreach ($a in @($adaylar | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $a)) { continue }
        $global:LASTEXITCODE = $null
        $out = @(& $a --version 2>&1 | ForEach-Object { "$_" })
        $kod = Son-Kod
        $surum = @($out | Where-Object { $_ -match '^git version' } | Select-Object -First 1)
        if ($kod -eq 0 -and $surum.Count -gt 0) { return [pscustomobject]@{ Yol = $a; Surum = "$($surum[0])".Trim() } }
        $script:GitCalismayan += ,([pscustomobject]@{ Yol = $a; Kod = $kod; Mesaj = @($out | Where-Object { "$_".Trim() }) })
    }
    return $null
}

function Axet-Bul {
    $c = Get-Command axet-code -CommandType Application -ErrorAction SilentlyContinue
    if ($c) { return [pscustomobject]@{ Yol = $c.Source; PathDe = $true } }
    $varsayilan = Join-Path "$env:LOCALAPPDATA" 'axet-code\bin\axet-code.exe'
    if ($env:LOCALAPPDATA -and (Test-Path -LiteralPath $varsayilan)) { return [pscustomobject]@{ Yol = $varsayilan; PathDe = $false } }
    return $null
}

# winget ile kurmayı dener (sorarak). $true = winget başarıyla bitti (araç yine de yeniden aranmalı).
function Winget-Kur([string]$ad, [string]$id, [string[]]$tarif) {
    $tarifYaz = { foreach ($t in $tarif) { Yaz "  $t" } }
    $w = $null
    if (-not $WingetKapali) { $w = Get-Command winget -ErrorAction SilentlyContinue }
    if ($DenemeModu) {
        Yaz "  [deneme] $ad yok: $(if ($w) { "winget install --id $id -e önerilecekti (sorarak)" } else { 'winget yok; aşağıdaki tarif yazılacaktı' })"
        & $tarifYaz
        return $false
    }
    if (-not $w) {
        Yaz "  winget bulunamadı (ya da kapalı). $ad elle kurulmalı:"
        & $tarifYaz
        return $false
    }
    if (-not (Sor "  $ad bulunamadı. winget ile kurayım mı? (winget install --id $id -e)")) {
        Yaz "  $ad kurulmadı. Elle kurmak için:"
        & $tarifYaz
        return $false
    }
    $global:LASTEXITCODE = $null
    & $w.Source install --id $id -e --source winget --accept-package-agreements --accept-source-agreements |
        ForEach-Object { Yaz "$_" }
    $kod = Son-Kod
    if ($kod -ne 0) {
        Yaz "  winget $ad kurulumunda hata verdi (çıkış kodu $kod). Elle kurmak için:"
        & $tarifYaz
        return $false
    }
    Path-Yenile
    return $true
}

function Git-Calistir([string[]]$argumanlar) {
    # git stdout'u fonksiyonun dönüş değerine karışmasın diye ekrana aktarılır (stderr doğrudan akar).
    $global:LASTEXITCODE = $null
    & $script:GIT @argumanlar | ForEach-Object { Yaz "$_" }
    return (Son-Kod)
}
function Git-Oku([string[]]$argumanlar) {
    $global:LASTEXITCODE = $null
    $out = & $script:GIT @argumanlar 2>$null
    $script:GitKod = Son-Kod
    return (@($out) | ForEach-Object { "$_" })
}
function Python-Calistir([string[]]$argumanlar) {
    $global:LASTEXITCODE = $null
    & $script:PY @argumanlar | ForEach-Object { Yaz "$_" }
    return (Son-Kod)
}

function Config-Yolu {
    $kok = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { Join-Path $env:USERPROFILE '.config' }
    return (Join-Path $kok 'axet-code\axet-code.json')
}

# Yolun junction/symlink'leri çözülmüş hâli. install.py klon kökünü Path(__file__).resolve() ile yazar; karşılaştırma bu
# hâlle yapılır. Ölçüldü (PS 5.1): [IO.Path]::GetFullPath junction'ı çözmez, Python Path.resolve() asıl klasörü verir.
# Çözülemezse $null döner, neden $script:GercekYolHata'dadır. Çözülmemiş yola DÜŞÜLMEZ: düşülürse junction'lı hedefte
# aktif klon "başka klon" sanılır ve --uninstall önerilir.
# Yol AXETYOL: önekli TEK satırdan alınır: ölçüldü, stdout'a yazan bir sitecustomize/atexit satırı son satır olunca
# "son satır" yol sanılıyordu. Önekli satır yok ya da birden çoksa çözülemedi sayılır.
function Gercek-Yol([string]$yol) {
    $script:GercekYolHata = $null
    if (-not $script:PY) { $script:GercekYolHata = 'Python yok'; return $null }
    $global:LASTEXITCODE = $null
    $out = @(& $script:PY -c 'import pathlib,sys; print(''AXETYOL:''+str(pathlib.Path(sys.argv[1]).resolve()))' $yol 2>$null |
             ForEach-Object { "$_" })
    $kod = Son-Kod
    if ($kod -ne 0) { $script:GercekYolHata = "Python yolu çözemedi (çıkış kodu $kod): $yol"; return $null }
    $isaretli = @($out | Where-Object { $_.StartsWith('AXETYOL:') } | ForEach-Object { $_.Substring(8).Trim() })
    if ($isaretli.Count -ne 1 -or -not $isaretli[0]) {
        $script:GercekYolHata = "Python çıktısında tek bir AXETYOL: satırı yok ($($isaretli.Count) adet): $yol"
        return $null
    }
    return $isaretli[0]
}

# Global config'teki aXet çekirdek yollarından klon köklerini çıkarır (…/core/00-temel.md -> klon kökü).
# JSON Python ile okunur: ölçüldü, PS 5.1 ConvertFrom-Json anahtarları harf duyarsız okur ve install.py'nin
# (aXet izin eşleşmesi harfe duyarlı olduğu için bilerek) harf varyantlarıyla yazdığı desenlerde "duplicated keys" verir.
function Config-Klonlari {
    $f = Config-Yolu
    if (-not (Test-Path -LiteralPath $f)) { return @() }
    # ~ Python'da açılır (Config-Girisleri ile aynı expanduser): açılmazsa GetFullPath "<cwd>\~\..." üretir (ölçüldü).
    $kod = "import json,sys,os; c=json.load(open(sys.argv[1],encoding='utf-8-sig')); o=c.get('options') or {}; print('\n'.join(os.path.expanduser(str(p)) for p in (o.get('context_paths') or [])))"
    $global:LASTEXITCODE = $null
    $satirlar = & $script:PY -c $kod $f 2>$null
    if ((Son-Kod) -ne 0) {
        Yaz "  UYARI: $f okunamadı ya da beklenen biçimde değil; önceki kurulum kontrol edilemedi (install.py ayrıca denetler)."
        return @()
    }
    $kokler = @()
    foreach ($p in @($satirlar)) {
        if ("$p" -match '^(.+)[\\/]core[\\/]00-temel\.md$') {
            try { $k = [IO.Path]::GetFullPath($Matches[1]) } catch { continue }
            if (-not ($kokler | Where-Object { Yol-Esit $_ $k })) { $kokler += $k }
        }
    }
    return $kokler
}

# Config'te bir klon kökünün altını gösteren girişler (install.py'nin yazdığı üç yer): "bölüm: değer" satırları.
# Yollar install.py _norm gibi karşılaştırılır (normcase + abspath; ayrıca ~ açılır: "C:/x/../eski", "~/eski" de eşleşir).
# $aktif (etkin klonun çözülmüş kökü) altındaki girişler listelenmez: bayat kök etkin klonun atası ya da sürücü kökü
# olduğunda etkin klonun kayıtları "sil" diye gösterilmesin. Bozuk tipli config bölümleri atlanır.
# Python kodunda çift tırnak yok: PS 5.1 native argümandaki gömülü çift tırnağı kaçışlamaz (Config-Klonlari ile aynı).
function Config-Girisleri([string]$kok, [string]$aktif) {
    $f = Config-Yolu
    if (-not (Test-Path -LiteralPath $f)) { return @() }
    $kod = "import json,sys,os; c=json.load(open(sys.argv[1],encoding='utf-8-sig')); c=c if isinstance(c,dict) else {}; n=lambda s: os.path.normcase(os.path.abspath(os.path.expanduser(s))); alt=lambda s,k: isinstance(s,str) and (n(s)+os.sep).startswith(k.rstrip(os.sep)+os.sep); k=n(sys.argv[2]); a=n(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3] else None; sec=lambda s: alt(s,k) and not (a and alt(s,a)); o=c.get('options'); o=o if isinstance(o,dict) else {}; p=c.get('permissions'); r=p.get('rules') if isinstance(p,dict) else None; r=r if isinstance(r,dict) else {}; print('\n'.join(['options.'+b+': '+x for b in ('context_paths','skills_paths') if isinstance(o.get(b),list) for x in o[b] if sec(x)]+['permissions.rules.'+d+': '+x for d,v in r.items() if isinstance(v,dict) for x in v if sec(x.rstrip('*'))]))"
    $global:LASTEXITCODE = $null
    $satirlar = & $script:PY -c $kod $f $kok $aktif 2>$null
    if ((Son-Kod) -ne 0) { return @("(girişler okunamadı: $f)") }
    return @($satirlar | ForEach-Object { "$_" } | Where-Object { $_.Trim() })
}

# Klasör bu aXet template'inin klonu mu? Eksik imzaların listesini döndürür (boş = template).
function Template-Eksikleri([string]$kok) {
    $eksik = @()
    $core = Join-Path $kok 'core\00-temel.md'
    if (-not (Test-Path -LiteralPath $core -PathType Leaf)) {
        $eksik += 'core\00-temel.md'
    } else {
        $imza = $false
        try { $imza = [bool](@([IO.File]::ReadAllLines($core)) | Where-Object { $_ -match '^CORE-ID:\s*AXET-CORE-' } | Select-Object -First 1) } catch { }
        if (-not $imza) { $eksik += 'core\00-temel.md içinde "CORE-ID: AXET-CORE-" satırı' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $kok 'scripts\install.py') -PathType Leaf)) { $eksik += 'scripts\install.py' }
    if (-not (Test-Path -LiteralPath (Join-Path $kok 'skills-sap') -PathType Container)) { $eksik += 'skills-sap\' }
    return $eksik
}

# Karşılaştırma için kaynak anahtarı: sondaki / \ ve .git atılır, yerel yol tam yola çevrilir, harf farkı yok sayılır.
function Kaynak-Anahtari([string]$k) {
    $s = "$k".Trim().TrimEnd('/', '\')
    if ($s -imatch '\.git$') { $s = $s.Substring(0, $s.Length - 4) }
    if ($s -notmatch '^[a-zA-Z][a-zA-Z0-9+.-]*://' -and $s -notmatch '^[^@/\\]+@[^:/\\]+:') {
        try { $s = [IO.Path]::GetFullPath($s).TrimEnd('\', '/') } catch { }
    }
    return $s.ToLowerInvariant()
}

# =================================================================================================================
try {
    # --- 0. Parametre doğrulama (hiçbir işlemden ÖNCE) -------------------------------------------------------------
    # Ölçüldü: kur.cmd'ye tırnaklı ve sonu ters bölü ile biten bir yol verilince ("C:\c b\") Windows \" dizisini
    # kaçışlı tırnak sayar; sonraki bütün parametreler (-DenemeModu, -WingetKapali dahil) bu değerin içine düşer.
    foreach ($ciftAd in @(@('-Hedef', $Hedef), @('-Kaynak', $Kaynak))) {
        if ("$($ciftAd[1])".Contains('"')) {
            Yaz "DURDU: $($ciftAd[0]) değerinde tırnak işareti var: $($ciftAd[1])"
            Yaz '  Büyük olasılıkla yol tırnak içinde ve ters bölü ile bitiyor (örn. -Hedef "C:\klasör\"). Windows bunu'
            Yaz '  kaçışlı tırnak sayar ve sonraki parametreleri yutar. Yolu ters bölü ile BİTİRME: -Hedef "C:\klasör"'
            Bitir 1
        }
    }
    try {
        $Hedef = [IO.Path]::GetFullPath($Hedef)
    } catch {
        Yaz "DURDU: -Hedef geçerli bir yol değil: $Hedef ($($_.Exception.Message))"
        Bitir 1
    }
    if ($Hedef.Length -gt 3) { $Hedef = $Hedef.TrimEnd('\', '/') }
    if ($Kaynak.Length -gt 3) { $Kaynak = $Kaynak.TrimEnd('\') }

    $islem = if ($Kaldir) { 'KALDIR' } else { 'KUR/GÜNCELLE' }
    Yaz "aXet template kurulumu · işlem: $islem$(if ($DenemeModu) { ' · DENEME MODU (hiçbir şey yazılmaz/kurulmaz)' })"
    Yaz "  Klon   : $Hedef"
    if (-not $Kaldir) { Yaz "  Kaynak : $Kaynak" }
    Yaz "  Config : $(Config-Yolu)"

    # --- KALDIR ----------------------------------------------------------------------------------------------------
    if ($Kaldir) {
        Baslik 'Kaldırma'
        $eksik = @(Template-Eksikleri $Hedef)
        if ($eksik.Count -gt 0) {
            Yaz "DURDU: $Hedef bu aXet template'inin klonu değil (eksik: $($eksik -join ', ')). Hiçbir betik çalıştırılmadı."
            Yaz '  -Hedef ile doğru klasörü ver.'
            Bitir 1
        }
        $python = Python-Bul
        if (-not $python) { Yaz 'DURDU: Python 3.9+ bulunamadı; kaldırma install.py ile yapılır.'; Bitir 2 }
        $script:PY = $python.Yol
        Yaz '  Not: kaldırma, bu klonda açılmış SAP''ye yazma iznini de kapatır (izin dosyasını siler).'
        $arg = @((Join-Path $Hedef 'scripts\install.py'), '--uninstall') + $(if ($DenemeModu) { @('--dry-run') } else { @() })
        $kod = Python-Calistir $arg
        if ($kod -ne 0) { Yaz "DURDU: install.py --uninstall $(if ($kod -eq -1) { 'çalıştırılamadı' } else { "çıkış kodu $kod" })."; Bitir 1 }
        Yaz ''
        if ($DenemeModu) { Yaz '[deneme] Config değiştirilmedi.'; Bitir 0 }
        Yaz "Global config'ten bu klonun kayıtları kaldırıldı. Klon klasörü SİLİNMEDİ: $Hedef"
        Yaz 'Klasörü de silmek istersen (geri alınamaz; önce içinde kendi değişikliğin olmadığından emin ol):'
        Yaz "  Remove-Item -LiteralPath '$Hedef' -Recurse -Force"
        Bitir 0
    }

    # --- 1. aXet ---------------------------------------------------------------------------------------------------
    Baslik '1/5 Ön koşul: aXet'
    $axet = Axet-Bul
    if (-not $axet) {
        Yaz 'DURDU: aXet (axet-code) bulunamadı: PATH içinde yok ve %LOCALAPPDATA%\axet-code\bin\axet-code.exe yok.'
        Yaz '  aXet şirket kanalından kurulur (bu betik aXet kurmaz). aXet''i kurup girişini yaptıktan sonra'
        Yaz '  YENİ bir terminalde kur.cmd''yi tekrar çalıştır.'
        Bitir 2
    }
    Yaz "  OK aXet: $($axet.Yol)"
    if (-not $axet.PathDe) {
        Yaz '  UYARI: axet-code PATH içinde değil (varsayılan yerde bulundu). Yeni terminal aç; hâlâ yoksa aXet kurulumunu'
        Yaz '         kontrol et. install.py ve doctor.py bu yüzden axet-code için uyarı gösterebilir.'
    }

    # --- 2. Git ve Python ------------------------------------------------------------------------------------------
    Baslik '2/5 Ön koşul: Git ve Python'
    $eksikArac = $false
    $yeniTerminal = $false
    $script:GIT = $null
    $script:PY = $null
    $g = Git-Bul
    if (-not $g -and @($script:GitCalismayan).Count -gt 0) {
        # XDG notu yalnız kanıt varsa: git'in mesajı config yolunu okuyamadığını söylüyor ya da değer geçersiz karakter taşıyor.
        $gitMetni = (@($script:GitCalismayan | ForEach-Object { @($_.Mesaj) }) -join "`n")
        $xdgIlgili = [bool]$env:XDG_CONFIG_HOME -and (($gitMetni -match 'unable to access') -or ($env:XDG_CONFIG_HOME -match '[<>|"?*]'))
        if ($xdgIlgili) {
            Yaz '  EKSİK: Git bulundu ama çalışmadı (git --version hata verdi). Git''in mesajı:'
        } else {
            Yaz '  EKSİK: git çalıştırılamadı (git --version hata verdi):'
        }
        foreach ($c in $script:GitCalismayan) {
            Yaz "    $($c.Yol) (çıkış kodu $($c.Kod))"
            foreach ($s in @($c.Mesaj)) { Yaz "      $s" }
        }
        if ($xdgIlgili) {
            Yaz "  Neden: git kendi config'ini XDG_CONFIG_HOME altında arar ve bu yolu okuyamıyor. Şu anki değer: $env:XDG_CONFIG_HOME"
            Yaz '  Değeri düzelt (< > | " ? * gibi karakter olmamalı) ya da kaldır; YENİ bir terminalde tekrar çalıştır. Git''i yeniden kurmak bunu düzeltmez.'
        } else {
            Yaz '  Yukarıdaki git.exe''nin kendi terminalinde "git --version" ile çalıştığını kontrol et; çalışınca kur.cmd''yi tekrar çalıştır.'
        }
        $eksikArac = $true
    } elseif (-not $g) {
        Yaz '  EKSİK: Git bulunamadı.'
        $tarif = @('Kurulacak: Git for Windows (varsayılan seçenekler yeterli).', 'Resmi indirme: https://git-scm.com/download/win',
                   'winget ile: winget install --id Git.Git -e')
        if (Winget-Kur 'Git' 'Git.Git' $tarif) {
            $g = Git-Bul -BilinenYerler
            if (-not $g) { $yeniTerminal = $true }
        }
        if (-not $g) { $eksikArac = $true }
    }
    if ($g) { $script:GIT = $g.Yol; Yaz "  OK Git: $($g.Surum) ($($g.Yol))" }

    $python = Python-Bul
    if (-not $python) {
        Yaz '  EKSİK: Python 3.9 ya da üstü bulunamadı.'
        $tarif = @('Kurulacak: Python 3 (3.9 ya da üstü; kurulumda "Add python.exe to PATH" işaretli olsun).',
                   'Resmi indirme: https://www.python.org/downloads/windows/',
                   'winget ile: winget install --id Python.Python.3.14 -e')
        if (Winget-Kur 'Python' 'Python.Python.3.14' $tarif) {
            $python = Python-Bul -BilinenYerler
            if (-not $python) { $yeniTerminal = $true }
        }
        if (-not $python) { $eksikArac = $true }
    }
    if ($python) { $script:PY = $python.Yol; Yaz "  OK Python: $($python.Surum) ($($python.Yol))" }

    if ($yeniTerminal) {
        Yaz ''
        Yaz 'DURDU: Kurulum bitti ama araç bu terminalde hâlâ bulunamıyor. YENİ bir terminal aç ve kur.cmd''yi tekrar çalıştır.'
        Bitir 3
    }
    if ($eksikArac) {
        Yaz ''
        if ($DenemeModu) { Yaz '[deneme] Eksik ön koşul var; gerçek çalıştırmada burada durulurdu.'; Bitir 2 }
        Yaz 'DURDU: Eksik ön koşul var (yukarıda). Kurduktan sonra YENİ bir terminalde kur.cmd''yi tekrar çalıştır.'
        Bitir 2
    }

    # --- 3. rg (isteğe bağlı) --------------------------------------------------------------------------------------
    Baslik '3/5 İsteğe bağlı: rg (ripgrep)'
    $rg = Get-Command rg -CommandType Application -ErrorAction SilentlyContinue
    if ($rg) {
        Yaz "  OK rg: $($rg.Source)"
    } else {
        Yaz '  rg yok: aXet''in arama aracı yavaş çalışır (zorunlu değil).'
        $tarif = @('İsteğe bağlı: winget install --id BurntSushi.ripgrep.MSVC -e', 'Resmi indirme: https://github.com/BurntSushi/ripgrep/releases')
        if (Winget-Kur 'rg (ripgrep)' 'BurntSushi.ripgrep.MSVC' $tarif) {
            Yaz '  rg kuruldu; aXet''in görmesi için yeni terminal ve yeni aXet oturumu gerekir.'
        }
    }

    # --- 4. Klon / güncelleme --------------------------------------------------------------------------------------
    Baslik '4/5 Template klonu'
    $yeniKlon = $false
    $klonla = $false
    if (-not (Test-Path -LiteralPath $Hedef)) {
        $klonla = $true
    } elseif (-not (Test-Path -LiteralPath $Hedef -PathType Container)) {
        Yaz "DURDU: $Hedef bir klasör değil (dosya). -Hedef ile başka bir yol ver."
        Bitir 1
    } else {
        # Kök mü: `rev-parse --show-cdup` boş = kök. Ölçüldü (Git 2.55): junction'lı yolda --show-toplevel çözümlenmiş
        # asıl yolu döndürür (yol karşılaştırması tutmaz); --show-cdup junction ve asıl klasörde aynı ("" kök, "../" alt).
        $cdup = Git-Oku @('-C', $Hedef, 'rev-parse', '--show-cdup')
        $gitKok = ($script:GitKod -eq 0 -and -not (@($cdup) | Where-Object { "$_".Trim() }))
        if ($script:GitKod -ne 0 -and (Test-Path -LiteralPath (Join-Path $Hedef '.git'))) {
            $global:LASTEXITCODE = $null
            $gitHata = @(& $script:GIT -C $Hedef rev-parse --show-toplevel 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ })
            $gitHataKod = Son-Kod
            Yaz "DURDU: $Hedef içinde .git var ama git bu klasörü okuyamadı (çıkış kodu $gitHataKod). Hiçbir şey değiştirilmedi. Git'in mesajı:"
            foreach ($s in $gitHata) { Yaz "    $s" }
            if (($gitHata -join "`n") -match 'dubious ownership') {
                $oneri = @($gitHata | Where-Object { $_ -match 'git config --global --add safe\.directory' } | Select-Object -First 1)
                Yaz '  Neden: git klasörü başka bir kullanıcıya ait görüyor (ağ paylaşımı/UNC yolu ya da başka hesapla oluşturulmuş klasör).'
                Yaz '  Bu klasöre güveniyorsan KENDİ terminalinde şu komutu çalıştır (kur.ps1 bunu kendisi ÇALIŞTIRMAZ):'
                if ($oneri.Count -gt 0) { Yaz "    $("$($oneri[0])".Trim())" } else { Yaz "    git config --global --add safe.directory '$($Hedef.Replace('\', '/'))'" }
                Yaz '  Sonra kur.cmd''yi tekrar çalıştır.'
            }
            Bitir 1
        }
        if (-not $gitKok) {
            $bos = -not (Get-ChildItem -LiteralPath $Hedef -Force -ErrorAction SilentlyContinue | Select-Object -First 1)
            if ($bos) {
                $klonla = $true
            } else {
                Yaz "DURDU: $Hedef var ama bir git klonunun kökü değil. İçindekilere dokunulmadı."
                Yaz '  Başka bir klasör ver (-Hedef) ya da bu klasörü kendin boşalt/taşı, sonra tekrar çalıştır.'
                Bitir 1
            }
        } else {
            # Yabancı bir repoda fetch/pull YAPILMAZ ve betikleri ÇALIŞTIRILMAZ: önce bu template olduğu doğrulanır.
            $eksik = @(Template-Eksikleri $Hedef)
            if ($eksik.Count -gt 0) {
                Yaz "DURDU: $Hedef bir git reposu ama bu aXet template'inin klonu değil (eksik: $($eksik -join ', '))."
                Yaz '  Güncelleme yapılmadı, o reponun hiçbir betiği çalıştırılmadı. -Hedef ile başka bir klasör ver.'
                Bitir 1
            }
            $origin = Git-Oku @('-C', $Hedef, 'remote', 'get-url', 'origin')
            if ($script:GitKod -eq 0 -and $origin -and ((Kaynak-Anahtari (@($origin)[0])) -ne (Kaynak-Anahtari $Kaynak))) {
                Yaz "  UYARI: klonun kaynağı '$(@($origin)[0])', istenen kaynak '$Kaynak'. Klonun kendi kaynağından güncellenecek."
            }
            $dal = Git-Oku @('-C', $Hedef, 'symbolic-ref', '--short', '-q', 'HEAD')
            if ($script:GitKod -ne 0 -or -not $dal) { Yaz "DURDU: $Hedef bir dalda değil (detached HEAD). Hiçbir şey değiştirilmedi."; Bitir 1 }
            $degisik = Git-Oku @('--no-optional-locks', '-C', $Hedef, 'status', '--porcelain', '--untracked-files=no')
            if ($script:GitKod -ne 0) { Yaz "DURDU: git status başarısız ($Hedef)."; Bitir 1 }
            if (@($degisik | Where-Object { $_ }).Count -gt 0) {
                Yaz "DURDU: $Hedef içinde yerel değişiklik var; güncelleme YAPILMADI, hiçbir dosyaya dokunulmadı:"
                foreach ($s in @($degisik | Where-Object { $_ } | Select-Object -First 20)) { Yaz "    $s" }
                Yaz '  Bu değişiklikler senin mi? Saklamak istiyorsan başka yere kopyala; sonra klonu temizleyip tekrar çalıştır.'
                Bitir 1
            }
            if ($DenemeModu) {
                Yaz "  [deneme] güncellenecekti: git -C $Hedef pull --ff-only (dal: $(@($dal)[0]); yerel değişiklik yok)"
            } else {
                Yaz "  Güncelleme kontrolü (dal: $(@($dal)[0]))"
                if ((Git-Calistir @('-C', $Hedef, 'fetch', '--quiet')) -ne 0) { Yaz 'DURDU: git fetch başarısız; yukarıdaki git çıktısına bak.'; Bitir 1 }
                $sayim = Git-Oku @('-C', $Hedef, 'rev-list', '--left-right', '--count', 'HEAD...@{u}')
                if ($script:GitKod -ne 0 -or "$(@($sayim)[0])" -notmatch '^(\d+)\s+(\d+)$') {
                    Yaz "DURDU: $Hedef dalının izlediği uzak dal (upstream) yok; güncelleme yapılamadı."
                    Bitir 1
                }
                $onde = [int]$Matches[1]; $geride = [int]$Matches[2]
                if ($onde -gt 0) {
                    Yaz "DURDU: klon uzak daldan ayrışmış (yerelde $onde commit, uzakta $geride commit fark). Güncelleme YAPILMADI."
                    Yaz '  Yerel commit''lerin senin işin olabilir; hiçbir şey silinmedi. Ne yapacağına emin değilsen destek iste.'
                    Bitir 1
                }
                if ($geride -eq 0) {
                    Yaz '  Değişiklik yok; klon zaten güncel.'
                } else {
                    if ((Git-Calistir @('-C', $Hedef, 'pull', '--ff-only')) -ne 0) { Yaz 'DURDU: git pull --ff-only başarısız; hiçbir şey zorlanmadı. Yukarıdaki git çıktısına bak.'; Bitir 1 }
                    Yaz "  Güncellendi ($geride yeni commit)."
                }
            }
        }
    }
    if ($klonla) {
        if ($DenemeModu) {
            Yaz "  [deneme] klonlanacaktı: git clone $Kaynak $Hedef"
        } else {
            Yaz "  Klonlanıyor: $Kaynak -> $Hedef"
            $ustKlasor = Split-Path -Parent $Hedef
            if ($ustKlasor -and -not (Test-Path -LiteralPath $ustKlasor)) { New-Item -ItemType Directory -Path $ustKlasor -Force | Out-Null }
            if ((Git-Calistir @('clone', '--', $Kaynak, $Hedef)) -ne 0) {
                Yaz "DURDU: git clone başarısız (kaynak: $Kaynak). Ağ/erişim ya da adres hatası olabilir; yukarıdaki git çıktısına bak."
                Bitir 1
            }
            $yeniKlon = $true
            $eksik = @(Template-Eksikleri $Hedef)
            if ($eksik.Count -gt 0) {
                Yaz "DURDU: klonlanan kaynak bu aXet template'i değil (eksik: $($eksik -join ', ')). Hiçbir betiği çalıştırılmadı."
                Yaz "  Klon $Hedef içinde duruyor; -Kaynak adresini kontrol et."
                Bitir 1
            }
        }
    }

    # --- 5. install.py --sap + doctor.py ---------------------------------------------------------------------------
    Baslik '5/5 aXet config kurulumu ve doğrulama'
    $installPy = Join-Path $Hedef 'scripts\install.py'
    $doctorPy = Join-Path $Hedef 'scripts\doctor.py'
    $onceki = @(Config-Klonlari)
    # Config'teki kökler install.py'nin çözülmüş yoludur: -Hedef junction ise çözülmüş hâliyle de karşılaştırılır, yoksa
    # 2. koşumda AKTİF klon "başka klon" sanılıp --uninstall önerilir (ölçüldü). Çözülemezse karşılaştırma ÖLÇÜLEMEDİ:
    # hiçbir kaldırma/bayat-kayıt önerisi yapılmaz.
    $HedefGercek = Gercek-Yol $Hedef
    $bayat = @()
    $baska = @()
    if ($null -eq $HedefGercek) {
        $farkli = @($onceki | Where-Object { -not (Yol-Esit $_ $Hedef) })
        if ($farkli.Count -gt 0) {
            Yaz "  DİKKAT: klon karşılaştırması ÖLÇÜLEMEDİ: $($script:GercekYolHata)"
            Yaz "          config'te kayıtlı klon: $($farkli -join ', ')"
            Yaz '          Bu klonun kendisi olabilir (junction/symlink ile verilen -Hedef). Aynı klasör mü elle kontrol et;'
            Yaz '          kur.ps1 bu durumda hiçbir kaydın kaldırılmasını önermez.'
        } elseif ($onceki.Count -gt 0) {
            Yaz '  Config zaten bu klonu gösteriyor; kayıtlar yenilenecek.'
        }
    } else {
        # Config'teki kök de çözülüp çözülmüş hâlle karşılaştırılır: config junction'lı biçimi tutup kur gerçek yolla
        # çalışınca AKTİF klon "başka klon" sanılıyordu (ölçüldü). Kök çözülemezse o kök için ÖLÇÜLEMEDİ: öneri yok.
        $olculemeyen = @()
        foreach ($o in $onceki) {
            if ((Yol-Esit $o $Hedef) -or (Yol-Esit $o $HedefGercek)) { continue }
            $oGercek = Gercek-Yol $o
            if ($null -eq $oGercek) { $olculemeyen += $o; Yaz "  DİKKAT: config'teki klonla karşılaştırma ÖLÇÜLEMEDİ: $($script:GercekYolHata)"; continue }
            if (-not (Yol-Esit $oGercek $HedefGercek)) { $baska += $o }
        }
        if ($olculemeyen.Count -gt 0) {
            Yaz "          config'te kayıtlı klon: $($olculemeyen -join ', ')"
            Yaz '          Bu klonun kendisi olabilir (junction/symlink). Aynı klasör mü elle kontrol et;'
            Yaz '          kur.ps1 bu kök için hiçbir kaydın kaldırılmasını ya da bayat sayılmasını önermez.'
        }
        # Kayıtlı ama install.py'si diskte olmayan klon (silinmiş/taşınmış): --uninstall önerilemez, kayıt bayattır.
        # Bu klonun install.py'si onu temizlemez: is_ours yalnız kendi klonunun altındaki yolları siler (install.py).
        $bayat = @($baska | Where-Object { -not (Test-Path -LiteralPath (Join-Path $_ 'scripts\install.py') -PathType Leaf) })
        $baska = @($baska | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'scripts\install.py') -PathType Leaf })
        foreach ($b in $bayat) {
            Yaz "  DİKKAT: config'te kayıtlı klon klasörü yok; kayıt bayat: $b"
            Yaz '          Bu kurulum o kayıtları silmez; elle silinecek girişler sonda listelenir.'
        }
        if ($baska.Count -gt 0) {
            Yaz "  DİKKAT: önceki kurulum şu klonu gösteriyordu: $($baska -join ', ')"
            Yaz "          şimdi bu klon eklenecek: $Hedef"
            Yaz '          install.py yalnız kendi klonunun kayıtlarını yönetir; öncekinin kayıtları config''te KALIR ve iki'
            Yaz '          çekirdek birden yüklenebilir. Önceki klonu artık kullanmayacaksan onun kayıtlarını PowerShell''de kaldır.'
            Yaz '          Bu komut o klonda açılmış SAP''ye yazma iznini de KAPATIR (izin dosyasını siler):'
            foreach ($b in $baska) { Yaz "            & `"$($script:PY)`" `"$(Join-Path $b 'scripts\install.py')`" --uninstall" }
        } elseif ($onceki.Count -gt 0 -and $olculemeyen.Count -eq 0) {
            Yaz '  Config zaten bu klonu gösteriyor; kayıtlar yenilenecek.'
        }
    }

    if ($DenemeModu) {
        if (-not (Test-Path -LiteralPath $Hedef)) {
            Yaz "  [deneme] çalıştırılacaktı: python $installPy --sap"
        } elseif (@(Template-Eksikleri $Hedef).Count -eq 0) {
            Yaz '  [deneme] install.py --sap --dry-run çıktısı:'
            $kod = Python-Calistir @($installPy, '--sap', '--dry-run')
            if ($kod -ne 0) { Yaz "DURDU: install.py --sap --dry-run $(if ($kod -eq -1) { 'çalıştırılamadı' } else { "çıkış kodu $kod" })."; Bitir 1 }
        }
        Yaz "  [deneme] çalıştırılacaktı: python $doctorPy"
        Yaz ''
        Yaz 'DENEME MODU bitti: hiçbir dosya, klon ya da config yazılmadı.'
        Bitir 0
    }

    $eksik = @(Template-Eksikleri $Hedef)
    if ($eksik.Count -gt 0) { Yaz "DURDU: $Hedef bu aXet template'inin klonu değil (eksik: $($eksik -join ', '))."; Bitir 1 }
    $kod = Python-Calistir @($installPy, '--sap')
    if ($kod -ne 0) { Yaz "DURDU: install.py --sap $(if ($kod -eq -1) { "çalıştırılamadı ($($script:PY))" } else { "çıkış kodu $kod (yukarıdaki çıktıya bak)" })."; Bitir 1 }

    Yaz ''
    Yaz '-- doctor.py --'
    $doctorKod = $null
    Push-Location -LiteralPath $Hedef
    try {
        $doctorKod = Python-Calistir @($doctorPy)
    } finally {
        Pop-Location
    }

    Yaz ''
    Yaz '================================================================================'
    $doctorTamam = ($null -ne $doctorKod -and $doctorKod -eq 0)
    if (-not $doctorTamam) {
        Yaz "Kurulum yazıldı ama doctor.py doğrulaması geçmedi ($(if ($doctorKod -eq -1 -or $null -eq $doctorKod) { 'çalıştırılamadı' } else { "çıkış kodu $doctorKod" })). Yukarıdaki [FAIL] satırlarına bak."
    } else {
        Yaz "Kurulum tamam$(if ($yeniKlon) { ' (yeni klon)' } else { '' }). Klon: $Hedef"
    }
    if ($bayat.Count -gt 0) {
        Yaz ''
        Yaz "BAYAT KAYIT: config'te klasörü artık olmayan klon kayıtlı. kur.ps1 config'e otomatik yazmaz; şu dosyayı aç:"
        Yaz "    $(Config-Yolu)"
        Yaz '  ve aşağıdaki girişleri sil (JSON bölümü: değer), sonra YENİ bir aXet oturumu aç:'
        foreach ($b in $bayat) {
            $girisler = @(Config-Girisleri $b $HedefGercek)
            if ($girisler.Count -eq 0) { Yaz "    ($b için giriş kalmamış)" }
            foreach ($s in $girisler) { Yaz "    $s" }
        }
    }
    if ($baska.Count -gt 0) {
        Yaz ''
        if ($doctorTamam) {
            Yaz 'ÖNCE BUNU YAP: config''te başka bir aXet template klonu da kayıtlı; iki çekirdek birden yüklenebilir.'
        } else {
            Yaz 'ÖNCE BUNU YAP: config''te başka bir aXet template klonu da kayıtlı; doctor''ın FAIL satırları büyük olasılıkla bundan.'
            Yaz '  FAIL satırlarındaki "yeniden adlandır" önerisini UYGULAMA (template skill''lerinin adı değiştirilmez).'
        }
        Yaz '  Önce eski klonun kayıtlarını PowerShell''de kaldır (o klonda açılmış SAP''ye yazma iznini de kapatır):'
        foreach ($b in $baska) { Yaz "    & `"$($script:PY)`" `"$(Join-Path $b 'scripts\install.py')`" --uninstall" }
        Yaz '  Sonra kur.cmd''yi tekrar çalıştır.'
    }
    Yaz 'SONRAKİ ADIM:'
    Yaz '  1. YENİ bir aXet oturumu aç (açık oturumlar yeni ayarı görmez).'
    Yaz '     İlk yanıtın ilk satırında AXET-CORE görünmeli; görünmüyorsa kurulum çalışmıyordur.'
    Yaz '  2. İlk proje için: aXet içinde %yeni-proje yaz'
    Yaz "     ya da proje klasöründe: `"$(Join-Path $Hedef 'yeni-proje.cmd')`""
    Yaz '  Güncellemek için bu komutu tekrar çalıştır; kaldırmak için: kur.cmd -Kaldir'
    if (-not $doctorTamam) { Bitir 4 }
    Bitir 0
} catch {
    Yaz ''
    Yaz "DURDU: beklenmeyen hata, kurulum yarıda kaldı: $($_.Exception.Message)"
    Yaz "  Konum: $($_.InvocationInfo.ScriptName):$($_.InvocationInfo.ScriptLineNumber)"
    Bitir 1
}
