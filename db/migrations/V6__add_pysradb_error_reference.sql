CREATE TABLE sracollector.pysradb_error_reference
(
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    operation varchar(50) NOT NULL
);

INSERT INTO sracollector.pysradb_error_reference (operation, name)
VALUES ('gse_to_srp','ATTRIBUTE_ERROR'),
('gse_to_srp','VALUE_ERROR'),
('gse_to_srp','KEY_ERROR'),
('srp_to_srr','ATTRIBUTE_ERROR'),
('gse_to_srp','NOT_FOUND'),
('srp_to_srr','NOT_FOUND');
;

CREATE TABLE sracollector_dev.pysradb_error_reference
(
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    operation varchar(50) NOT NULL
);

INSERT INTO sracollector_dev.pysradb_error_reference (operation, name)
VALUES ('gse_to_srp','ATTRIBUTE_ERROR'),
('gse_to_srp','VALUE_ERROR'),
('gse_to_srp','KEY_ERROR'),
('srp_to_srr','ATTRIBUTE_ERROR'),
('gse_to_srp','NOT_FOUND'),
('srp_to_srr','NOT_FOUND');
