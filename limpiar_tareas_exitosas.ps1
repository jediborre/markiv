param(
    [switch]$Install,
    [switch]$Run
)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$logDirectory = Join-Path $projectRoot 'logs'
$logFile = Join-Path $logDirectory 'limpiar_tareas_exitosas.log'
$taskName = 'MarkIV Limpieza diaria'

if (-not (Test-Path -LiteralPath $logDirectory)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-CleanupLog([string]$Message) {
    $line = '{0:yyyy-MM-dd HH:mm:ss} {1}' -f (Get-Date), $Message
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
}

if (-not (Test-Administrator)) {
    throw 'Se requieren permisos de administrador para gestionar las tareas programadas de Mark IV.'
}

if ($Install) {
    $powerShellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $action = New-ScheduledTaskAction -Execute $powerShellPath -Argument (
        '-NoProfile -ExecutionPolicy Bypass -File "{0}" -Run' -f $PSCommandPath
    ) -WorkingDirectory $projectRoot
    $trigger = New-ScheduledTaskTrigger -Daily -At '00:00'
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

    Register-ScheduledTask `
        -TaskName $taskName `
        -Description 'Elimina tareas ODDS, Resultado y SEG de Mark IV terminadas correctamente; conserva las fallidas o pendientes.' `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force | Out-Null

    Write-CleanupLog "INSTALADA tarea diaria '$taskName' a las 00:00 bajo SYSTEM."
}
elseif (-not $Run) {
    throw 'Usa -Install para instalar la limpieza y ejecutarla ahora, o -Run desde el Programador de tareas.'
}

$now = Get-Date
$removed = 0
$preserved = 0
$taskScriptByName = @{
    'ODDS' = 'process_flashscore.py'
    'Resultado' = 'resultado_flashscore.py'
    'SEG' = 'seguimiento_flashscore.py'
}

foreach ($task in Get-ScheduledTask) {
    if ($task.TaskName -notmatch '^(ODDS|Resultado|SEG) \d{4} \d+$') {
        continue
    }

    $prefix = $task.TaskName.Split(' ')[0]
    $expectedScript = Join-Path $projectRoot $taskScriptByName[$prefix]
    $belongsToProject = @(
        $task.Actions | Where-Object {
            $_.Arguments -and
            $_.Arguments.IndexOf($expectedScript, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        }
    ).Count -gt 0

    if (-not $belongsToProject) {
        continue
    }

    try {
        $info = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath
        $hasRun = $info.LastRunTime -gt [datetime]'2000-01-01'
        $hasSuccessfulResult = $info.LastTaskResult -eq 0
        $hasFutureRun = $info.NextRunTime -gt $now
        $isRunning = $task.State -eq 'Running'

        if ($hasRun -and $hasSuccessfulResult -and -not $hasFutureRun -and -not $isRunning) {
            Unregister-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -Confirm:$false
            Write-CleanupLog "ELIMINADA $($task.TaskPath)$($task.TaskName): ejecución terminada correctamente."
            $removed++
        }
        else {
            $preserved++
            Write-CleanupLog "CONSERVADA $($task.TaskPath)$($task.TaskName): LastRun=$($info.LastRunTime); LastResult=$($info.LastTaskResult); NextRun=$($info.NextRunTime); State=$($task.State)."
        }
    }
    catch {
        $preserved++
        Write-CleanupLog "ERROR; se conserva $($task.TaskPath)$($task.TaskName): $($_.Exception.Message)"
    }
}

Write-CleanupLog "FIN: eliminadas=$removed; conservadas=$preserved."
Write-Output "Limpieza terminada. Eliminadas: $removed; conservadas: $preserved. Registro: $logFile"
