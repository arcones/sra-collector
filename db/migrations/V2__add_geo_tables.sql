CREATE TABLE GEO_STUDY
(
    ID            SERIAL PRIMARY KEY,
    NCBI_STUDY_ID INTEGER     NOT NULL REFERENCES NCBI_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    GSE           VARCHAR(50) NOT NULL CHECK (GSE LIKE 'GSE%'),
    CREATED_ON    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (NCBI_STUDY_ID, GSE)
);

CREATE TABLE GEO_EXPERIMENT
(
    ID            SERIAL PRIMARY KEY,
    NCBI_STUDY_ID INTEGER     NOT NULL REFERENCES NCBI_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    GSM           VARCHAR(50) NOT NULL CHECK (GSM LIKE 'GSM%'),
    CREATED_ON    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (NCBI_STUDY_ID, GSM)
);

CREATE TABLE GEO_DATA_SET
(
    ID            SERIAL PRIMARY KEY,
    NCBI_STUDY_ID INTEGER     NOT NULL REFERENCES NCBI_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    GDS           VARCHAR(50) NOT NULL CHECK (GDS LIKE 'GDS%'),
    CREATED_ON    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (NCBI_STUDY_ID, GDS)
);

CREATE TABLE GEO_PLATFORM
(
    ID            SERIAL PRIMARY KEY,
    NCBI_STUDY_ID INTEGER     NOT NULL REFERENCES NCBI_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    GPL           VARCHAR(50) NOT NULL CHECK (GPL LIKE 'GPL%'),
    CREATED_ON    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (NCBI_STUDY_ID, GPL)
);
