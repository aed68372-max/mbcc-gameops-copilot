package io.github.mbcc;

import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.ollama.OllamaChatModel;
import dev.langchain4j.model.ollama.OllamaEmbeddingModel;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import java.time.Duration;

@SpringBootApplication
@org.springframework.scheduling.annotation.EnableScheduling
public class Application {
    public static void main(String[] args) { SpringApplication.run(Application.class, args); }
    @Bean ChatModel chatModel(@Value("${mbcc.ollama-url}") String url, @Value("${mbcc.chat-model}") String name) {
        return OllamaChatModel.builder().baseUrl(url).modelName(name).temperature(0.0)
                .think(false).numPredict(512).timeout(Duration.ofSeconds(90)).build();
    }
    @Bean EmbeddingModel embeddingModel(@Value("${mbcc.ollama-url}") String url, @Value("${mbcc.embedding-model}") String name) {
        return OllamaEmbeddingModel.builder().baseUrl(url).modelName(name).timeout(Duration.ofSeconds(90)).build();
    }
}
