# Set up QuikLight auto-start for the signed-in Windows user.
# No admin rights, services, scheduled tasks or elevated permissions required.
param(
    [ValidateSet("Install", "Remove", "Status")]
    [string]$Mode = "Install"
)
$ErrorActionPreference = "Stop"
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$name = "QuikLight"
$gui = Join-Path (Split-Path -Parent $PSScriptRoot) "gui\quiklight_windows.pyw"

if ($Mode -eq "Remove") {
    Remove-ItemProperty -Path $runKey -Name $name -ErrorAction SilentlyContinue
    Write-Host "Inicialização automática desativada."
    exit 0
}

if ($Mode -eq "Status") {
    $entry = (Get-ItemProperty -Path $runKey -Name $name -ErrorAction SilentlyContinue).$name
    if ($entry) { Write-Host "Inicialização automática ativa: $entry" }
    else { Write-Host "Inicialização automática desativada." }
    exit 0
}

if (-not (Test-Path -LiteralPath $gui)) { throw "Interface Windows não encontrada: $gui" }
$pythonw = Get-Command "pythonw.exe" -ErrorAction Stop
$pythonwPath = $pythonw.Source
if (-not (Test-Path -LiteralPath $pythonwPath)) { throw "pythonw.exe não encontrado: $pythonwPath" }

# --tray starts the USB backend if needed, while the GUI remains hidden.
$value = ('"{0}" "{1}" --tray' -f $pythonwPath, $gui)
New-Item -Path $runKey -Force | Out-Null
New-ItemProperty -Path $runKey -Name $name -Value $value -PropertyType String -Force | Out-Null
Write-Host "QuikLight configurado para iniciar minimizado na bandeja ao entrar no Windows."
Write-Host "Comando registrado: $value"
Write-Host "Para desfazer: .\windows\setup-startup.ps1 -Mode Remove"
