CREATE TABLE SRA_PROJECT
(
    ID         SERIAL PRIMARY KEY,
    SRP        VARCHAR(50) NOT NULL CHECK (SRP LIKE 'SRP%'),
    CREATED_ON TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE GEO_STUDY_SRA_PROJECT_LINK
(
    GEO_STUDY_ID   INTEGER NOT NULL,
    SRA_PROJECT_ID INTEGER NOT NULL,
    CREATED_ON     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (GEO_STUDY_ID, SRA_PROJECT_ID),
    FOREIGN KEY (GEO_STUDY_ID) REFERENCES GEO_STUDY (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (SRA_PROJECT_ID) REFERENCES SRA_PROJECT (ID) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (GEO_STUDY_ID, SRA_PROJECT_ID)
);
