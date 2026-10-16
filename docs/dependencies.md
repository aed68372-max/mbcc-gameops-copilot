# Dependency verification — 2026-10-16

Official references consulted:
- https://docs.langchain4j.dev/get-started/ (Java 17 minimum; AI Services uses `langchain4j`)
- https://docs.langchain4j.dev/tutorials/spring-boot-integration/ (Spring Boot 3.5+, Java 17; Boot 3 and Boot 4 starters differ)
- https://docs.langchain4j.dev/integrations/language-models/ollama/ (`langchain4j-ollama:1.22.0`, ChatModel, think(false))
- https://docs.langchain4j.dev/integrations/embedding-models/ollama/
- https://docs.langchain4j.dev/integrations/embedding-stores/milvus/ (future migration: `langchain4j-milvus-v2:1.22.0-beta32`, Milvus 2.5+, Java 17)

This project explicitly wires AI Services using Spring beans. It does not need the beta Spring starter. Core and Ollama use the same stable 1.22.0 version. Spring Boot is pinned to 3.5.7. Dependency resolution/build evidence is recorded separately; consulting a documentation page alone does not prove runtime compatibility. Milvus is not a runtime dependency in round one and has not been validated.

The live documentation pages displayed different minor versions in different sections. The Ollama page's exact version was selected rather than combining unrelated latest versions. See evidence for the version actually resolved.
