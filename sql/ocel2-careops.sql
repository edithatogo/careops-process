-- Privacy-preserving relational projection of the CareOps OCEL 2.0 contract.
CREATE TABLE ocel_log (log_id VARCHAR(128) PRIMARY KEY, ocel_version CHAR(3) NOT NULL CHECK (ocel_version = '2.0'), schema_version VARCHAR(32) NOT NULL, lineage VARCHAR(500) NOT NULL);
CREATE TABLE ocel_object (object_id VARCHAR(128) PRIMARY KEY, log_id VARCHAR(128) NOT NULL REFERENCES ocel_log(log_id), object_type VARCHAR(80) NOT NULL, attributes_json JSON NOT NULL);
CREATE TABLE ocel_event (event_id VARCHAR(128) PRIMARY KEY, log_id VARCHAR(128) NOT NULL REFERENCES ocel_log(log_id), event_type VARCHAR(120) NOT NULL, timestamp_utc TIMESTAMP WITH TIME ZONE NOT NULL, source_system VARCHAR(80) NOT NULL, observed_or_inferred VARCHAR(9) NOT NULL CHECK (observed_or_inferred IN ('observed','inferred')), confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1), qualifiers_json JSON NOT NULL);
CREATE TABLE ocel_event_object (event_id VARCHAR(128) NOT NULL REFERENCES ocel_event(event_id), object_id VARCHAR(128) NOT NULL REFERENCES ocel_object(object_id), PRIMARY KEY (event_id, object_id));
CREATE TABLE ocel_object_relation (relation_id VARCHAR(128) PRIMARY KEY, log_id VARCHAR(128) NOT NULL REFERENCES ocel_log(log_id), relation_type VARCHAR(120) NOT NULL, source_object_id VARCHAR(128) NOT NULL REFERENCES ocel_object(object_id), target_object_id VARCHAR(128) NOT NULL REFERENCES ocel_object(object_id), observed_or_inferred VARCHAR(9) NOT NULL CHECK (observed_or_inferred IN ('observed','inferred')), confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1), CHECK (source_object_id <> target_object_id));
CREATE INDEX idx_ocel_object_log_id ON ocel_object(log_id);
CREATE INDEX idx_ocel_event_log_id ON ocel_event(log_id);
CREATE INDEX idx_ocel_event_object_object_id ON ocel_event_object(object_id);
CREATE INDEX idx_ocel_relation_log_id ON ocel_object_relation(log_id);
CREATE INDEX idx_ocel_relation_source_id ON ocel_object_relation(source_object_id);
CREATE INDEX idx_ocel_relation_target_id ON ocel_object_relation(target_object_id);
