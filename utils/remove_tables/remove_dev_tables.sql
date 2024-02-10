DROP TABLE sracollector_dev.request CASCADE;
DROP TABLE sracollector_dev.geo_study CASCADE;
DROP TABLE sracollector_dev.sra_project CASCADE;
DROP TABLE sracollector_dev.sra_run CASCADE;
DROP TABLE sracollector_dev.sra_project_missing CASCADE;
DROP TABLE sracollector_dev.pysradb_error_reference CASCADE;
DELETE FROM flyway_schema_history WHERE version IS NOT NULL;
