<#
.SYNOPSIS
    Wife God - Windows Installation Script
.DESCRIPTION
    Automated installation script for Wife God eMitra + Twitter Automation Agent on Windows.
    Installs system dependencies, Python, Ollama, and sets up the environment.
.NOTES
    Author: Wife God Team
    Version: 1.0.0
    Requires: Administrator privileges
#>

param(
    [string]$InstallPath = "$env:USERPROFILE\WifeGod",
    [string]$PythonVersion = "3.11",
    [string]$OllamaModel = "llama3:8b",
    [switch]$InstallOllama,
    [switch]$InstallPlaywright,
    [switch]$CreateShortcut,
    [switch]$AutoStart,
    [switch]$Silent
)

# ============================================
# Configuration
# ============================================
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\.."

# Colors for output
$Colors = @{
    Info    = 'Cyan'
    Success = 'Green'
    Warning = 'Yellow'
    Error   = 'Red'
    Header  = 'Magenta'
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'Info'
    )
    $color = $Colors[$Level]
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Message" -ForegroundColor $color
}

function Check-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Check-Command {
    param([string]$Command)
    return (Get-Command $Command -ErrorAction SilentlyContinue) -ne $null
}

function Install-Chocolatey {
    if (-not (Check-Command "choco")) {
        Write-Log "Installing Chocolatey..." 'Info'
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        refreshenv
    } else {
        Write-Log "Chocolatey already installed" 'Success'
    }
}

function Install-SystemDependencies {
    Write-Log "Installing system dependencies..." 'Header'

    if ($InstallOllama) {
        Install-Ollama
    }

    # Install via Chocolatey
    $packages = @(
        "tesseract",
        "googlechrome",
        "git",
        "vcredist140",
        "portaudio"
    )

    foreach ($pkg in $packages) {
        Write-Log "Installing $pkg..." 'Info'
        choco install -y $pkg --no-progress
    }
}

function Install-Ollama {
    Write-Log "Installing Ollama..." 'Info'

    if (Check-Command "ollama") {
        Write-Log "Ollama already installed" 'Success'
        return
    }

    $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
    $installerPath = "$env:TEMP\OllamaSetup.exe"

    try {
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $installerPath
        Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait
        Remove-Item $installerPath -Force
        Write-Log "Ollama installed successfully" 'Success'
    } catch {
        Write-Log "Failed to install Ollama: $_" 'Error'
        throw
    }
}

function Install-Python {
    Write-Log "Checking Python installation..." 'Header'

    if (Check-Command "python") {
        $version = python --version 2>&1
        Write-Log "Python found: $version" 'Success'
        return
    }

    Write-Log "Installing Python $PythonVersion..." 'Info'
    choco install -y python --version=$PythonVersion --no-progress
    refreshenv
}

function Create-VirtualEnvironment {
    Write-Log "Creating virtual environment..." 'Header'

    $venvPath = Join-Path $InstallPath "venv"

    if (Test-Path $venvPath) {
        Write-Log "Virtual environment already exists at $venvPath" 'Success'
        return
    }

    python -m venv $venvPath
    Write-Log "Virtual environment created at $venvPath" 'Success'
}

function Install-PythonDependencies {
    Write-Log "Installing Python dependencies..." 'Header'

    $venvPath = Join-Path $InstallPath "venv"
    $pipPath = Join-Path $venvPath "Scripts\pip.exe"
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"
    $reqFile = Join-Path $ProjectRoot "requirements.txt"

    if (-not (Test-Path $reqFile)) {
        Write-Log "Requirements file not found: $reqFile" 'Error'
        throw "Requirements file not found"
    }

    # Upgrade pip
    & $pipPath install --upgrade pip setuptools wheel

    # Install dependencies
    & $pipPath install -r $reqFile

    # Install Playwright if requested
    if ($InstallPlaywright) {
        Write-Log "Installing Playwright..." 'Info'
        & $pipPath install playwright
        & $pythonPath -m playwright install chromium
    }
}

function Setup-Configuration {
    Write-Log "Setting up configuration..." 'Header'

    $configFile = Join-Path $InstallPath "config.json"
    $exampleConfig = Join-Path $ProjectRoot "config.json.example"

    if (-not (Test-Path $configFile)) {
        if (Test-Path $exampleConfig) {
            Copy-Item $exampleConfig $configFile
            Write-Log "Created config.json from template" 'Success'
        } else {
            # Create default config
            $defaultConfig = @{
                app = @{
                    input_folder = "./input_documents"
                    output_folder = "./output"
                    temp_folder = "./temp"
                    log_level = "INFO"
                }
                ollama = @{
                    url = "http://localhost:11434"
                    model = "llama3:8b"
                    timeout = 120
                    temperature = 0.1
                    max_tokens = 4096
                }
                voice = @{
                    tts_engine = "pyttsx3"
                    tts_rate = 150
                    tts_volume = 0.9
                    tts_voice = "hindi"
                    stt_engine = "whisper"
                    whisper_model = "base"
                    language = "hi"
                    vad_threshold = 0.5
                    sample_rate = 16000
                }
                emitra = @{
                    sso_url = "https://sso.rajasthan.gov.in"
                    portal_url = "https://emitra.rajasthan.gov.in"
                    username = ""
                    password = ""
                    headless = $false
                    browser = "chromium"
                    viewport = @{width = 1920; height = 1080}
                    timeout = 30000
                }
                twitter = @{
                    username = ""
                    password = ""
                    headless = $false
                    browser = "chromium"
                    viewport = @{width = 1920; height = 1080}
                    timeout = 30000
                }
            }
            $defaultConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath $configFile -Encoding UTF8
            Write-Log "Created default config.json" 'Success'
        }
    } else {
        Write-Log "config.json already exists" 'Info'
    }
}

function Create-Directories {
    Write-Log "Creating directories..." 'Header'

    $dirs = @(
        "data",
        "input_documents",
        "output",
        "temp",
        "models",
        "logs",
        "data_products",
        "screenshots\templates"
    )

    foreach ($dir in $dirs) {
        $fullPath = Join-Path $InstallPath $dir
        if (-not (Test-Path $fullPath)) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Log "Created directory: $fullPath" 'Info'
        }
    }
}

function Pull-OllamaModel {
    Write-Log "Pulling Ollama model: $OllamaModel..." 'Header'

    try {
        ollama pull $OllamaModel
        Write-Log "Model $OllamaModel pulled successfully" 'Success'
    } catch {
        Write-Log "Warning: Failed to pull Ollama model. Run 'ollama pull $OllamaModel' manually." 'Warning'
    }
}

function Install-PlaywrightBrowsers {
    if ($InstallPlaywright) {
        Write-Log "Installing Playwright browsers..." 'Header'
        $venvPath = Join-Path $InstallPath "venv"
        $pythonPath = Join-Path $venvPath "Scripts\python.exe"
        & $pythonPath -m playwright install chromium
    }
}

function Create-Shortcuts {
    if ($CreateShortcut) {
        Write-Log "Creating shortcuts..." 'Header'

        $shell = New-Object -ComObject WScript.Shell
        $desktop = [Environment]::GetFolderPath("Desktop")

        # Main shortcut
        $shortcut = $shell.CreateShortcut("$desktop\Wife God.lnk")
        $shortcut.TargetPath = Join-Path $InstallPath "venv\Scripts\python.exe"
        $shortcut.Arguments = "-m main --interactive"
        $shortcut.WorkingDirectory = $InstallPath
        $shortcut.Description = "Wife God - Sovereign Local AI Agent"
        $shortcut.IconLocation = Join-Path $InstallPath "assets\wife_god.ico"
        $shortcut.Save()

        # Daemon shortcut
        $shortcutDaemon = $shell.CreateShortcut("$desktop\Wife God (Daemon).lnk")
        $shortcutDaemon.TargetPath = Join-Path $InstallPath "venv\Scripts\python.exe"
        $shortcutDaemon.Arguments = "-m main --daemon"
        $shortcutDaemon.WorkingDirectory = $InstallPath
        $shortcutDaemon.Description = "Wife God - Daemon Mode"
        $shortcutDaemon.Save()

        Write-Log "Desktop shortcuts created" 'Success'
    }
}

function Setup-AutoStart {
    if ($AutoStart) {
        Write-Log "Setting up auto-start..." 'Header'

        $venvPath = Join-Path $InstallPath "venv"
        $pythonPath = Join-Path $venvPath "Scripts\python.exe"

        $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        Set-ItemProperty -Path $regPath -Name "WifeGod" -Value "`"$pythonPath`" -m main --daemon" -Force

        Write-Log "Auto-start configured" 'Success'
    }
}

function Create-Uninstaller {
    Write-Log "Creating uninstaller..." 'Header'

    $uninstallScript = @"
#requires -RunAsAdministrator
<#
.SYNOPSIS
    Uninstall Wife God
#>

`$installPath = "$InstallPath"

Write-Host "Uninstalling Wife God..." -ForegroundColor Cyan

# Remove auto-start
`$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
if (Test-Path `$regPath) {
    Remove-ItemProperty -Path `$regPath -Name "WifeGod" -ErrorAction SilentlyContinue
}

# Remove shortcuts
`$desktop = [Environment]::GetFolderPath("Desktop")
`$shortcuts = @("Wife God.lnk", "Wife God (Daemon).lnk")
foreach (`$shortcut in `$shortcuts) {
    `$path = Join-Path `$desktop `$shortcut
    if (Test-Path `$path) {
        Remove-Item `$path -Force
    }
}

# Remove installation directory
if (Test-Path "`$installPath") {
    Remove-Item -Path `$installPath -Recurse -Force
    Write-Host "Wife God uninstalled successfully" -ForegroundColor Green
} else {
    Write-Host "Installation not found" -ForegroundColor Yellow
}
"@

    $uninstallPath = Join-Path $InstallPath "uninstall.ps1"
    $uninstallScript | Out-File -FilePath $uninstallPath -Encoding UTF8

    # Create batch wrapper for easy execution
    $batchContent = @"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"
pause
"@
    $batchPath = Join-Path $InstallPath "uninstall.bat"
    $batchContent | Out-File -FilePath $batchPath -Encoding UTF8

    Write-Log "Uninstaller created" 'Success'
}

function Verify-Installation {
    Write-Log "Verifying installation..." 'Header'

    $venvPath = Join-Path $InstallPath "venv"
    $pythonPath = Join-Path $venvPath "Scripts\python.exe"

    $checks = @(
        @{ Name = "Virtual Environment"; Test = { Test-Path $venvPath } },
        @{ Name = "Python Executable"; Test = { Test-Path $pythonPath } },
        @{ Name = "Config File"; Test = { Test-Path (Join-Path $InstallPath "config.json") } },
        @{ Name = "Directories"; Test = {
            (Test-Path (Join-Path $InstallPath "data")) -and
            (Test-Path (Join-Path $InstallPath "input_documents")) -and
            (Test-Path (Join-Path $InstallPath "output")) -and
            (Test-Path (Join-Path $InstallPath "temp"))
        }},
        @{ Name = "Python Imports"; Test = {
            & `$pythonPath -c "import easyocr, playwright, ollama, cv2, numpy, pandas, PIL, whisper, pyttsx3; print('OK')" 2>$null
        }}
    )

    $allPassed = $true
    foreach ($check in $checks) {
        try {
            $result = & $check.Test
            if ($result) {
                Write-Log "[PASS] $($check.Name)" 'Success'
            } else {
                Write-Log "[FAIL] $($check.Name)" 'Error'
                $allPassed = $false
            }
        } catch {
            Write-Log "[FAIL] $($check.Name) - $_" 'Error'
            $allPassed = $false
        }
    }

    if ($allPassed) {
        Write-Log "All verification checks passed!" 'Success'
    } else {
        Write-Log "Some verification checks failed" 'Warning'
    }

    return $allPassed
}

# ============================================
# Main Installation Flow
# ============================================
function Main {
    Write-Log "=" * 60 'Header'
    Write-Log "Wife God - Windows Installation" 'Header'
    Write-Log "=" * 60 'Header'

    # Check admin rights
    if (-not (Check-Admin)) {
        Write-Log "This script requires Administrator privileges!" 'Error'
        Write-Log "Please run PowerShell as Administrator" 'Error'
        exit 1
    }

    # Check if already installed
    if (Test-Path $InstallPath) {
        Write-Log "Wife God already installed at $InstallPath" 'Warning'
        if (-not $Silent) {
            $response = Read-Host "Reinstall? (y/N)"
            if ($response -notmatch '^[yY]') {
                Write-Log "Installation cancelled" 'Info'
                exit 0
            }
        }
    }

    try {
        # Run installation steps
        Install-Chocolatey
        Install-SystemDependencies
        Install-Python
        Create-VirtualEnvironment
        Install-PythonDependencies
        if ($InstallPlaywright) { Install-PlaywrightBrowsers }
        Pull-OllamaModel
        Create-Directories
        Setup-Configuration
        Create-Shortcuts
        Setup-AutoStart
        Create-Uninstaller

        # Verify
        $verified = Verify-Installation

        Write-Log "=" * 60 'Header'
        if ($verified) {
            Write-Log "INSTALLATION SUCCESSFUL!" 'Success'
        } else {
            Write-Log "INSTALLATION COMPLETED WITH WARNINGS" 'Warning'
        }
        Write-Log "=" * 60 'Header'

        Write-Log ""
        Write-Log "Installation path: $InstallPath" 'Info'
        Write-Log ""
        Write-Log "Next steps:" 'Header'
        Write-Log "1. Edit config.json with your credentials:" 'Info'
        Write-Log "   notepad $InstallPath\config.json" 'Info'
        Write-Log "2. Start Ollama service:" 'Info'
        Write-Log "   ollama serve" 'Info'
        Write-Log "3. Run Wife God:" 'Info'
        Write-Log "   cd $InstallPath" 'Info'
        Write-Log("   .\venv\Scripts\python.exe -m main --interactive") 'Info'
        Write-Log ""
        Write-Log "Or use desktop shortcut: 'Wife God'" 'Info'

    } catch {
        Write-Log "INSTALLATION FAILED: $_" 'Error'
        exit 1
    }
}

# Run main
Main