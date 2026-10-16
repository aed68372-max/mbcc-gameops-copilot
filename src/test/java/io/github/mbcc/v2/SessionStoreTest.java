package io.github.mbcc.v2;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class SessionStoreTest {
    @TempDir Path temp;
    AgentEngine.Run run(String answer) {return new AgentEngine.Run("test","mock","tools","OK",1,new AgentEngine.Reply(answer,List.of(),false,false),"",List.of(),List.of(),null,List.of(),null);}
    @Test void twoSessionsAreIsolatedAndWrongCapabilityIsDenied() {
        var store=new SessionStore(new ObjectMapper(),temp);var a=store.create();var b=store.create();
        store.append(a.sessionId(),a.accessToken(),"介绍罗睺",run("只保留本会话内容"));
        assertEquals(1,store.history(a.sessionId(),a.accessToken()).size());
        assertTrue(store.history(b.sessionId(),b.accessToken()).isEmpty());
        assertThrows(SecurityException.class,()->store.history(a.sessionId(),b.accessToken()));
    }
    @Test void tokenIsHashedAndHistorySurvivesStoreRecreation() throws Exception {
        var store=new SessionStore(new ObjectMapper(),temp);var a=store.create();
        store.append(a.sessionId(),a.accessToken(),"问题",run("回答"));
        String file=Files.readString(temp.resolve(a.sessionId()+".json"));assertFalse(file.contains(a.accessToken()));
        var restored=new SessionStore(new ObjectMapper(),temp);
        assertEquals("问题",restored.history(a.sessionId(),a.accessToken()).get(0).user());
    }
    @Test void historyHasBothTurnAndCharacterBounds() {
        var store=new SessionStore(new ObjectMapper(),temp);var a=store.create();
        for(int i=0;i<12;i++)store.append(a.sessionId(),a.accessToken(),"问".repeat(2000),run("答".repeat(4000)));
        var turns=store.history(a.sessionId(),a.accessToken());assertTrue(turns.size()<=6);
        assertTrue(turns.stream().mapToInt(t->t.user().length()+t.assistant().length()+t.toolSummary().length()).sum()<=8000);
    }
    @Test void idleSessionExpiresWithoutSleepingOrHardcodedPronounResolver() {
        var store=new SessionStore(new ObjectMapper(),temp);var a=store.create();
        store.authenticate(a.sessionId(),a.accessToken()).updatedAt-=1801;
        assertThrows(SecurityException.class,()->store.history(a.sessionId(),a.accessToken()));
        assertFalse(Files.exists(temp.resolve(a.sessionId()+".json")));
    }
}
