package io.github.mbcc.v2;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AgentValidationTest {
    @Test void rejectsMalformedModelOutput() {
        var engine=new AgentEngine(mock(KnowledgeGateway.class),mock(MetricsGateway.class),new ObjectMapper(),"http://localhost:11434");
        assertThrows(Exception.class,()->engine.parse("I already called a tool"));
        assertThrows(Exception.class,()->engine.parse("{\"answer\":\"a\",\"citations\":[],\"abstained\":\"false\",\"clarification\":false}"));
    }
    @Test void badToolArgumentsAreLoggedWithoutExecutingDependency() {
        var gateway=mock(KnowledgeGateway.class);
        var tools=new AgentTools(gateway,mock(MetricsGateway.class),"test");
        assertEquals("INVALID_ARGUMENT",tools.searchCharacterKnowledge(null,"背景",null).status());
        verifyNoInteractions(gateway);
        assertEquals(1,tools.traces().size());
        assertEquals("test:1",tools.traces().get(0).callId());
        assertTrue(tools.traces().get(0).elapsedMs()>=0);
    }
    @Test void metricWindowInjectionIsRejected() {
        var metrics=mock(MetricsGateway.class);
        var tools=new AgentTools(mock(KnowledgeGateway.class),metrics,"test");
        assertEquals("INVALID_ARGUMENT",tools.queryGameMetrics(MetricsGateway.Metric.DAU,"2025-02-02","2025-01-01",null,null).status());
        verifyNoInteractions(metrics);
    }
}
