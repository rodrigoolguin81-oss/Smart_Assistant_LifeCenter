-- SPEC-002 (R3): accent-insensitive Spanish full-text search over knowledge base fragments.
-- Idempotent: safe to re-run.

CREATE EXTENSION IF NOT EXISTS unaccent;

-- unaccent() is not IMMUTABLE, so it cannot appear in a generated column. Accent-folding is done
-- inside this text search configuration's dictionary mapping instead (see plan.md).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'spanish_unaccent') THEN
        CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish);
        ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
            ALTER MAPPING FOR hword, hword_part, word
            WITH unaccent, spanish_stem;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS kb_fragments (
    fragment_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     text    NOT NULL,
    tipo          text    NOT NULL,
    titulo        text    NOT NULL,
    vigente_desde date    NOT NULL,
    ejemplo       boolean NOT NULL DEFAULT false,
    chunk_text    text    NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('spanish_unaccent', chunk_text)) STORED
);

CREATE INDEX IF NOT EXISTS kb_fragments_search_vector_idx
    ON kb_fragments USING gin (search_vector);
