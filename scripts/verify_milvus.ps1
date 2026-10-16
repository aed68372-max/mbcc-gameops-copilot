param([string]$BaseUrl='http://127.0.0.1:18081')
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$out=Join-Path $project 'evidence\v2\stage-b'
New-Item -ItemType Directory -Force $out | Out-Null
if(!(Get-Command docker -ErrorAction SilentlyContinue)) {
    @{status='BLOCKED';reason='Docker engine/command unavailable; Windows prerequisite installation remains incomplete until reboot and service verification; no Milvus write/restart proof';checked_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $out 'milvus-persistence.json') -Encoding utf8
    Write-Output 'BLOCKED: Docker unavailable; memory vector tests do not count as Milvus evidence.'
    exit 2
}
$before=Invoke-RestMethod "$BaseUrl/api/v2/health"
if($before.knowledge.store -ne 'MILVUS'){throw 'Application must explicitly use Milvus; refusing memory fallback'}
$collection=$before.knowledge.collection
$payload=@{collectionName=$collection}|ConvertTo-Json
$statsBefore=Invoke-RestMethod 'http://127.0.0.1:19530/v2/vectordb/collections/get_stats' -Method Post -ContentType 'application/json' -Body $payload
$q=[Text.Encoding]::UTF8.GetBytes('{"question":"加洛法诺属于什么组织？","character":"加洛法诺"}')
$queryBefore=Invoke-RestMethod "$BaseUrl/api/knowledge/search" -Method Post -ContentType 'application/json; charset=utf-8' -Body $q
& docker compose -p mbcc -f (Join-Path $project 'deploy\compose.milvus.yml') restart standalone
if($LASTEXITCODE -ne 0){throw 'Milvus restart failed'}
for($i=0;$i -lt 30;$i++) {
    try {Invoke-RestMethod http://127.0.0.1:9091/healthz -TimeoutSec 2 | Out-Null;break}catch{Start-Sleep -Seconds 2}
}
$statsAfter=Invoke-RestMethod 'http://127.0.0.1:19530/v2/vectordb/collections/get_stats' -Method Post -ContentType 'application/json' -Body $payload
$queryAfter=Invoke-RestMethod "$BaseUrl/api/knowledge/search" -Method Post -ContentType 'application/json; charset=utf-8' -Body $q
$expected=$before.knowledge.chunks
$verified=($statsBefore.data.rowCount -eq $expected -and $statsAfter.data.rowCount -eq $expected -and $queryBefore[0].source.source_id -eq $queryAfter[0].source.source_id)
@{status=$(if($verified){'VERIFIED'}else{'PARTIAL'});collection=$collection;expected_chunks=$expected;stats_before=$statsBefore;stats_after=$statsAfter;query_before=$queryBefore;query_after=$queryAfter} | ConvertTo-Json -Depth 15 | Set-Content (Join-Path $out 'milvus-persistence.json') -Encoding utf8
if(!$verified){throw 'Persistence acceptance failed'}
