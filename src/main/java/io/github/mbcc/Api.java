package io.github.mbcc;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class Api {
    public record Question(@NotBlank @Size(max=1000) String question, @Size(max=100) String character, @Size(max=100) String version) {}
    private final KnowledgeIndex index;
    private final CopilotService service;
    @org.springframework.beans.factory.annotation.Autowired(required=false)
    private io.github.mbcc.v2.KnowledgeGateway v2Knowledge;
    @org.springframework.beans.factory.annotation.Autowired(required=false)
    private io.github.mbcc.v2.AgentEngine v2Agent;
    @org.springframework.beans.factory.annotation.Value("${mbcc.chat-model:qwen3:1.7b}")
    private String modelName;
    public Api(KnowledgeIndex index, CopilotService service) { this.index=index; this.service=service; }
    @GetMapping("/health") Object health() {
        if(v2Knowledge==null)return Map.of("status", "UP", "store", "IN_MEMORY", "embedding", "REAL_OLLAMA", "documents", index.sources().size(), "chunks", index.chunks());
        var status=new java.util.LinkedHashMap<String,Object>((Map<String,Object>)v2Knowledge.status());
        status.put("status","UP");status.put("embedding","REAL_OLLAMA");status.put("model",modelName);status.put("legacy_documents",index.sources().size());return status;
    }
    @GetMapping("/sources") Object sources() { return index.sources(); }
    @PostMapping("/search") Object search(@Valid @RequestBody Question q) { return index.search(q.question(),q.character(),q.version(),null,4); }
    @PostMapping("/ask") Object ask(@Valid @RequestBody Question q) { return service.ask(q.question(),q.character(),q.version()); }
    @PostMapping("/agent") Object agent(@Valid @RequestBody Question q) {
        // Preserve the legacy Java fixture/tests, but retire its fixed Synthetic metric tool from public runtime routing.
        if(v2Agent!=null)return v2Agent.run(modelName,"tools",q.question()+"\n用户过滤：character="+q.character()+", version="+q.version());
        return service.agent(q.question());
    }
    @ExceptionHandler(RuntimeException.class)
    ResponseEntity<?> unavailable(RuntimeException e) { return ResponseEntity.status(503).body(Map.of("status","MODEL_OR_RETRIEVAL_FAILED", "error",e.getClass().getSimpleName())); }
}
