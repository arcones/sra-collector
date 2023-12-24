CREATE TABLE SRA_PROJECT
(
    ID SERIAL PRIMARY KEY,
    SRP VARCHAR(50) NOT NULL,
    REQUEST_ID VARCHAR REFERENCES REQUEST (
        ID
    ) ON UPDATE CASCADE ON DELETE CASCADE,
    GEO_STUDY_ID INTEGER REFERENCES GEO_STUDY (
        ID
    ) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (GEO_STUDY_ID, REQUEST_ID, SRP)
);