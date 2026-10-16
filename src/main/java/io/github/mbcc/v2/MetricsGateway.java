package io.github.mbcc.v2;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Value;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.*;
import java.util.concurrent.*;
import java.nio.charset.StandardCharsets;
import java.io.*;

@Service
public class MetricsGateway {
    public enum Metric { DAU, PAYMENT, RETENTION_D1, RETENTION_D7, EVENT_REVENUE, EVENT_PARTICIPATION }
    private final ObjectMapper json;
    private final boolean enabled;
    private final String python;
    public MetricsGateway(ObjectMapper json,@Value("${mbcc.sql-enabled:false}") boolean enabled,
                          @Value("${mbcc.python:python}") String python) {this.json=json;this.enabled=enabled;this.python=python;}
    public Object query(Metric metric, String startDate, String endDate, String eventId, String platform) {
        if(!enabled)return Map.of("status","BLOCKED","synthetic",true,"reason","SQL integration disabled by configuration");
        Map<String,Object> payload=new LinkedHashMap<>();payload.put("metric",metric.name());payload.put("startDate",startDate);
        payload.put("endDate",endDate);payload.put("eventId",eventId);payload.put("platform",platform);
        Process process=null;
        try {
            var builder=new ProcessBuilder(python,"scripts/sql_bridge.py");builder.environment().put("PYTHONIOENCODING","utf-8");
            process=builder.start();final Process running=process;
            var bytes=CompletableFuture.supplyAsync(()->{try{return running.getInputStream().readAllBytes();}catch(IOException e){throw new UncheckedIOException(e);}});
            // The bridge has a fixed metric allowlist and prepared values; no SQL is ever accepted from an LLM.
            try(var input=process.getOutputStream()){input.write(json.writeValueAsBytes(payload));}
            if(!process.waitFor(25,TimeUnit.SECONDS)){process.destroyForcibly();return Map.of("status","TIMEOUT","synthetic",true);}
            byte[] output=bytes.get(2,TimeUnit.SECONDS);
            if(output.length>1_000_000 || process.exitValue()!=0)throw new IOException("SQL bridge failed");
            return json.readValue(new String(output,StandardCharsets.UTF_8),Map.class);
        } catch(Exception e) {return Map.of("status","UNAVAILABLE","synthetic",true,"error",e.getClass().getSimpleName());}
        finally {if(process!=null && process.isAlive())process.destroyForcibly();}
    }
    public Object status() { return Map.of("status",enabled?"CONFIGURED_NOT_A_LIVE_PROBE":"BLOCKED","synthetic",true,
            "database","MBCCCopilotSynthetic","query_user","mbcc_reader","transport","Windows ODBC via bounded local bridge"); }
}
