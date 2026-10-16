package io.github.mbcc.v2;

import io.github.mbcc.Knowledge;
import io.github.mbcc.KnowledgeIndex;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.*;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import dev.langchain4j.store.embedding.milvus.v2.MilvusV2EmbeddingStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import static dev.langchain4j.store.embedding.filter.MetadataFilterBuilder.metadataKey;

/** Round two gateway; the legacy twelve-entry index and API remain compatible. */
@Service
public class KnowledgeGateway {
    private final Map<String,Knowledge> documents=new LinkedHashMap<>();
    private final EmbeddingModel model;
    private final EmbeddingStore<TextSegment> store;
    private final String kind,collection,uri;
    private final ObjectMapper json;
    private final List<TextSegment> segments=new ArrayList<>();
    public KnowledgeGateway(EmbeddingModel model,ObjectMapper json,@Value("${mbcc.vector-store:memory}") String kind,
         @Value("${mbcc.milvus-uri:http://localhost:19530}") String uri,
         @Value("${mbcc.embedding-model}") String embeddingName,@Value("${mbcc.ollama-url}") String ollama) throws Exception {
        this.model=model;this.json=json;this.kind=kind;this.uri=uri;
        for(String file:List.of("/knowledge.json","/knowledge-v2.json")) {
            try(var input=getClass().getResourceAsStream(file)) {
                List<Knowledge> entries=json.readValue(Objects.requireNonNull(input),new TypeReference<>(){});
                for(var k:entries) {
                    if(k.source_id()==null || k.source_url()==null || !k.source_url().startsWith("https://wqmt.aisnogames.com/")) throw new IllegalArgumentException("source metadata invalid");
                    if(documents.putIfAbsent(k.source_id(),k)!=null)throw new IllegalArgumentException("duplicate source id");
                }
            }
        }
        String corpusHash=hash(json.writer().without(com.fasterxml.jackson.databind.SerializationFeature.INDENT_OUTPUT).writeValueAsString(documents.values()));
        collection="mbcc_v2_"+corpusHash.substring(0,12);
        store=switch(kind) {
            case "memory" -> new InMemoryEmbeddingStore<>();
            case "milvus" -> MilvusV2EmbeddingStore.builder().uri(uri).collectionName(collection).dimension(1024).build();
            default -> throw new IllegalArgumentException("MBCC_VECTOR_STORE must be memory or milvus");
        };
        // Bind the cache to actual Ollama model digest and document text; tag reuse cannot silently reuse old vectors.
        var http=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        var tags=http.send(HttpRequest.newBuilder(URI.create(ollama+"/api/tags")).timeout(Duration.ofSeconds(10)).GET().build(),HttpResponse.BodyHandlers.ofString());
        String digest=null;
        for(var node:json.readTree(tags.body()).path("models")) if(node.path("name").asText().equals(embeddingName))digest=node.path("digest").asText();
        if(digest==null)throw new IllegalStateException("embedding model unavailable");
        Path cache=Path.of(".runtime/embedding-"+hash(embeddingName+digest).substring(0,16)+".json");
        Map<String,float[]> vectors=Files.exists(cache)?json.readValue(Files.readString(cache),new TypeReference<>(){}):new LinkedHashMap<>();
        Set<String> seen=new HashSet<>();
        for(var k:documents.values()) {
            String clean=k.content().replaceAll("\\s+"," ").trim();
            if(!seen.add(k.source_url()+clean))continue;
            for(int offset=0;offset<clean.length();offset+=400) {
                String text=k.title()+" "+clean.substring(offset,Math.min(offset+400,clean.length()));
                String id=UUID.nameUUIDFromBytes((k.source_id()+":"+offset+":"+corpusHash).getBytes(StandardCharsets.UTF_8)).toString();
                var metadata=new Metadata().put("source_id",k.source_id()).put("character_name",k.character_name())
                      .put("game_version",k.game_version()).put("category",k.category()).put("chunk_id",id);
                var segment=TextSegment.from(text,metadata);segments.add(segment);
                float[] vector=vectors.get(hash(text));
                if(vector==null){vector=model.embed(segment).content().vector();vectors.put(hash(text),vector);}
                if(vector.length!=1024)throw new IllegalStateException("unexpected embedding dimension");
                Embedding embedding=Embedding.from(vector);
                boolean exists=kind.equals("milvus") && !store.search(EmbeddingSearchRequest.builder().queryEmbedding(embedding)
                        .filter(metadataKey("chunk_id").isEqualTo(id)).maxResults(1).build()).matches().isEmpty();
                if(!exists)store.addAll(List.of(id),List.of(embedding),List.of(segment));
            }
        }
        Files.createDirectories(cache.getParent());Files.writeString(cache,json.writeValueAsString(vectors));
    }
    private static String hash(String text) throws Exception {return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));}
    public List<KnowledgeIndex.Hit> search(String query, String character, String version, String category, int k) {
        if(query==null || query.isBlank())return List.of();
        var filter=metadataKey("source_id").isIn(new ArrayList<>(documents.keySet()));
        if(character!=null && !character.isBlank())filter=filter.and(metadataKey("character_name").isEqualTo(character));
        if(version!=null && !version.isBlank())filter=filter.and(metadataKey("game_version").isEqualTo(version));
        if(category!=null && !category.isBlank())filter=filter.and(metadataKey("category").isEqualTo(category));
        String semanticQuery=character==null || character.isBlank()?query:character+" "+query;
        return store.search(EmbeddingSearchRequest.builder().queryEmbedding(model.embed(semanticQuery).content()).filter(filter)
                .maxResults(Math.max(1,Math.min(k,10))).minScore(.70).build()).matches().stream()
                .map(m->new KnowledgeIndex.Hit(m.score(),m.embedded().text(),documents.get(m.embedded().metadata().getString("source_id")))).toList();
    }
    public List<KnowledgeIndex.Hit> keywordSearch(String query,int k) {
        Set<String> terms=terms(query);
        return segments.stream().map(s->{var overlap=terms(s.text());overlap.retainAll(terms);
            return new KnowledgeIndex.Hit(terms.isEmpty()?0:(double)overlap.size()/terms.size(),s.text(),documents.get(s.metadata().getString("source_id")));})
            .filter(h->h.score()>0).sorted(Comparator.comparingDouble(KnowledgeIndex.Hit::score).reversed()).limit(k).toList();
    }
    private Set<String> terms(String text) {
        String s=text.toLowerCase().replaceAll("[^\\p{L}\\p{N}]","");Set<String> result=new HashSet<>();
        for(int i=0;i+1<s.length();i++)result.add(s.substring(i,i+2));return result;
    }
    public Object status() {
        Map<String,Object> result=new LinkedHashMap<>();result.put("store",kind.equals("milvus")?"MILVUS":"IN_MEMORY");
        result.put("documents",documents.size());result.put("chunks",segments.size());result.put("dimension",1024);result.put("collection",collection);
        result.put("milvusVerified",false); // Only the external write/restart/reconnect probe may establish verification.
        return result;
    }
    public Collection<Knowledge> sources() { return List.copyOf(documents.values()); }
}
