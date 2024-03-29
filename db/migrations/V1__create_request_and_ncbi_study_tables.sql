CREATE TABLE REQUEST
(
    ID         VARCHAR UNIQUE,
    QUERY      VARCHAR(500) NOT NULL,
    GEO_COUNT  INTEGER      NOT NULL,
    CREATED_ON TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID)
);

CREATE TABLE NCBI_STUDY
(
    ID         SERIAL PRIMARY KEY,
    NCBI_ID    INTEGER NOT NULL,
    REQUEST_ID VARCHAR NOT NULL REFERENCES REQUEST (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    CREATED_ON TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (REQUEST_ID, NCBI_ID)
);
