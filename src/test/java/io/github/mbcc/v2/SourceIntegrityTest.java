package io.github.mbcc.v2;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.mbcc.Knowledge;
import org.junit.jupiter.api.Test;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
class SourceIntegrityTest {
    @Test void completeCorpusMeetsCoverageAndProvenanceContract() throws Exception {
        Set<String> ids=new HashSet<>();int count=0;
        for(String name:List.of("/knowledge.json","/knowledge-v2.json")) {
            List<Knowledge> rows=new ObjectMapper().readValue(getClass().getResourceAsStream(name),new TypeReference<>(){});
            for(var k:rows) {
                assertTrue(ids.add(k.source_id()));assertTrue(k.source_url().startsWith("https://wqmt.aisnogames.com/news/"));
                assertEquals("official",k.source_type());assertFalse(k.collected_at().isBlank());assertFalse(k.game_version().isBlank());
                assertEquals("verified_public_page",k.verification_status());assertTrue(k.content().length()<400);count++;
            }
        }
        assertTrue(count>=40 && count<=80);
    }
}
