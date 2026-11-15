param(
    [ValidateSet('status', 'enable', 'disable')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$valueName = 'QuiklightWindows'

if ($Action -eq 'enable') {
    $pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
    $launcher = (Resolve-Path (Join-Path $PSScriptRoot '..\gui\quiklight_windows.pyw')).Path

    # Per-user startup: runs when the Windows user signs in.
    # Does NOT run before sign-in or capture the secure login screen.
    $command = '"' + $pythonw + '" "' + $launcher + '" --tray'
    New-Item -Path $runKey -Force | Out-Null
    New-ItemProperty -Path $runKey -Name $valueName -Value $command -PropertyType String -Force | Out-Null
}

if ($Action -eq 'disable') {
    Remove-ItemProperty -Path $runKey -Name $valueName -ErrorAction SilentlyContinue
}

$entry = (Get-ItemProperty -Path $runKey -Name $valueName -ErrorAction SilentlyContinue).$valueName

if ([string]::IsNullOrWhiteSpace($entry)) {
    Write-Output 'Inicializacao automatica apos login: desativada.'
} else {
    Write-Output 'Inicializacao automatica apos login: ativada.'
    Write-Output "Comando: $entry"
}
