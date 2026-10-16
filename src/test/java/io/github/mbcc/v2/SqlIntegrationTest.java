package io.github.mbcc.v2;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
@EnabledIfEnvironmentVariable(named="MBCC_SQL_TESTS",matches="true")
class SqlIntegrationTest {
    @ParameterizedTest @EnumSource(MetricsGateway.Metric.class)
    void fixedMetricRunsWithReadonlyDatabaseUser(MetricsGateway.Metric metric) {
        var gateway=new MetricsGateway(new ObjectMapper(),true,System.getenv().getOrDefault("MBCC_PYTHON","python"));
        var result=(Map<?,?>)gateway.query(metric,"2025-01-11","2025-01-20",null,null);
        assertEquals("OK",result.get("status"));assertEquals(true,result.get("synthetic"));
        assertEquals("mbcc_reader",((Map<?,?>)result.get("identity")).get("database_user"));
        assertEquals(true,result.get("parameterized"));assertNotNull(result.get("definition"));
    }
}
