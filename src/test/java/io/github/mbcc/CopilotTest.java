package io.github.mbcc;

import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.output.Response;
import org.junit.jupiter.api.Test;
import org.springframework.validation.beanvalidation.LocalValidatorFactoryBean;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class CopilotTest {
    // MOCK embeddings deliberately have no semantic value. These tests verify plumbing and guards only.
    KnowledgeIndex index() throws Exception {
        EmbeddingModel embedding = mock(EmbeddingModel.class);
        when(embedding.embed(any(TextSegment.class))).thenReturn(Response.from(Embedding.from(new float[]{1,0,0})));
        when(embedding.embed(anyString())).thenReturn(Response.from(Embedding.from(new float[]{1,0,0})));
        return new KnowledgeIndex(embedding, new ObjectMapper());
    }
    @Test void curatedSourcesHaveRequiredMetadata() throws Exception {
        var index = index();
        assertEquals(12, index.sources().size());
        assertTrue(index.chunks() >= 12);
        for(var k : index.sources()) {
            assertTrue(k.source_url().startsWith("https://wqmt.aisnogames.com/news/"));
            assertEquals("verified_public_page", k.verification_status());
            assertFalse(k.game_version().isBlank());
            assertFalse(k.title().isBlank());
        }
    }
    @Test void filtersApplyBeforeTopKAndMissingVersionReturnsNothing() throws Exception {
        var index = index();
        var found = index.search("生日", "赫卡蒂", null, "character", 10);
        assertFalse(found.isEmpty());
        assertTrue(found.stream().allMatch(h -> h.source().source_id().equals("char-001")));
        assertTrue(index.search("生日", "赫卡蒂", "不存在版本", null, 10).isEmpty());
    }
    @Test void noEvidenceDoesNotInvokeChat() throws Exception {
        var model = mock(ChatModel.class);
        var service = new CopilotService(index(), model);
        var result = service.ask("未收录角色经历", "不存在的角色", null);
        assertEquals("REAL_RETRIEVAL_NO_EVIDENCE", result.mode());
        assertTrue(result.answer().contains("未收录"));
        verifyNoInteractions(model);
    }
    @Test void mockAiServicesActuallyExecutesToolLoop() throws Exception {
        var model = mock(ChatModel.class);
        var call = ToolExecutionRequest.builder().id("mock-1").name("getSyntheticOperationsMetrics").arguments("{}").build();
        when(model.chat(any(ChatRequest.class))).thenReturn(
                ChatResponse.builder().aiMessage(AiMessage.from(call)).build(),
                ChatResponse.builder().aiMessage(AiMessage.from("Synthetic payerRate=5%" )).build());
        var result = new CopilotService(index(), model).agent("模拟指标");
        assertEquals(1,result.executedTools().size());
        assertTrue(result.executedTools().get(0).startsWith("getSyntheticOperationsMetrics"));
        assertTrue(result.toolEvidence().get(0).result().contains("Synthetic: activeUsers=1000, payingUsers=50"));
        assertFalse(result.toolEvidence().get(0).failed());
        assertEquals("SYNTHETIC_TOOL_RESULT", result.answerStatus());
        assertEquals(result.toolEvidence().get(0).result(), result.answer());
        assertEquals("Synthetic payerRate=5%", result.modelDraft());
        verify(model,times(2)).chat(any(ChatRequest.class));
    }
    @Test void restRejectsBlankInput() throws Exception {
        var validator = new LocalValidatorFactoryBean();
        validator.afterPropertiesSet();
        var mvc = MockMvcBuilders.standaloneSetup(new Api(mock(KnowledgeIndex.class),mock(CopilotService.class)))
                .setValidator(validator).build();
        mvc.perform(post("/api/ask").contentType("application/json").content("{\"question\":\" \"}"))
                .andExpect(status().isBadRequest());
        validator.close();
    }
}
