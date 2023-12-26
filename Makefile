SHELL=/bin/bash

FLYWAY_PASSWORD?='$(shell aws secretsmanager get-secret-value --secret-id rds\!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6 --region eu-central-1 --output json | jq -r .SecretString | jq -r .password)'
DATABASE_PASSWORD?=$(shell urlencode $(FLYWAY_PASSWORD))

truncate-db-tables:
	@cd utils/truncate_tables && \
	psql "postgresql://sracollector:$(DATABASE_PASSWORD)@sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com/sracollector" -f truncate_tables.sql

remove-db-tables:
	@cd utils/remove_tables && \
	psql "postgresql://sracollector:$(DATABASE_PASSWORD)@sracollector.cgaqaljpdpat.eu-central-1.rds.amazonaws.com/sracollector" -f remove_tables.sql

db-migrations:
	@docker run --rm -v $(shell pwd)/db/migrations:/flyway/sql -v $(shell pwd)/db:/flyway/conf -e FLYWAY_PASSWORD=$(FLYWAY_PASSWORD) flyway/flyway migrate

update-diagram:
	@rm -rf tmp/diagrams && mkdir -p tmp/diagrams && \
	docker run -v $(shell pwd)/tmp/diagrams:/output -v $(shell pwd)/schemaspy.properties:/schemaspy.properties schemaspy/schemaspy -p $(FLYWAY_PASSWORD) && \
	cp tmp/diagrams/diagrams/summary/relationships.real.large.png db/diagram.png

clean-queues:
	cd utils/purge_queues && \
	pip install -r requirements.txt && \
	python ./purge-queues.py

clean-builds:
	./utils/clean_temp/clean_temp.sh

build-lambda-dependencies: clean-builds
	cd infra/lambdas/docker && \
	docker build --tag=lambda-dependencies . && \
	docker create --name deps lambda-dependencies:latest && \
	docker cp deps:dependencies.zip .. && \
	docker rm deps

init-infra: clean-queues build-lambda-dependencies
	 cd infra && terraform init ; cd ..

plan-infra:
	 cd infra && terraform plan ; cd ..

build-infra:
	cd infra && terraform apply --auto-approve ; cd ..
