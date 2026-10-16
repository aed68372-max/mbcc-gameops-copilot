package io.github.mbcc.v2;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class SqlProvenanceTest {
    @Test void onlySuccessfulSqlGetsAnAuditableSourceId() {
        var fake=new MetricsGateway(new ObjectMapper(),true,"unused") {
            @Override public Object query(Metric metric,String start,String end,String event,String platform) {
                return Map.of("status","OK","synthetic",true,"rows",List.of(Map.of("active_users",3)));
            }
        };
        var tools=new AgentTools(null,fake,"test-run");
        var ok=tools.queryGameMetrics(MetricsGateway.Metric.PAYMENT,"2025-01-01","2025-01-10",null,null);
        assertEquals("test-run:1",((Map<?,?>)ok.data()).get("source_id"));
        assertEquals(Set.of("test-run:1"),tools.cited());
        var invalid=tools.queryGameMetrics(MetricsGateway.Metric.PAYMENT,"bad","2025-01-10",null,null);
        assertNotEquals("OK",invalid.status());assertEquals(Set.of("test-run:1"),tools.cited());
        assertEquals("test-run:1",tools.traces().get(0).callId());
    }
}
