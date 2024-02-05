ALTER TABLE sracollector_dev.geo_study
DROP CONSTRAINT geo_study_request_id_fkey;
ALTER TABLE sracollector_dev.geo_study
ADD CONSTRAINT geo_study_request_id_fkey FOREIGN KEY (request_id)
REFERENCES sracollector_dev.request (id);

ALTER TABLE sracollector_dev.sra_project
DROP CONSTRAINT sra_project_geo_study_id_fkey;
ALTER TABLE sracollector_dev.sra_project
ADD CONSTRAINT sra_project_geo_study_id_fkey FOREIGN KEY (geo_study_id)
REFERENCES sracollector_dev.geo_study (id);

ALTER TABLE sracollector_dev.sra_run
DROP CONSTRAINT sra_run_sra_project_id_fkey;
ALTER TABLE sracollector_dev.sra_run
ADD CONSTRAINT sra_run_sra_project_id_fkey FOREIGN KEY (sra_project_id)
REFERENCES sracollector_dev.sra_project (id);
