param([switch]$Real, [string]$JavaHome = $env:JAVA_HOME, [string]$MavenHome = $env:MAVEN_HOME)
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$taskRoot = [IO.Path]::GetFullPath((Join-Path $project '..\..'))
if (!$JavaHome) { $JavaHome = (Get-ChildItem (Join-Path $taskRoot 'work\runtime') -Directory -Filter 'jdk-17*' | Select-Object -First 1).FullName }
if (!$MavenHome) { $MavenHome = Join-Path $taskRoot 'work\runtime\apache-maven-3.9.9' }
if (!(Test-Path (Join-Path $JavaHome 'bin\java.exe'))) { throw 'Set JAVA_HOME to a Java 17/21 JDK.' }
$env:JAVA_HOME = $JavaHome
$env:MBCC_REAL_TESTS = if($Real) {'true'} else {'false'}
Push-Location $project
try {
    & (Join-Path $MavenHome 'bin\mvn.cmd') -B -f (Join-Path $project 'pom.xml') "-Dmaven.repo.local=$taskRoot\work\m2" package
    if ($LASTEXITCODE -ne 0) { throw 'Build/tests failed. Inspect test reports; real failures must not be labelled as Mock success.' }
} finally {Pop-Location}
