package io.github.mbcc.v2;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;

@Service
public class SessionStore {
    public record Created(String sessionId,String accessToken,long idleTimeoutSeconds) {}
    public record Turn(String user,String assistant,String toolSummary) {}
    public static class State {
        public String sessionId,tokenHash;
        public long updatedAt;
        public List<Turn> turns=new ArrayList<>();
    }
    private final ObjectMapper json;
    private final Path folder;
    private static final long TTL=1800;
    private final SecureRandom random=new SecureRandom();
    private final ConcurrentMap<String,State> states=new ConcurrentHashMap<>();
    @org.springframework.beans.factory.annotation.Autowired
    public SessionStore(ObjectMapper json) {this(json,Path.of(".runtime/sessions"));}
    public SessionStore(ObjectMapper json,Path folder) {this.json=json;this.folder=folder.toAbsolutePath().normalize();}
    public synchronized Created create() {
        cleanup();if(states.size()>=100)throw new IllegalStateException("session capacity reached");
        String id=UUID.randomUUID().toString();byte[] secret=new byte[32];random.nextBytes(secret);
        String token=Base64.getUrlEncoder().withoutPadding().encodeToString(secret);
        State state=new State();state.sessionId=id;state.tokenHash=hash(token);state.updatedAt=Instant.now().getEpochSecond();
        states.put(id,state);persist(state);return new Created(id,token,TTL);
    }
    public synchronized State authenticate(String id,String token) {
        if(id==null || !id.matches("[0-9a-f-]{36}") || token==null)throw new SecurityException("session access denied");
        State state=states.get(id);
        if(state==null) {
            try {state=json.readValue(Files.readString(path(id)),State.class);states.put(id,state);}catch(Exception e){throw new SecurityException("session access denied");}
        }
        if(!MessageDigest.isEqual(state.tokenHash.getBytes(StandardCharsets.UTF_8),hash(token).getBytes(StandardCharsets.UTF_8)))throw new SecurityException("session access denied");
        if(Instant.now().getEpochSecond()-state.updatedAt>TTL){states.remove(id);delete(id);throw new SecurityException("session expired");}
        return state;
    }
    public synchronized List<Turn> history(String id,String token) {return List.copyOf(authenticate(id,token).turns);}
    public synchronized void append(String id,String token,String user,AgentEngine.Run run) {
        State s=authenticate(id,token);
        String answer=!run.status().equals("OK") || run.reply()==null?"[模型输出校验失败，不作为事实记忆]":run.reply().answer();
        String summary=run.tools().stream().map(t->t.tool()+":"+t.status()).reduce("",(a,b)->a+" "+b);
        s.turns.add(new Turn(limit(user,2000),limit(answer,4000),limit(summary,1000)));
        while(s.turns.size()>6 || (s.turns.size()>1 && s.turns.stream().mapToInt(t->t.user().length()+t.assistant().length()+t.toolSummary().length()).sum()>8000))s.turns.remove(0);
        s.updatedAt=Instant.now().getEpochSecond();persist(s);
    }
    @org.springframework.scheduling.annotation.Scheduled(fixedDelay=60000)
    public synchronized void cleanup() {
        long now=Instant.now().getEpochSecond();
        states.values().removeIf(s->{if(now-s.updatedAt>TTL){delete(s.sessionId);return true;}return false;});
        if(Files.isDirectory(folder))try(var files=Files.list(folder)) {
            files.filter(p->p.getFileName().toString().matches("[0-9a-f-]{36}\\.json")).forEach(p->{
                try{var s=json.readValue(Files.readString(p),State.class);if(now-s.updatedAt>TTL)Files.deleteIfExists(p);}catch(Exception ignored){}
            });
        }catch(Exception e){throw new IllegalStateException("session cleanup failed");}
    }
    private Path path(String id) {Path p=folder.resolve(id+".json").normalize();if(!p.startsWith(folder))throw new SecurityException();return p;}
    private void delete(String id) {try{Files.deleteIfExists(path(id));}catch(Exception e){throw new IllegalStateException("session delete failed");}}
    private void persist(State s) {try{Files.createDirectories(folder);Files.writeString(path(s.sessionId),json.writeValueAsString(s));}catch(Exception e){throw new IllegalStateException("history persistence failed",e);}}
    private String hash(String s) {try{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));}catch(Exception e){throw new IllegalStateException(e);}}
    private String limit(String s,int size) {return s.length()>size?s.substring(0,size):s;}
}
