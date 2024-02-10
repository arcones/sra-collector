CREATE TABLE sracollector_dev.request
(
    id         VARCHAR UNIQUE,
    query      VARCHAR(500) NOT NULL,
    geo_count  INTEGER      NOT NULL,
    created_on TIMESTAMP[]  NOT NULL DEFAULT ARRAY [now()],
    PRIMARY KEY (id)
);

CREATE TABLE sracollector_dev.geo_study
(
    id         SERIAL PRIMARY KEY,
    ncbi_id    INTEGER     NOT NULL,
    request_id VARCHAR     NOT NULL REFERENCES sracollector_dev.request (id) ON UPDATE CASCADE ON DELETE CASCADE,
    gse        VARCHAR(50) NOT NULL,
    UNIQUE (request_id, gse)
);

CREATE TABLE sracollector_dev.sra_project
(
    id           SERIAL PRIMARY KEY,
    srp          VARCHAR(50) NOT NULL,
    geo_study_id INTEGER     NOT NULL REFERENCES sracollector_dev.geo_study (id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (geo_study_id, srp)
);

CREATE TABLE sracollector_dev.sra_run
(
    id             SERIAL PRIMARY KEY,
    srr            VARCHAR(50) NOT NULL,
    sra_project_id INTEGER     NOT NULL REFERENCES sracollector_dev.sra_project (id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (sra_project_id, srr)
);
