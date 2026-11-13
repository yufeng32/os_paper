# Runs the pattern-level reproducer for the Kubernetes ListAndWatch resync
# goroutine leak (fix commit 991674380b7773d73afaeafeac6242bf3b6e6001).
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File experiments/blocking/feasibility/reproducer/run.ps1
#
# It builds once, then runs the buggy mode 3 times and the fixed mode 3 times
# (the course requires at least 3 independent runs), and writes each run into
# logs/run_<mode>_<n>.txt.

$ErrorActionPreference = "Stop"

$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$feasDir = Split-Path -Parent $here
$logsDir = Join-Path $feasDir "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$exe     = Join-Path $here "repro.exe"

Push-Location $here
try {
    Write-Host "== go version =="
    go version
    Write-Host ""
    Write-Host "== go build =="
    & go build -o $exe .
    if ($LASTEXITCODE -ne 0) { throw "go build failed with exit code $LASTEXITCODE" }
    Write-Host "build ok"
    Write-Host ""

    foreach ($mode in @("buggy", "fixed")) {
        for ($i = 1; $i -le 3; $i++) {
            $log = Join-Path $logsDir ("run_{0}_{1}.txt" -f $mode, $i)
            Write-Host ("== running mode={0} repetition {1} ==" -f $mode, $i)
            & $exe ("-mode=" + $mode) "-calls=5" 2>&1 | Tee-Object -FilePath $log
            Write-Host ""
        }
    }
} finally {
    Pop-Location
}
