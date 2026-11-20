# Tests direct shutdown IPC without rebooting the computer.
# -Action status: no side effects.
# -Action blackout: turns the LEDs off and stops the running backend.
# Restart the backend using the Quiklight tray "Ligar" action afterwards.
param(
    [ValidateSet('status','blackout')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$reqName = 'Local\QuiklightShutdownRequestV1'
$ackName = 'Local\QuiklightShutdownAckV1'
$req = $null
$ack = $null

try {
    $req = [System.Threading.EventWaitHandle]::OpenExisting($reqName)
    $ack = [System.Threading.EventWaitHandle]::OpenExisting($ackName)
    Write-Output '=== QUIKLIGHT SHUTDOWN IPC ==='
    Write-Output "Conta: $([Security.Principal.WindowsIdentity]::GetCurrent().Name)"
    Write-Output 'Eventos encontrados: SIM'
    Write-Output 'Backend IPC: disponivel'
    if ($Action -eq 'blackout') {
        Write-Output 'Enviando pedido de desligamento ao backend atual...'
        if (-not $req.Set()) { throw 'Nao foi possivel sinalizar o pedido.' }
        $ok = $ack.WaitOne(3000)
        Write-Output "Backend confirmou USB blackout: $ok"
        if (-not $ok) { throw 'Timeout aguardando confirmacao de envio USB.' }
        Write-Output 'Teste concluido. Reinicie apenas o backend pelo menu Ligar da bandeja.'
    }
} finally {
    if ($req) { $req.Dispose() }
    if ($ack) { $ack.Dispose() }
}
