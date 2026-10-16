# User-authorized system prerequisites only. Never restarts Windows or touches game/project databases.
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$out=Join-Path $project 'evidence\v2\stage-g'
$result=[ordered]@{started_at=(Get-Date).ToString('o');automatic_reboot=$false;status='PARTIAL'}
try {
    $admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if(!$admin){throw 'Administrator elevation required'}
    & dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart *> (Join-Path $out 'virtual-machine-platform.log')
    $result['virtual_machine_platform_exit']=$LASTEXITCODE
    & dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart *> (Join-Path $out 'windows-wsl-feature.log')
    $result['wsl_feature_exit']=$LASTEXITCODE
    & winget install --id Microsoft.WSL --version 2.7.13 --exact --source winget --silent --accept-package-agreements --accept-source-agreements --disable-interactivity *> (Join-Path $out 'wsl-admin-install.log')
    $result['wsl_install_exit']=$LASTEXITCODE
    & winget install --id Docker.DockerDesktop --version 4.95.0 --exact --source winget --silent --accept-package-agreements --accept-source-agreements --disable-interactivity *> (Join-Path $out 'docker-admin-install.log')
    $result['docker_install_exit']=$LASTEXITCODE
    $result['status']='PARTIAL_VERIFY_ACTUAL_SERVICES_AND_REBOOT_REQUIREMENT'
} catch {$result['status']='BLOCKED';$result['error']=$_.Exception.Message}
$result['finished_at']=(Get-Date).ToString('o')
$result | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'admin-install-result.json') -Encoding utf8
