CREATE TABLE sracollector.sra_run_missing
(
    id                         SERIAL PRIMARY KEY,
    sra_project_id               INTEGER      NOT NULL REFERENCES sracollector.sra_project (id) ON UPDATE CASCADE ON DELETE CASCADE,
    pysradb_error_reference_id INTEGER      NOT NULL REFERENCES sracollector.pysradb_error_reference (id),
    details                    VARCHAR(500) NOT NULL
);

CREATE TABLE sracollector_dev.sra_run_missing
(
    id                         SERIAL PRIMARY KEY,
    sra_project_id               INTEGER      NOT NULL REFERENCES sracollector_dev.sra_project (id) ON UPDATE CASCADE ON DELETE CASCADE,
    pysradb_error_reference_id INTEGER      NOT NULL REFERENCES sracollector_dev.pysradb_error_reference (id),
    details                    VARCHAR(500) NOT NULL
);
