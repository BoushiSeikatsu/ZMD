Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-PythonCandidate {
    param(
        [string]$Command,
        [string[]]$PrefixArgs
    )

    try {
        & $Command @PrefixArgs --version *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Resolve-PythonCommand {
    $candidates = New-Object System.Collections.Generic.List[object]

    if ($env:CONDA_PREFIX) {
        $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path -LiteralPath $condaPython -PathType Leaf) {
            [void]$candidates.Add([pscustomobject]@{ Cmd = $condaPython; Prefix = @() })
        }
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        [void]$candidates.Add([pscustomobject]@{ Cmd = "py"; Prefix = @("-3") })
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        [void]$candidates.Add([pscustomobject]@{ Cmd = "python"; Prefix = @() })
    }

    foreach ($candidate in $candidates) {
        if (Test-PythonCandidate -Command $candidate.Cmd -PrefixArgs $candidate.Prefix) {
            return $candidate
        }
    }

    throw "Python executable not found or not runnable. Activate conda (e.g. 'conda activate base') or install Python launcher 'py'."
}

function Resolve-RepoRoot {
    param(
        [string]$ScriptPath
    )

    $candidates = @()

    $currentDir = (Get-Location).Path
    if ($currentDir) {
        $candidates += $currentDir
    }

    if ($ScriptPath) {
        $scriptDir = Split-Path -Parent $ScriptPath
        if ($scriptDir) {
            $repoFromScript = Split-Path -Parent $scriptDir
            if ($repoFromScript) {
                $candidates += $repoFromScript
            }
            $candidates += $scriptDir
        }
    }

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $cvikoPath = Join-Path $candidate "cviko5.py"
        $imgDir = Join-Path $candidate "cviko5_imgs"
        if ((Test-Path -LiteralPath $cvikoPath -PathType Leaf) -and (Test-Path -LiteralPath $imgDir -PathType Container)) {
            return $candidate
        }
    }

    throw "Could not locate ZMD root. Expected both 'cviko5.py' and 'cviko5_imgs' in the same directory. Run from ZMD or call this script from ZMD/cviko5_imgs."
}

try {
    $repoRoot = Resolve-RepoRoot -ScriptPath $PSCommandPath
    $cvikoScript = Join-Path $repoRoot "cviko5.py"
    $imgDir = Join-Path $repoRoot "cviko5_imgs"

    $leftImage = Join-Path $imgDir "teddy-im2.png"
    $rightImage = Join-Path $imgDir "teddy-im6.png"

    if (-not (Test-Path -LiteralPath $cvikoScript -PathType Leaf)) {
        throw "Missing script: $cvikoScript"
    }
    if (-not (Test-Path -LiteralPath $leftImage -PathType Leaf)) {
        throw "Missing input image: $leftImage"
    }
    if (-not (Test-Path -LiteralPath $rightImage -PathType Leaf)) {
        throw "Missing input image: $rightImage"
    }

    $pythonResolved = Resolve-PythonCommand
    $pythonCmd = $pythonResolved.Cmd
    $pythonPrefix = $pythonResolved.Prefix

    $metrics = @("SAD", "NCC", "CENSUS", "RANK")
    $windows = @(3, 5, 9)
    $maxDisp = 64

    $generated = New-Object System.Collections.Generic.List[string]

    foreach ($metric in $metrics) {
        foreach ($window in $windows) {
            $outputName = "teddy_disp_{0}_w{1}_md{2}.png" -f $metric, $window, $maxDisp
            $outputPath = Join-Path $imgDir $outputName

            & $pythonCmd @pythonPrefix $cvikoScript $leftImage $rightImage $maxDisp $metric $window $outputPath
            if ($LASTEXITCODE -ne 0) {
                throw "python cviko5.py failed for metric=$metric, window=$window, max_disp=$maxDisp"
            }

            if (-not (Test-Path -LiteralPath $outputPath -PathType Leaf)) {
                throw "Expected output file was not created: $outputPath"
            }

            [void]$generated.Add($outputName)
        }
    }

    Write-Host "Generated files:"
    foreach ($name in $generated) {
        Write-Host $name
    }

    if ($generated.Count -ne 12) {
        Write-Error "Expected 12 generated files, but got $($generated.Count)."
        exit 1
    }

    $fsGenerated = Get-ChildItem -LiteralPath $imgDir -Filter "teddy_disp_*_md64.png" -File
    if ($fsGenerated.Count -lt 12) {
        Write-Error "Expected at least 12 files matching teddy_disp_*_md64.png in $imgDir, but found $($fsGenerated.Count)."
        exit 1
    }

    Write-Host "Validation passed: generated 12 files."
    exit 0
}
catch {
    Write-Error "generate_teddy_12.ps1 failed: $($_.Exception.Message)"
    exit 1
}
