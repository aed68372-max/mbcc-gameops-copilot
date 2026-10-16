# Cancel only this task's initial installer, already proven to have failed prerequisite checks.
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$out=Join-Path $project 'evidence\v2\stage-g\failed-installer-close.json'
$expected='C:\Users\a\AppData\Local\Temp\DockerDesktopInstallers\1792135738314737800\Docker Desktop Installer.exe'
try {
    $process=Get-Process -Id 59808 -ErrorAction Stop
    if($process.Path -ne $expected){throw 'PID/path mismatch; refusing to stop process'}
    $log=Get-Content 'C:\ProgramData\DockerDesktop\install-log-admin.txt' -Raw
    if($log -notmatch 'Prerequisite failed' -or $log -notmatch '1792135738314737800'){throw 'Failure evidence mismatch'}
    $closed=$process.CloseMainWindow()
    Start-Sleep -Seconds 2
    if(Get-Process -Id 59808 -ErrorAction SilentlyContinue){Stop-Process -Id 59808 -Force}
    @{status='VERIFIED_CANCELLED_FAILED_INSTALLER';pid=59808;path=$expected;graceful_close_requested=$closed;other_installers_and_services_untouched=$true} | ConvertTo-Json | Set-Content $out -Encoding utf8
}catch{@{status='PARTIAL';error=$_.Exception.Message}|ConvertTo-Json|Set-Content $out -Encoding utf8}
