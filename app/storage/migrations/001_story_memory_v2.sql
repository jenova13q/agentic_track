CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    synopsis TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_fragments (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    fragment_kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    source_label TEXT NOT NULL,
    text TEXT NOT NULL,
    fragment_order INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS story_chunks (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    fragment_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    source_ref TEXT NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (fragment_id) REFERENCES story_fragments(id) ON DELETE CASCADE,
    UNIQUE(story_id, chunk_index),
    UNIQUE(fragment_id, source_ref)
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    entity_kind TEXT NOT NULL CHECK (entity_kind IN ('character', 'object', 'location', 'group')),
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    confidence REAL NOT NULL DEFAULT 0.5,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entities_story_kind ON entities(story_id, entity_kind);
CREATE INDEX IF NOT EXISTS idx_entities_story_canonical ON entities(story_id, canonical_name);

CREATE TABLE IF NOT EXISTS character_profiles (
    entity_id TEXT PRIMARY KEY,
    trait_summary TEXT NOT NULL DEFAULT '',
    factual_summary TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS object_profiles (
    entity_id TEXT PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    current_state_summary TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    timeline_note TEXT NOT NULL DEFAULT '',
    anchor_event_id TEXT,
    temporal_relation TEXT NOT NULL DEFAULT 'unknown' CHECK (temporal_relation IN ('before', 'after', 'during', 'parallel', 'unknown')),
    sequence_hint TEXT,
    fragment_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    confidence REAL NOT NULL DEFAULT 0.5,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (anchor_event_id) REFERENCES events(id) ON DELETE SET NULL,
    FOREIGN KEY (fragment_id) REFERENCES story_fragments(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_story_status ON events(story_id, status);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'participant',
    PRIMARY KEY (event_id, entity_id, role),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    fact_kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    subject_entity_id TEXT,
    object_entity_id TEXT,
    event_id TEXT,
    timeline_event_id TEXT,
    valid_from_event_id TEXT,
    valid_to_event_id TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    confidence REAL NOT NULL DEFAULT 0.5,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_entity_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (object_entity_id) REFERENCES entities(id) ON DELETE SET NULL,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL,
    FOREIGN KEY (timeline_event_id) REFERENCES events(id) ON DELETE SET NULL,
    FOREIGN KEY (valid_from_event_id) REFERENCES events(id) ON DELETE SET NULL,
    FOREIGN KEY (valid_to_event_id) REFERENCES events(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_facts_story_kind ON facts(story_id, fact_kind);
CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject_entity_id);
CREATE INDEX IF NOT EXISTS idx_facts_object ON facts(object_entity_id);

CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    left_entity_id TEXT NOT NULL,
    right_entity_id TEXT NOT NULL,
    relation_kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    confidence REAL NOT NULL DEFAULT 0.5,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (left_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (right_entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_relations_left ON relations(left_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_right ON relations(right_entity_id);

CREATE TABLE IF NOT EXISTS evidence_links (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    target_table TEXT NOT NULL CHECK (target_table IN ('entity', 'event', 'fact', 'relation')),
    target_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES story_chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_target ON evidence_links(target_table, target_id);

CREATE TABLE IF NOT EXISTS pending_updates (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    fragment_id TEXT,
    summary TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'confirmed', 'rejected', 'conflicted')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
    FOREIGN KEY (fragment_id) REFERENCES story_fragments(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pending_update_items (
    id TEXT PRIMARY KEY,
    pending_update_id TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('entity', 'event', 'fact', 'relation', 'fragment')),
    item_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'close')),
    summary TEXT NOT NULL,
    FOREIGN KEY (pending_update_id) REFERENCES pending_updates(id) ON DELETE CASCADE
);
