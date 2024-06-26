CREATE TABLE SRA_PROJECT
(
    ID           SERIAL PRIMARY KEY,
    SRP          VARCHAR(50)    NOT NULL CHECK (SRP LIKE 'SRP%'),
    GEO_STUDY_ID INTEGER UNIQUE NOT NULL REFERENCES GEO_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    CREATED_ON   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (GEO_STUDY_ID, SRP)
);

CREATE TABLE SRA_RUN
(
    ID             SERIAL PRIMARY KEY,
    SRR            VARCHAR(50) NOT NULL CHECK (SRR LIKE 'SRR%'),
    SRA_PROJECT_ID INTEGER     NOT NULL REFERENCES SRA_PROJECT (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    CREATED_ON     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (SRA_PROJECT_ID, SRR)
);
