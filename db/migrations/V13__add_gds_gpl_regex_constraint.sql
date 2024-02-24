ALTER TABLE sracollector.geo_data_set
ADD CONSTRAINT check_gsm_regex
CHECK (gds ~ '^GDS[0-9]+$');

ALTER TABLE sracollector_dev.geo_data_set
ADD CONSTRAINT check_gsm_regex
CHECK (gds ~ '^GDS[0-9]+$');

ALTER TABLE sracollector.geo_platform
ADD CONSTRAINT check_gsm_regex
CHECK (gpl ~ '^GPL[0-9]+$');

ALTER TABLE sracollector_dev.geo_platform
ADD CONSTRAINT check_gsm_regex
CHECK (gpl ~ '^GPL[0-9]+$');
