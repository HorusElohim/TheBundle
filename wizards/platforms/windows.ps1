[CmdletBinding()]
param(
    [string]$VenvPath = ".venv",
    [string]$PackageName = "thebundle[all]",
    [switch]$AdminStagesOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[wizard] $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[wizard] $Message" -ForegroundColor Green
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "[wizard] $Message" -ForegroundColor Yellow
}

function Confirm-Stage {
    param([string]$Stage)
    $reply = Read-Host "[wizard] Stage: $Stage. Continue? [y/N]"
    if ($reply -notin @("y", "Y", "yes", "YES")) {
        throw "Aborted at stage: $Stage"
    }
}

function Test-Command {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-HypervisorLaunchAuto {
    try {
        $bcd = (bcdedit /enum 2>$null) -join "`n"
        if ($bcd -match "hypervisorlaunchtype\s+(\w+)") {
            $hlt = $Matches[1]
            Write-Step "hypervisorlaunchtype = $hlt"
            if ($hlt -ieq "Off") {
                Write-WarnMsg "Setting hypervisorlaunchtype to auto..."
                bcdedit /set hypervisorlaunchtype auto | Out-Null
                return $true
            }
        }
    } catch {
        Write-WarnMsg "Could not query/update hypervisorlaunchtype: $($_.Exception.Message)"
    }
    return $false
}

function Ensure-WSL2 {
    if (-not (Test-IsAdmin)) {
        throw "Run this script in an elevated PowerShell (Administrator) to configure WSL and Windows features."
    }

    Write-Step "Enabling WSL/VM/Hyper-V features..."
    $needsReboot = $false
    $features = @(
        "Microsoft-Windows-Subsystem-Linux",
        "VirtualMachinePlatform",
        "Microsoft-Hyper-V-All"
    )

    foreach ($feature in $features) {
        try {
            dism.exe /online /enable-feature /featurename:$feature /all /norestart | Out-Null
            Write-Ok "Feature ensured: $feature"
        } catch {
            Write-WarnMsg "Could not enable '$feature': $($_.Exception.Message)"
        }
    }

    if (Ensure-HypervisorLaunchAuto) {
        $needsReboot = $true
    }

    if (-not (Test-Command "wsl.exe")) {
        throw "wsl.exe not found. Update Windows and rerun."
    }

    try {
        Write-Step "Updating WSL..."
        wsl --update | Out-Null
    } catch {
        Write-WarnMsg "wsl --update failed: $($_.Exception.Message)"
    }

    try {
        Write-Step "Setting WSL default version to 2..."
        wsl --set-default-version 2 | Out-Null
    } catch {
        Write-WarnMsg "Could not set WSL default version to 2: $($_.Exception.Message)"
    }

    try {
        $distros = (wsl -l -q 2>$null)
        if ($distros -notmatch "^Ubuntu(\s|$)") {
            Write-Step "Installing Ubuntu distro for WSL..."
            wsl --install -d Ubuntu | Out-Null
            $needsReboot = $true
        } else {
            Write-Ok "Ubuntu distro already present."
        }
    } catch {
        Write-WarnMsg "Could not query/install Ubuntu distro: $($_.Exception.Message)"
    }

    return $needsReboot
}

function Start-ElevatedAdminStages {
    $argList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-VenvPath", "`"$VenvPath`"",
        "-PackageName", "`"$PackageName`"",
        "-AdminStagesOnly"
    )
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList | Out-Null
}

function Ensure-Git {
    if (Test-Command "git") {
        Write-Ok "Git already installed."
        return
    }

    if (-not (Test-Command "winget")) {
        throw "winget is required to install Git automatically on Windows."
    }

    Write-Step "Installing Git..."
    & winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements --silent
    if (-not (Test-Command "git")) {
        throw "Git installation finished but the command was not found. Restart your shell and run the wizard again."
    }
    Write-Ok "Git installed."
}

function Get-PythonCommand {
    if (Test-Command "python") { return "python" }
    if (Test-Command "py") { return "py -3" }
    return $null
}

function Ensure-Python {
    $pythonCmd = Get-PythonCommand
    if ($pythonCmd) {
        Write-Ok "Python already installed."
        return $pythonCmd
    }

    if (-not (Test-Command "winget")) {
        throw "winget is required to install Python automatically on Windows."
    }

    Write-Step "Installing Python..."
    & winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent
    $pythonCmd = Get-PythonCommand
    if (-not $pythonCmd) {
        throw "Python installation finished but the command was not found. Restart your shell and run the wizard again."
    }
    Write-Ok "Python installed."
    return $pythonCmd
}

function Ensure-DockerDesktop {
    if (Test-Command "docker") {
        Write-Ok "Docker CLI already installed."
        return
    }

    if (-not (Test-Command "winget")) {
        throw "winget is required to install Docker Desktop automatically on Windows."
    }

    Write-Step "Installing Docker Desktop..."
    & winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements --silent
    if (-not (Test-Command "docker")) {
        Write-WarnMsg "Docker CLI not found yet. Start Docker Desktop once to finish setup."
    } else {
        Write-Ok "Docker Desktop installed."
    }
}

function Ensure-NvidiaSupport {
    if (Test-Command "nvidia-smi") {
        Write-Ok "NVIDIA driver detected (nvidia-smi found)."
    } else {
        Write-WarnMsg "NVIDIA driver not detected. Install/update NVIDIA Windows drivers for WSL2 GPU support."
        return
    }

    if (Test-Command "docker") {
        Write-Step "After Docker Desktop is running, validate GPU containers with:"
        Write-Host "docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi"
    } else {
        Write-WarnMsg "Docker CLI not available yet; run GPU validation after Docker Desktop setup finishes."
    }
}

function New-OrReuseVenv {
    param(
        [string]$PythonCommand,
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-WarnMsg "Virtual environment already exists at '$Path'. Reusing it."
    } else {
        Write-Step "Creating virtual environment at '$Path'..."
        if ($PythonCommand -like "py *") {
            & py -3 -m venv $Path
        } else {
            & $PythonCommand -m venv $Path
        }
    }
    return (Join-Path $Path "Scripts\python.exe")
}

Write-Step "Starting TheBundle setup on Windows..."
$needsReboot = $false

if (-not $AdminStagesOnly) {
    Confirm-Stage "Install Git"
    Ensure-Git
    Confirm-Stage "Install Python"
    $pythonCommand = Ensure-Python
    Confirm-Stage "Install Docker Desktop"
    Ensure-DockerDesktop
    Confirm-Stage "Configure NVIDIA GPU support for Docker"
    Ensure-NvidiaSupport
    Confirm-Stage "Create virtual environment at $VenvPath"
    $venvPython = New-OrReuseVenv -PythonCommand $pythonCommand -Path $VenvPath

    if (-not (Test-Path $venvPython)) {
        throw "Could not find venv python executable at '$venvPython'."
    }

    Confirm-Stage "Upgrade pip/setuptools/wheel"
    Write-Step "Upgrading pip/setuptools/wheel..."
    & $venvPython -m pip install --upgrade pip setuptools wheel

    Confirm-Stage "Install package $PackageName"
    Write-Step "Installing package '$PackageName'..."
    & $venvPython -m pip install $PackageName

    Confirm-Stage "Configure WSL2 + Hyper-V (requires Administrator)"
    if (Test-IsAdmin) {
        if (Ensure-WSL2) {
            $needsReboot = $true
        }
    } else {
        $elevateReply = Read-Host "[wizard] Administrator privileges are required for WSL2/Hyper-V. Relaunch elevated now? [y/N]"
        if ($elevateReply -in @("y", "Y", "yes", "YES")) {
            Start-ElevatedAdminStages
            Write-Ok "Launched elevated admin stage window."
        } else {
            Write-WarnMsg "Skipping admin stages. Re-run as Administrator to complete WSL2/Hyper-V setup."
        }
    }
} else {
    if (-not (Test-IsAdmin)) {
        throw "Admin stages require elevated PowerShell."
    }
    Confirm-Stage "Configure WSL2 + Hyper-V"
    if (Ensure-WSL2) {
        $needsReboot = $true
    }
    Write-Ok "Admin stages completed."
}

Write-Ok "Setup completed."
Write-Host ""
Write-Host "Activate with: $VenvPath\Scripts\Activate.ps1"
Write-Host "Then run: python -m pip show thebundle"
if ($needsReboot) {
    Write-WarnMsg "A reboot is recommended to complete WSL/Hyper-V setup."
}
