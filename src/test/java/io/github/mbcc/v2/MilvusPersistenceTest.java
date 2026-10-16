package io.github.mbcc.v2;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.ollama.OllamaEmbeddingModel;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import java.net.*;
import java.net.http.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import static org.junit.jupiter.api.Assertions.*;
@EnabledIfEnvironmentVariable(named="MBCC_MILVUS_TESTS",matches="true")
class MilvusPersistenceTest {
    @Test void actualRestartRetainsCountAndSource() throws Exception {
        var embedding=OllamaEmbeddingModel.builder().baseUrl("http://localhost:11434").modelName("qwen3-embedding:0.6b").build();
        var json=new ObjectMapper();var before=new KnowledgeGateway(embedding,json,"milvus","http://127.0.0.1:19530","qwen3-embedding:0.6b","http://localhost:11434");
        var hit=before.search("加洛法诺所属组织","加洛法诺",null,null,5);assertFalse(hit.isEmpty());
        var state=(Map<?,?>)before.status();String collection=state.get("collection").toString();
        long count=stats(collection,json);assertEquals(((Number)state.get("chunks")).longValue(),count);
        var process=new ProcessBuilder(System.getenv().getOrDefault("MBCC_DOCKER","docker"),"compose","-p","mbcc","-f","deploy/compose.milvus.yml","restart","standalone").redirectErrorStream(true).start();
        assertTrue(process.waitFor(60,TimeUnit.SECONDS));assertEquals(0,process.exitValue());
        var http=HttpClient.newHttpClient();boolean ready=false;
        for(int i=0;i<30;i++){try{ready=http.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:9091/healthz")).timeout(Duration.ofSeconds(2)).GET().build(),HttpResponse.BodyHandlers.discarding()).statusCode()==200;}catch(Exception ignored){}if(ready)break;Thread.sleep(1000);}
        assertTrue(ready);
        var after=new KnowledgeGateway(embedding,json,"milvus","http://127.0.0.1:19530","qwen3-embedding:0.6b","http://localhost:11434");
        assertEquals(count,stats(collection,json));assertEquals(hit.get(0).source().source_id(),after.search("加洛法诺所属组织","加洛法诺",null,null,5).get(0).source().source_id());
        System.out.println("REAL_MILVUS_RESTART_COUNT="+count+" SOURCE="+hit.get(0).source().source_id());
    }
    long stats(String collection,ObjectMapper json) throws Exception {
        var body=json.writeValueAsString(Map.of("collectionName",collection));
        var response=HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:19530/v2/vectordb/collections/get_stats")).header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());
        var data=json.readTree(response.body());assertEquals(0,data.path("code").asInt());return data.path("data").path("rowCount").asLong(-1);
    }
}
