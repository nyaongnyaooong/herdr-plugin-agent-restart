$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$runner = Join-Path $PSScriptRoot 'restart-windows.py'
$candidates = @($env:HERDR_PYTHON)
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd -and $cmd.Source -notmatch 'WindowsApps') { $candidates += $cmd.Source }
$candidates += (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
$candidates += 'C:\QMK_MSYS\ucrt64\bin\python.exe'
$python = $null
foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
        & $candidate -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,9) else 1)'
        if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
    }
}
if (-not $python) { throw 'Python 3.9+ is required. Set HERDR_PYTHON or install Python.' }
& $python $runner @args
exit $LASTEXITCODE