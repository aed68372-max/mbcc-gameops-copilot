package io.github.mbcc;

public record Knowledge(String source_id, String title, String source_url, String source_type,
                        String character_name, String game_version, String collected_at,
                        String content_type, String verification_status, String category, String content) {}
