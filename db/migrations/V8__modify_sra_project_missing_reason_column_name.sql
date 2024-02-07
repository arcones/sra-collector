ALTER TABLE sracollector.sra_project_missing RENAME
COLUMN reason TO pysradb_error_reference_id;
ALTER TABLE sracollector_dev.sra_project_missing RENAME
COLUMN reason TO pysradb_error_reference_id;
