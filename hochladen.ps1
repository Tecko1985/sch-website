# =========================================================
#  SCH-Website hochladen (GitHub Pages)
#  Doppelklick auf hochladen.bat – oder: Rechtsklick > Mit PowerShell ausführen
# =========================================================
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$Seite = 'https://tecko1985.github.io/sch-website/'
$utf8  = New-Object System.Text.UTF8Encoding($false)

function Ende($text, $farbe = 'Green') {
    Write-Host ""; Write-Host $text -ForegroundColor $farbe
    Read-Host "`nEnter zum Schließen" | Out-Null; exit
}

Write-Host "=== SCH-Website hochladen ===" -ForegroundColor Cyan

# 1) Git vorhanden?
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Ende "Git ist nicht installiert. Einmalig in PowerShell ausführen:`n  winget install --id Git.Git -e`nDanach dieses Skript erneut starten." 'Red'
}
if (-not (Test-Path '.git')) {
    Ende "Dieser Ordner ist kein Git-Repo.`nEinmalig klonen:`n  git clone https://github.com/tecko1985/sch-website.git`nund das Skript aus dem geklonten Ordner starten." 'Red'
}

# 2) Neuesten Stand holen (eigene Änderungen bleiben erhalten)
Write-Host "`nHole aktuellen Stand von GitHub ..."
git pull --rebase --autostash
if ($LASTEXITCODE -ne 0) { Ende "Pull fehlgeschlagen – vermutlich Konflikt. Bitte melden." 'Red' }

# 3) Änderungen vorhanden?
$aenderungen = git status --porcelain
if (-not $aenderungen) { Ende "Keine Änderungen – nichts hochzuladen." 'Yellow' }

Write-Host "`nGeänderte Dateien:" -ForegroundColor Cyan
$aenderungen | ForEach-Object { Write-Host "  $_" }

# 4) Cache-Busting: bei geänderten CSS/JS-Dateien ?v=… in den HTML-Dateien hochzählen,
#    damit Besucher nicht die alte Version aus dem Browser-Cache sehen
$geaendert = $aenderungen | ForEach-Object { $_.Substring(3).Trim('"') } |
             Where-Object { $_ -match '^[^/]+\.(css|js)$' }
if ($geaendert) {
    foreach ($html in Get-ChildItem -Filter *.html -File) {
        $inhalt = [IO.File]::ReadAllText($html.FullName)
        $neu = $inhalt
        foreach ($datei in $geaendert) {
            $muster = '(["''/])' + [regex]::Escape($datei) + '(\?v=(\d+))?(["''])'
            $neu = [regex]::Replace($neu, $muster, {
                param($m)
                $v = if ($m.Groups[3].Success) { [int]$m.Groups[3].Value + 1 } else { 1 }
                "$($m.Groups[1].Value)$datei`?v=$v$($m.Groups[4].Value)"
            })
        }
        if ($neu -ne $inhalt) {
            [IO.File]::WriteAllText($html.FullName, $neu, $utf8)
            Write-Host "  Version hochgezählt in $($html.Name)" -ForegroundColor DarkGray
        }
    }
}

# 5) Commit-Nachricht
$standard = "Update " + (Get-Date -Format 'dd.MM.yyyy HH:mm')
$nachricht = Read-Host "`nWas wurde geändert? (Enter = '$standard')"
if ([string]::IsNullOrWhiteSpace($nachricht)) { $nachricht = $standard }

# 6) Hochladen
git add -A
git commit -m $nachricht | Out-Null
Write-Host "`nLade hoch ..."
git push
if ($LASTEXITCODE -ne 0) {
    Ende "Push fehlgeschlagen. Beim ersten Mal öffnet sich ein GitHub-Login – anmelden und Skript erneut starten." 'Red'
}

# 7) Warten bis GitHub Pages die neue Version ausliefert
$commit = (git rev-parse --short HEAD).Trim()
Write-Host "`nHochgeladen (Commit $commit). GitHub Pages baut jetzt neu ..." -ForegroundColor Green
$ziel = Get-Date
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 10
    try {
        $r = Invoke-WebRequest -Uri ($Seite + '?nocache=' + [guid]::NewGuid()) -Method Head -UseBasicParsing
        $stand = [datetime]$r.Headers['Last-Modified']
        if ($stand -gt $ziel.AddMinutes(-1)) { Write-Host "Online!" -ForegroundColor Green; break }
    } catch {}
    Write-Host "  ... noch nicht live ($((($i+1)*10)) s)"
}
Start-Process $Seite
Ende "Fertig. Falls noch die alte Version zu sehen ist: Strg+F5 drücken."
