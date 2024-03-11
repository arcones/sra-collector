CREATE TABLE PYSRADB_ERROR_REFERENCE
(
    ID        SERIAL PRIMARY KEY,
    NAME      VARCHAR(50) NOT NULL,
    OPERATION VARCHAR(50) NOT NULL,
    CREATED_ON TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO PYSRADB_ERROR_REFERENCE (OPERATION, NAME)
VALUES ('gse_to_srp', 'ATTRIBUTE_ERROR'),
       ('gse_to_srp', 'VALUE_ERROR'),
       ('gse_to_srp', 'KEY_ERROR'),
       ('gse_to_srp', 'NOT_FOUND'),

       ('srp_to_srr', 'ATTRIBUTE_ERROR'),
       ('srp_to_srr', 'NOT_FOUND'),
       ('srp_to_srr', 'TYPE_ERROR')
;
