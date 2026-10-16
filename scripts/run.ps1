param([string]$JavaHome = $env:JAVA_HOME, [switch]$EnableSql, [string]$Python = $env:MBCC_PYTHON, [ValidateSet('memory','milvus')][string]$VectorStore = 'memory')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
if (!$JavaHome) {
    $taskRoot = [IO.Path]::GetFullPath((Join-Path $project '..\..'))
    $JavaHome = (Get-ChildItem (Join-Path $taskRoot 'work\runtime') -Directory -Filter 'jdk-17*' | Select-Object -First 1).FullName
}
if (!(Test-Path (Join-Path $JavaHome 'bin\java.exe'))) { throw 'Set JAVA_HOME or -JavaHome to a Java 17/21 JDK.' }
$env:MBCC_VECTOR_STORE=$VectorStore
$env:MBCC_SQL_ENABLED=if($EnableSql){'true'}else{'false'}
if($EnableSql){
    if(!$Python){throw 'Supply -Python or MBCC_PYTHON with pyodbc installed; see docs/deployment.md.'}
    $env:MBCC_PYTHON=$Python
}
Push-Location $project
try {
    & (Join-Path $JavaHome 'bin\java.exe') '-Dfile.encoding=UTF-8' -jar (Join-Path $project 'target\mbcc-gameops-copilot-0.1.0.jar')
    if($LASTEXITCODE -ne 0){throw 'Application stopped with an error. Check the dependency health and logs.'}
} finally {Pop-Location}
