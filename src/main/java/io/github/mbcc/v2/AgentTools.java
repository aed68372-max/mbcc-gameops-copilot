package io.github.mbcc.v2;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import io.github.mbcc.KnowledgeIndex;
import java.time.*;
import java.util.*;
import java.util.function.Supplier;

public class AgentTools {
    public record ToolResult(String status, String sourceType, Object data, String error) {}
    public record Trace(String callId, String tool, Map<String,Object> arguments, String status,
                        double elapsedMs, ToolResult result) {}
    private final KnowledgeGateway knowledge;
    private final MetricsGateway metrics;
    private final String runId;
    private final List<Trace> traces = new ArrayList<>();
    private final Set<String> cited = new LinkedHashSet<>();
    private final Map<String,String> sourceUrls=new LinkedHashMap<>();
    public AgentTools(KnowledgeGateway knowledge, MetricsGateway metrics, String runId) {
        this.knowledge=knowledge; this.metrics=metrics; this.runId=runId;
    }
    public List<Trace> traces() { return List.copyOf(traces); }
    public Set<String> cited() { return Set.copyOf(cited); }
    public Map<String,String> sourceUrls() { return Map.copyOf(sourceUrls); }
    private Map<String,Object> args(Object... pairs) {
        Map<String,Object> result = new LinkedHashMap<>();
        for(int i=0;i<pairs.length;i+=2) result.put((String)pairs[i],pairs[i+1]);
        return result;
    }
    private ToolResult invoke(String name, Map<String,Object> arguments, String type, Supplier<Object> operation) {
        long began=System.nanoTime(); ToolResult result;
        try {
            if(traces.size()>=6) throw new IllegalArgumentException("maximum six actual tool executions per request");
            Object data=operation.get();
            String state=data instanceof List<?> l && l.isEmpty() ? "NO_EVIDENCE" : "OK";
            if(data instanceof Map<?,?> m && m.get("status") instanceof String s)state=s;
            if(state.equals("OK") && type.equals("SYNTHETIC_SQL") && data instanceof Map<?,?> m) {
                String sourceId=runId+":"+(traces.size()+1);
                Map<String,Object> withSource=new LinkedHashMap<>();
                m.forEach((k,v)->withSource.put(k.toString(),v));
                withSource.put("source_id",sourceId);withSource.put("source_type","SYNTHETIC_SQL");
                data=withSource;cited.add(sourceId);
            }
            result = new ToolResult(state,type,data,null);
        } catch(IllegalArgumentException e) {
            result=new ToolResult("INVALID_ARGUMENT",type,null,e.getMessage());
        } catch(RuntimeException e) {
            result=new ToolResult("UNAVAILABLE",type,null,"Dependency unavailable; do not invent data");
        }
        traces.add(new Trace(runId+":"+(traces.size()+1),name,arguments,result.status(),(System.nanoTime()-began)/1e6,result));
        return result;
    }
    private String checked(String s, int max, boolean required) {
        if(s==null || s.isBlank()) { if(required) throw new IllegalArgumentException("required nonblank argument"); return null; }
        if(s.length()>max) throw new IllegalArgumentException("argument too long");
        return s.trim();
    }
    private Object lookup(String query,String character,String version,String category) {
        var hits=knowledge.search(checked(query,500,true),checked(character,60,false),checked(version,80,false),category,5);
        hits.forEach(h -> {cited.add(h.source().source_id());sourceUrls.put(h.source().source_id(),h.source().source_url());});
        return hits;
    }
    @Tool("检索官方禁闭者背景、职业、技能事实，角色问答或角色比较时使用。没有证据必须说明未收录。")
    public ToolResult searchCharacterKnowledge(@P("完整角色名；比较两人时分别查询") String character,
              @P("要查询的具体事实，例如背景或技能") String query,
              @P(value="精确公告版本标签；不限制时省略",required=false) String version) {
        return invoke("searchCharacterKnowledge",args("character",character,"query",query,"version",version),"OFFICIAL_KNOWLEDGE",
                ()->lookup(query,checked(character,60,true),version,"character"));
    }
    @Tool("检索游戏机制，例如追踪保底、战斗、养成或极域重构的公开规则。")
    public ToolResult searchGameMechanics(@P("具体玩法及问题") String query,
              @P(value="精确公告版本；不限制时省略",required=false) String version) {
        return invoke("searchGameMechanics",args("query",query,"version",version),"OFFICIAL_KNOWLEDGE",()->lookup(query,null,version,"gameplay"));
    }
    @Tool("检索公开历史活动或卡池规则及时间。历史公告不能推断当前开放状态。")
    public ToolResult getGameEventInfo(@P("活动或卡池名称") String eventName,
              @P("所需信息，例如规则或日期") String query) {
        return invoke("getGameEventInfo",args("eventName",eventName,"query",query),"OFFICIAL_KNOWLEDGE",
                ()->lookup(checked(eventName,100,true)+" "+checked(query,500,true),null,null,"gameplay"));
    }
    @Tool("查询独立只读SQL中的Synthetic教学数据。支持DAU、PAYMENT(付费率ARPU/ARPPU)、RETENTION_D1/D7、EVENT_REVENUE、EVENT_PARTICIPATION。日期范围闭区间；不是无期迷途真实运营数据。")
    public ToolResult queryGameMetrics(@P("允许的指标枚举") MetricsGateway.Metric metric,
              @P("开始日期 YYYY-MM-DD") String startDate, @P("结束日期 YYYY-MM-DD") String endDate,
              @P(value="活动ID；不限制时省略",required=false) String eventId,
              @P(value="平台；不限制时省略",required=false) String platform) {
        return invoke("queryGameMetrics",args("metric",metric,"startDate",startDate,"endDate",endDate,"eventId",eventId,"platform",platform),"SYNTHETIC_SQL",()-> {
            if(metric==null) throw new IllegalArgumentException("metric required");
            LocalDate start=LocalDate.parse(checked(startDate,10,true)), end=LocalDate.parse(checked(endDate,10,true));
            if(end.isBefore(start) || java.time.temporal.ChronoUnit.DAYS.between(start,end)>366) throw new IllegalArgumentException("invalid date window");
            return metrics.query(metric,start.toString(),end.toString(),checked(eventId,60,false),checked(platform,30,false));
        });
    }
}
