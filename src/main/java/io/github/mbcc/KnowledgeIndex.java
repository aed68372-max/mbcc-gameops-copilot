package io.github.mbcc;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingSearchRequest;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import org.springframework.stereotype.Service;
import java.io.IOException;
import java.util.*;
import static dev.langchain4j.store.embedding.filter.MetadataFilterBuilder.metadataKey;

@Service
public class KnowledgeIndex {
    private final EmbeddingModel model;
    private final InMemoryEmbeddingStore<TextSegment> store = new InMemoryEmbeddingStore<>();
    private final Map<String, Knowledge> documents = new LinkedHashMap<>();
    private int chunks;
    public record Hit(double score, String chunk, Knowledge source) {}
    public KnowledgeIndex(EmbeddingModel model, ObjectMapper mapper) throws IOException {
        this.model = model;
        try (var input = Objects.requireNonNull(getClass().getResourceAsStream("/knowledge.json"))) {
            List<Knowledge> data = mapper.readValue(input, new TypeReference<>() {});
            Set<String> seen = new HashSet<>();
            for (Knowledge k : data) {
                String cleaned = k.content().replaceAll("\\s+", " ").trim();
                if (!seen.add(k.source_url() + cleaned)) continue;
                if (documents.putIfAbsent(k.source_id(), k) != null) throw new IllegalArgumentException("duplicate source_id");
                // Curated JSON entries are section boundaries; long sections split by sentence, with a hard size cap.
                for (String section : cleaned.split("(?<=。)")) {
                    for (int start = 0; start < section.length(); start += 400) {
                        String text = k.title() + " " + section.substring(start, Math.min(start + 400, section.length()));
                        Metadata meta = new Metadata().put("source_id", k.source_id()).put("category", k.category())
                                .put("character_name", k.character_name()).put("game_version", k.game_version());
                        TextSegment segment = TextSegment.from(text, meta);
                        store.add(model.embed(segment).content(), segment);
                        chunks++;
                    }
                }
            }
        }
    }
    public Collection<Knowledge> sources() { return List.copyOf(documents.values()); }
    public int chunks() { return chunks; }
    public List<Hit> search(String query, String character, String version, String category, int topK) {
        var request = EmbeddingSearchRequest.builder().queryEmbedding(model.embed(query).content())
                .maxResults(Math.max(1, Math.min(topK, 10))).minScore(0.70);
        var filter = metadataKey("source_id").isIn(new ArrayList<>(documents.keySet()));
        if (character != null && !character.isBlank()) filter = filter.and(metadataKey("character_name").isEqualTo(character));
        if (version != null && !version.isBlank()) filter = filter.and(metadataKey("game_version").isEqualTo(version));
        if (category != null && !category.isBlank()) filter = filter.and(metadataKey("category").isEqualTo(category));
        request.filter(filter);
        return store.search(request.build()).matches().stream().map(m -> new Hit(m.score(), m.embedded().text(),
                documents.get(m.embedded().metadata().getString("source_id")))).toList();
    }
}
