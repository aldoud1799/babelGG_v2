param(
    [switch]$SkipTests,
    [switch]$SkipExtendedTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe. Create/activate the .venv first."
}

Write-Host "[1/4] Running unit tests..." -ForegroundColor Cyan
if (-not $SkipTests) {
    $testArgs = @("tests/run_all.py")
    if (-not $SkipExtendedTests) {
        $testArgs += "--extended"
    }
    & $pythonExe @testArgs
}
else {
    Write-Host "Skipped tests (-SkipTests)." -ForegroundColor Yellow
}

Write-Host "[2/4] Building EXE with PyInstaller..." -ForegroundColor Cyan
& $pythonExe -m PyInstaller "BabelGG.spec" --clean --noconfirm

$distExe = Join-Path $repoRoot "dist\BabelGG\BabelGG.exe"
if (-not (Test-Path $distExe)) {
    throw "Expected EXE missing: $distExe"
}

$bundledModelsDir = Join-Path $repoRoot "dist\BabelGG\models"
if (Test-Path $bundledModelsDir) {
    $bundledGguf = Get-ChildItem -Path $bundledModelsDir -Filter *.gguf -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($bundledGguf) {
        throw "Packaging regression: bundled GGUF found in dist payload: $($bundledGguf.FullName)"
    }
}

Write-Host "[3/4] Resolving ISCC (Inno Setup compiler)..." -ForegroundColor Cyan
$isccCmd = Get-Command iscc -ErrorAction SilentlyContinue
if ($isccCmd) {
    $isccExe = $isccCmd.Source
}
else {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $isccExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $isccExe) {
    throw "ISCC.exe not found. Install Inno Setup 6 or add ISCC to PATH."
}

Write-Host "Using ISCC: $isccExe" -ForegroundColor DarkGray

Write-Host "[4/4] Building installer..." -ForegroundColor Cyan
& $isccExe "installer_build\babelgg_setup.iss"

$setupExe = Join-Path $repoRoot "installer\BabelGG_Setup.exe"
if (-not (Test-Path $setupExe)) {
    throw "Expected installer missing: $setupExe"
}

Write-Host "" 
Write-Host "Release build complete." -ForegroundColor Green
Write-Host "EXE:    $distExe"
Write-Host "SETUP:  $setupExe"
