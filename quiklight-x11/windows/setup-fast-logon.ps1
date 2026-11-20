<#
QuikLight fast interactive logon startup.
prepare  - registers a per-user interactive logon task; keeps the existing Run key.
activate - checks the task, preserves the Run command, then migrates to the task.
rollback - restores the original Run command, then removes the fast logon task.
status   - read-only inspection.

The pre-logon static LED task is deliberately never changed.
Neither Quiklight binaries nor the USB controller are touched.
#>
param(
    [ValidateSet('status','prepare','activate','rollback')]
    [string] $Action = 'status'
)

$ErrorActionPreference = 'Stop'
$taskName = 'Quiklight - Login rapido'
$runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$runName = 'QuiklightWindows'
$backupKey = 'HKCU:\Software\Quiklight\FastLogonMigration'
$backupName = 'OriginalRunCommand'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$launcher = Join-Path $repo 'gui\quiklight_windows.pyw'
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name

function Get-Task {
    Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
}
function Get-RunEntry {
    (Get-ItemProperty -Path $runKey -Name $runName -ErrorAction SilentlyContinue).$runName
}
function Get-RunBackup {
    (Get-ItemProperty -Path $backupKey -Name $backupName -ErrorAction SilentlyContinue).$backupName
}
function Test-CurrentAccount([string]$identity) {
    # Windows Task Scheduler may store 'Anderson' instead of 'COMPUTER\\Anderson'.
    # A SID match is authoritative; accept the short name only when it matches
    # this interactive account and has no foreign domain qualifier.
    if ([string]::IsNullOrWhiteSpace($identity)) { return $false }
    $me = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $account = [Security.Principal.NTAccount]::new($identity)
        $actualSid = $account.Translate([Security.Principal.SecurityIdentifier]).Value
        if ($actualSid -eq $me.User.Value) { return $true }
    } catch {
        # Some Windows installations do not resolve unqualified stored names.
    }
    if ($identity -eq $me.Name) { return $true }
    $shortName = ($me.Name -split '\\')[-1]
    return ($identity -notmatch '[\\@]' -and $identity -eq $shortName)
}
function Assert-OurTask($task) {
    if (-not $task) { throw "Tarefa nao encontrada: $taskName" }
    if (-not (Test-CurrentAccount ([string]$task.Principal.UserId))) {
        throw "A tarefa pertence a outro usuario; nao alterarei: $($task.Principal.UserId)"
    }
    if ($task.Principal.LogonType -ne 'Interactive') {
        throw "A tarefa nao possui logon interativo; nenhuma alteracao."
    }
    $act = @($task.Actions)
    $expectedPythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
    $expectedArgs = '"' + $launcher + '" --tray'
    if ($act.Count -ne 1 -or $act[0].Execute -ne $expectedPythonw -or
        $act[0].Arguments -ne $expectedArgs) {
        throw 'Tarefa existente possui um executavel ou argumentos inesperados; nenhuma alteracao.'
    }
    $logonTriggers = @($task.Triggers | Where-Object {
        $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger'
    })
    if ($logonTriggers.Count -ne 1 -or @($task.Triggers).Count -ne 1) {
        throw 'Tarefa existente possui gatilhos inesperados; nenhuma alteracao.'
    }
}
function Status {
    $t = Get-Task
    $run = Get-RunEntry
    $backup = Get-RunBackup
    Write-Output '=== INICIALIZACAO RAPIDA ==='
    if ($t) {
        Write-Output "Tarefa: $($t.TaskName)"
        Write-Output "Estado: $($t.State)"
        Write-Output "Usuario: $($t.Principal.UserId)"
        Write-Output "Tipo: $($t.Principal.LogonType)"
        Write-Output "Executavel: $($t.Actions[0].Execute)"
        Write-Output "Argumentos: $($t.Actions[0].Arguments)"
        $info = Get-ScheduledTaskInfo -TaskName $taskName
        Write-Output "Ultima execucao: $($info.LastRunTime)"
        Write-Output "Ultimo resultado: $($info.LastTaskResult)"
    } else {
        Write-Output 'Tarefa: nao instalada'
    }
    Write-Output "Run antigo: $(if ($run) { 'presente' } else { 'ausente' })"
    Write-Output "Backup do Run: $(if ($backup) { 'presente' } else { 'ausente' })"
    Write-Output 'Tarefa SYSTEM de iluminacao no boot: nao modificada'
}

switch ($Action) {
    'prepare' {
        $existing = Get-Task
        if ($existing) {
            Assert-OurTask $existing
            Write-Output 'TAREFA JA PREPARADA. Validada sem criar duplicata; Run antigo preservado.'
            Status
            break
        }
        if (-not (Test-Path $launcher)) {
            throw "GUI nao encontrada: $launcher"
        }
        $pythonw = (Get-Command pythonw.exe -ErrorAction Stop).Source
        if (-not (Test-Path $pythonw)) {
            throw "pythonw.exe nao encontrado: $pythonw"
        }
        $args = '"' + $launcher + '" --tray'
        $taskAction = New-ScheduledTaskAction -Execute $pythonw -Argument $args -WorkingDirectory $repo
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
        $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
        Register-ScheduledTask -TaskName $taskName -Action $taskAction `
            -Trigger $trigger -Principal $principal -Settings $settings `
            -Description 'Quiklight GUI and Ambilight startup immediately after interactive user logon.' | Out-Null
        Assert-OurTask (Get-Task)
        Write-Output 'TAREFA PREPARADA. Run antigo preservado. Nao reinicie antes da migracao.'
        Status
    }
    'activate' {
        $t = Get-Task
        Assert-OurTask $t
        if ($t.State -eq 'Disabled') {
            Enable-ScheduledTask -TaskName $taskName | Out-Null
        }
        $run = Get-RunEntry
        if ($run) {
            $existingBackup = Get-RunBackup
            if ($existingBackup -and $existingBackup -ne $run) {
                throw 'Backup antigo diferente do Run atual; migracao cancelada.'
            }
            New-Item -Path $backupKey -Force | Out-Null
            New-ItemProperty -Path $backupKey -Name $backupName `
                -Value $run -PropertyType String -Force | Out-Null
            Remove-ItemProperty -Path $runKey -Name $runName -ErrorAction Stop
        }
        Write-Output 'MIGRACAO ATIVA: tarefa de login agora substitui HKCU Run.'
        Status
    }
    'rollback' {
        $t = Get-Task
        if ($t) { Assert-OurTask $t }
        $backup = Get-RunBackup
        if ($backup) {
            $existing = Get-RunEntry
            if ($existing -and $existing -ne $backup) {
                throw 'Run atual difere do backup. Nao vou sobrescreve-lo.'
            }
            New-Item -Path $runKey -Force | Out-Null
            New-ItemProperty -Path $runKey -Name $runName `
                -Value $backup -PropertyType String -Force | Out-Null
        }
        if ($t) { Unregister-ScheduledTask -TaskName $taskName -Confirm:$false }
        Write-Output 'ROLLBACK CONCLUIDO: tarefa removida e Run original restaurado, se havia backup.'
        Status
    }
    'status' { Status }
}
