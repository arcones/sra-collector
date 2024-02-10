ALTER TABLE sracollector.geo_study
ADD CONSTRAINT check_gse_regex
CHECK (gse ~ '^GSE[0-9]+$');

ALTER TABLE sracollector_dev.geo_study
ADD CONSTRAINT check_gse_regex
CHECK (gse ~ '^GSE[0-9]+$');

ALTER TABLE sracollector.geo_experiment
ADD CONSTRAINT check_gsm_regex
CHECK (gsm ~ '^GSM[0-9]+$');

ALTER TABLE sracollector_dev.geo_experiment
ADD CONSTRAINT check_gse_regex
CHECK (gsm ~ '^GSM[0-9]+$');


ALTER TABLE sracollector.sra_project
ADD CONSTRAINT check_srp_regex
CHECK (srp ~ '^SRP[0-9]+$');

ALTER TABLE sracollector_dev.sra_project
ADD CONSTRAINT check_srp_regex
CHECK (srp ~ '^SRP[0-9]+$');

ALTER TABLE sracollector.sra_run
ADD CONSTRAINT check_srr_regex
CHECK (srr ~ '^SRR[0-9]+$');

ALTER TABLE sracollector_dev.sra_run
ADD CONSTRAINT check_srr_regex
CHECK (srr ~ '^SRR[0-9]+$');
