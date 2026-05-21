param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardArgs
)

$ErrorActionPreference = "Stop"

function Test-HasArgument {
    param(
        [string[]]$ArgsList,
        [string]$Name
    )
    foreach ($item in $ArgsList) {
        if ($item -eq $Name -or $item.StartsWith("$Name=")) {
            return $true
        }
    }
    return $false
}

function Get-ArgumentValue {
    param(
        [string[]]$ArgsList,
        [string]$Name
    )
    for ($i = 0; $i -lt $ArgsList.Count; $i++) {
        $item = $ArgsList[$i]
        if ($item -eq $Name) {
            if ($i + 1 -ge $ArgsList.Count) {
                throw "Missing value for $Name"
            }
            return $ArgsList[$i + 1]
        }
        if ($item.StartsWith("$Name=")) {
            return $item.Substring($Name.Length + 1)
        }
    }
    return $null
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory = $true)][string]$Id
    )
    & winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
}

function Ensure-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required to bootstrap missing tools on Windows."
    }
}

function Ensure-Git {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        return
    }
    Ensure-Winget
    Install-WingetPackage -Id "Git.Git"
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git installation completed, but git is still not on PATH."
    }
}

function Resolve-PythonExecutable {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return (Get-Command python).Source
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $resolved = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if (-not $resolved) {
            $resolved = & py -3 -c "import sys; print(sys.executable)"
        }
        if ($resolved) {
            return $resolved.Trim()
        }
    }
    return $null
}

function Ensure-Python {
    $resolved = Resolve-PythonExecutable
    if ($resolved) {
        return $resolved
    }
    Ensure-Winget
    Install-WingetPackage -Id "Python.Python.3.11"
    $resolved = Resolve-PythonExecutable
    if (-not $resolved) {
        throw "Python 3.11 installation completed, but no python executable could be resolved."
    }
    return $resolved
}

function Ensure-Node {
    if (Get-Command node -ErrorAction SilentlyContinue) {
        return
    }
    Ensure-Winget
    Install-WingetPackage -Id "OpenJS.NodeJS.LTS"
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        throw "Node installation completed, but node is still not on PATH."
    }
}

$explicitPython = Get-ArgumentValue -ArgsList $ForwardArgs -Name "--python"
$withWebsite = Test-HasArgument -ArgsList $ForwardArgs -Name "--with-website"

Ensure-Git
if ($withWebsite) {
    Ensure-Node
}

$pythonExecutable = if ($explicitPython) { (Resolve-Path $explicitPython).Path } else { Ensure-Python }

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$orchestrator = Join-Path $scriptRoot "package_chattodo.py"

$invokeArgs = New-Object System.Collections.Generic.List[string]
foreach ($item in $ForwardArgs) {
    $invokeArgs.Add($item)
}
if (-not $explicitPython) {
    $invokeArgs.Add("--python")
    $invokeArgs.Add($pythonExecutable)
}

Write-Host "Using Python: $pythonExecutable"
& $pythonExecutable $orchestrator @invokeArgs
