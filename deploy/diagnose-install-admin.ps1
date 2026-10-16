$ErrorActionPreference='Continue'
$project=Split-Path $PSScriptRoot -Parent
$result=[ordered]@{captured_at=(Get-Date).ToString('o')}
$result['processes']=Get-CimInstance Win32_Process -Filter "Name like '%Docker%Installer%' OR Name='wslinstaller.exe'" | Select-Object Name,ProcessId,ParentProcessId,CommandLine,ExecutablePath
$result['features']=@('VirtualMachinePlatform','Microsoft-Windows-Subsystem-Linux') | ForEach-Object { $f=Get-WindowsOptionalFeature -Online -FeatureName $_; @{feature=$_;state=$f.State.ToString()} }
$result['reboot_pending']=(Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
$result['docker_registration']=Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object DisplayName -like '*Docker*' | Select-Object DisplayName,InstallLocation,DisplayVersion
$result['log_files']=@('C:\ProgramData\DockerDesktop','C:\Users\a\AppData\Local\Docker') | ForEach-Object {Get-ChildItem $_ -File -Filter '*install*log*' -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime}
$result | ConvertTo-Json -Depth 7 | Set-Content (Join-Path $project 'evidence\v2\stage-g\admin-diagnostic.json') -Encoding utf8
