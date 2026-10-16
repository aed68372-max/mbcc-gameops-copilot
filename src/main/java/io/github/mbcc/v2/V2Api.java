package io.github.mbcc.v2;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import java.util.*;
import java.util.concurrent.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import jakarta.annotation.PreDestroy;

@RestController
public class V2Api {
    public record Probe(@NotBlank @Size(max=4000) String question,String model,String profile,List<SessionStore.Turn> history) {}
    public record Chat(@NotBlank @Size(max=4000) String question,@NotBlank String sessionId) {}
    public record Search(@NotBlank @Size(max=1000) String question,String character,String version,String category,@Min(1) @Max(10) Integer topK) {}
    public record MetricRequest(@NotNull MetricsGateway.Metric metric,@NotBlank String startDate,@NotBlank String endDate,String eventId,String platform) {}
    private final AgentEngine engine;
    private final KnowledgeGateway knowledge;
    private final MetricsGateway metrics;
    private final String model;
    private final SessionStore sessions;
    private final ObjectMapper json;
    private final ExecutorService pool=new ThreadPoolExecutor(2,2,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<>(4));
    public V2Api(AgentEngine engine,KnowledgeGateway knowledge,MetricsGateway metrics,SessionStore sessions,ObjectMapper json,@Value("${mbcc.chat-model}") String model) {
        this.engine=engine;this.knowledge=knowledge;this.metrics=metrics;this.model=model;
        this.sessions=sessions;this.json=json;
    }
    @PostMapping("/api/sessions") Object create() {return sessions.create();}
    @PostMapping("/api/chat") Object chat(@Valid @RequestBody Chat p,@RequestHeader("X-MBCC-Session-Token") String token) throws Exception {
        var history=sessions.history(p.sessionId(),token);
        java.util.concurrent.Future<AgentEngine.Run> task=pool.submit(()->engine.run(model,"tools",p.question(),history));
        try {var run=task.get(240,TimeUnit.SECONDS);sessions.append(p.sessionId(),token,p.question(),run);return run;}
        catch(TimeoutException e){task.cancel(true);return ResponseEntity.status(504).body(Map.of("status","TIMEOUT"));}
    }
    @PostMapping("/api/knowledge/search") Object search(@Valid @RequestBody Search p) {
        return knowledge.search(p.question(),p.character(),p.version(),p.category(),p.topK()==null?5:p.topK());
    }
    @GetMapping("/api/characters") Object characters() {return knowledge.sources().stream().map(io.github.mbcc.Knowledge::character_name).filter(s->s!=null&&!s.isBlank()).distinct().sorted().toList();}
    @GetMapping("/api/events") Object events() throws Exception {
        Object synthetic=Files.exists(Path.of("data/synthetic/manifest.json"))?json.readTree(Files.readString(Path.of("data/synthetic/manifest.json"))).path("events"):List.of();
        return Map.of("officialHistoricalDocuments",knowledge.sources().stream().filter(k->k.category().equals("gameplay")).toList(),"syntheticEvents",synthetic);
    }
    @PostMapping("/api/metrics/query") Object metric(@Valid @RequestBody MetricRequest p) {
        long began=System.nanoTime();Object result=metrics.query(p.metric(),p.startDate(),p.endDate(),p.eventId(),p.platform());
        return Map.of("requestId",UUID.randomUUID().toString(),"elapsedMs",(System.nanoTime()-began)/1e6,"result",result);
    }
    @GetMapping("/api/evaluation/summary") Object evaluation() throws Exception {
        Path path=Path.of("evidence/v2/stage-e/summary.json");
        return Files.exists(path)?json.readTree(Files.readString(path)):Map.of("status","PARTIAL","reason","Evaluation not completed yet");
    }
    @ExceptionHandler(SecurityException.class) Object forbidden(SecurityException e) {return ResponseEntity.status(403).body(Map.of("status","SESSION_ACCESS_DENIED"));}
    @ExceptionHandler({ExecutionException.class}) Object failed(ExecutionException e) {return ResponseEntity.status(503).body(Map.of("status","DEPENDENCY_ERROR"));}
    @PreDestroy void stop() {pool.shutdownNow();}
    @GetMapping("/api/v2/health") Object health() {return Map.of("status","UP","knowledge",knowledge.status(),"metrics",metrics.status(),"model",model);}
    @PostMapping("/api/v2/agent") Object agent(@Valid @RequestBody Probe p) throws Exception {
        if(p.history()!=null && (p.history().size()>6 || p.history().stream().mapToInt(t->t.user().length()+t.assistant().length()+t.toolSummary().length()).sum()>8000))throw new IllegalArgumentException("history too large");
        java.util.concurrent.Future<?> task=pool.submit(()->engine.run(p.model()==null?model:p.model(),p.profile()==null?"guided":p.profile(),p.question(),p.history()==null?List.of():p.history()));
        try{return task.get(240,TimeUnit.SECONDS);}catch(TimeoutException e){task.cancel(true);return ResponseEntity.status(504).body(Map.of("status","TIMEOUT"));}
    }
    @ExceptionHandler({IllegalArgumentException.class}) Object invalid(IllegalArgumentException e) {return ResponseEntity.badRequest().body(Map.of("status","INVALID_ARGUMENT"));}
}
