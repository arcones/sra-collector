CREATE TABLE sracollector.sra_project_missing
(
    id                         SERIAL PRIMARY KEY,
    geo_study_id               INTEGER      NOT NULL REFERENCES sracollector.geo_study (id) ON UPDATE CASCADE ON DELETE CASCADE,
    pysradb_error_reference_id INTEGER      NOT NULL REFERENCES sracollector.pysradb_error_reference (id),
    details                    VARCHAR(500) NOT NULL
);

CREATE TABLE sracollector_dev.sra_project_missing
(
    id                         SERIAL PRIMARY KEY,
    geo_study_id               INTEGER      NOT NULL REFERENCES sracollector_dev.geo_study (id) ON UPDATE CASCADE ON DELETE CASCADE,
    pysradb_error_reference_id INTEGER      NOT NULL REFERENCES sracollector_dev.pysradb_error_reference (id),
    details                    VARCHAR(500) NOT NULL
);
