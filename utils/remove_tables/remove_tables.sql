DROP TABLE sracollector.request CASCADE;
DROP TABLE sracollector.geo_study CASCADE;
DROP TABLE sracollector.sra_project CASCADE;
DROP TABLE sracollector.sra_run CASCADE;
DROP TABLE sracollector.sra_project_missing CASCADE;
DROP TABLE sracollector.pysradb_error_reference CASCADE;
DELETE FROM flyway_schema_history WHERE version IS NOT NULL;
