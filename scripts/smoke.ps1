param([string]$BaseUrl = 'http://127.0.0.1:18081')
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$results = [ordered]@{captured_at=(Get-Date).ToString('o'); health=(Invoke-RestMethod "$BaseUrl/api/health")}
$cases = @(
    @{name='search_character'; path='search'; body=@{question='赫卡蒂生日收到谁的明信片？'; character='赫卡蒂'}},
    @{name='rag_character'; path='ask'; body=@{question='赫卡蒂生日收到谁的明信片？'; character='赫卡蒂'}},
    @{name='unknown_character'; path='ask'; body=@{question='她的技能伤害是多少？'; character='未收录角色'}},
    @{name='unknown_version'; path='ask'; body=@{question='海拉稀有度？'; character='海拉';version='未收录版本'}},
    @{name='unrelated_question'; path='ask'; body=@{question='太阳的质量是多少公斤？'}},
    @{name='agent_metrics'; path='agent'; body=@{question='调用 getSyntheticOperationsMetrics 工具，报告模拟付费率。'}}
)
foreach ($case in $cases) {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($case.body | ConvertTo-Json))
    try {
        $response = Invoke-RestMethod "$BaseUrl/api/$($case.path)" -Method Post -ContentType 'application/json; charset=utf-8' -Body $bytes -TimeoutSec 180 -StatusCodeVariable httpStatus
        $results[$case.name] = @{http_status=$httpStatus; response=$response}
    }
    catch { $results[$case.name] = @{error=$_.Exception.Message} }
}
try {
    Invoke-RestMethod "$BaseUrl/api/ask" -Method Post -ContentType 'application/json' -Body '{"question":" "}' | Out-Null
    $results['blank_input'] = @{unexpected='accepted'}
} catch { $results['blank_input'] = @{http_status=[int]$_.Exception.Response.StatusCode} }
$results | ConvertTo-Json -Depth 15 | Set-Content (Join-Path $project 'evidence\http-smoke.json') -Encoding utf8
$results | ConvertTo-Json -Depth 15
