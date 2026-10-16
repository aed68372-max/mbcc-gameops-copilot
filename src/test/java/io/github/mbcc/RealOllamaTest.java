package io.github.mbcc;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.model.ollama.OllamaEmbeddingModel;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import java.time.Duration;
import static org.junit.jupiter.api.Assertions.*;

@EnabledIfEnvironmentVariable(named="MBCC_REAL_TESTS", matches="true")
class RealOllamaTest {
    @Test void realJavaChatEmbeddingRagAndToolProbe() throws Exception {
        var chat = OllamaChatModel.builder().baseUrl("http://localhost:11434").modelName("qwen3:0.6b")
                .think(false).temperature(0.0).numPredict(512).timeout(Duration.ofSeconds(90)).build();
        String greeting = chat.chat("请只回答：连接成功");
        System.out.println("REAL_JAVA_CHAT=" + greeting);
        assertFalse(greeting.isBlank());
        var embedding = OllamaEmbeddingModel.builder().baseUrl("http://localhost:11434")
                .modelName("qwen3-embedding:0.6b").timeout(Duration.ofSeconds(90)).build();
        var vector = embedding.embed("赫卡蒂生日").content();
        System.out.println("REAL_EMBEDDING_DIMENSION=" + vector.dimension());
        assertEquals(1024,vector.dimension());
        var index = new KnowledgeIndex(embedding, new ObjectMapper());
        var hits = index.search("赫卡蒂生日收到谁的明信片？", "赫卡蒂", null, null, 4);
        System.out.println("REAL_RETRIEVAL=" + hits);
        assertFalse(hits.isEmpty());
        assertEquals("char-001",hits.get(0).source().source_id());
        var service = new CopilotService(index,chat);
        var answer = service.ask("赫卡蒂生日收到谁的明信片？", "赫卡蒂", null);
        System.out.println("REAL_RAG=" + answer);
        assertTrue(answer.answer().contains("海拉"));
        var tool = service.agent("请调用 getSyntheticOperationsMetrics 工具，报告模拟付费率。必须使用工具，不要自己算。");
        System.out.println("REAL_AI_SERVICES_TOOL=" + tool);
        assertTrue(tool.executedTools().stream().anyMatch(t -> t.startsWith("getSyntheticOperationsMetrics")),
                "Real Qwen did not select the expected tool; MOCK success must not conceal this failure");
    }
}
