SHELL=/bin/bash

FLYWAY_PASSWORD?='$(shell aws secretsmanager get-secret-value --secret-id rds\!db-3ce19e76-772e-4b32-b2b1-fc3e6d54c7f6 --region eu-central-1 --output json | jq -r .SecretString | jq -r .password)'
DATABASE_PASSWORD?=$(shell urlencode $(FLYWAY_PASSWORD))
DB_CONNECTION_LIB_VERSION=0.0.5
SQS_HELPER_LIB_VERSION=0.0.1
S3_HELPER_LIB_VERSION=0.0.1

db-migrations-integration-test:
	@docker run --rm -v $(shell pwd)/db/migrations:/flyway/sql -v $(shell pwd)/db/conf-integration-test:/flyway/conf -e FLYWAY_PASSWORD=$(FLYWAY_PASSWORD) flyway/flyway clean migrate

db-migrations-prod:
	@docker run --rm -v $(shell pwd)/db/migrations:/flyway/sql -v $(shell pwd)/db/conf-prod:/flyway/conf -e FLYWAY_PASSWORD=$(FLYWAY_PASSWORD) flyway/flyway migrate

db-migrations-unit-test:
	@docker run --rm -v $(shell pwd)/db/migrations:/flyway/sql -v $(shell pwd)/db/conf-unit-test:/flyway/conf -v $(shell pwd)/tmp/test-db:/db  flyway/flyway clean migrate
	sudo chown $(shell whoami):$(shell whoami) tmp/test-db/test.db.mv.db

update-diagram:
	@rm -rf tmp/diagrams && mkdir -p tmp/diagrams && chmod 777 tmp/diagrams && \
	docker run -v $(shell pwd)/tmp/diagrams:/output -v $(shell pwd)/schemaspy.properties:/schemaspy.properties schemaspy/schemaspy -p $(FLYWAY_PASSWORD) && \
	cp tmp/diagrams/diagrams/summary/relationships.real.large.png db/diagram.png

purge-queues:
	cd utils/purge_queues && \
	pip install -r requirements.txt && \
	python ./purge-queues.py

reset-alarms:
	cd utils/reset_alarms && \
	pip install -r requirements.txt && \
	python ./reset-alarms.py

clean-os-indices:
	curl -w "\n%{http_code}" --location --request DELETE 'https://search-sracollector-opensearch-bbcrkwlcfb2fjb7psquiefeg2a.eu-central-1.es.amazonaws.com/cwl-sra-collector-*' \
		--header 'Content-Type: application/json' \
		--data '{ "query": { "match_all": {} } }'

clean-builds:
	./utils/clean_temp/clean_temp.sh

build-lambda-dependencies: clean-builds
	cd infra/lambdas/docker && \
	docker build --tag=lambda-dependencies . && \
	docker create --name deps lambda-dependencies:latest && \
	docker cp deps:dependencies.zip .. && \
	docker rm deps

init-infra: purge-queues reset-alarms
	cd infra && terraform init -upgrade; cd ..

plan-infra:
	cd infra && terraform plan ; cd ..

build-infra:
	cd infra && terraform plan -detailed-exitcode -out terraform.plan; \
	INFRA_CHANGES=$$?; \
	if [ $$INFRA_CHANGES = "2" ]; then\
		cd lambdas/docker && \
		docker build --tag=lambda-dependencies . && \
		docker create --name deps lambda-dependencies:latest && \
		docker cp deps:dependencies.zip .. && \
		docker rm deps && \
		cd ../.. && \
		terraform apply --auto-approve terraform.plan; cd ..;\
	else \
		echo "There are no infra changes" && cd ..; \
	fi

xs-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "multiple sclerosis AND Astrocyte-produced HB-EGF and WGBS" }'

s-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "stroke AND single cell rna seq AND musculus" }'

m-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "asthma AND children AND rna seq" }'

l-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "arabidopsis thaliana AND rna seq AND zea mays" }'

xl-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "multiple sclerosis AND rna seq" }'

max-sra-collector-request:
	curl -w "\n%{http_code}" --location --request POST 'https://sra-collector.martaarcones.net/query-submit' \
		--header 'Content-Type: application/json' \
		--data '{ "ncbi_query": "cancer AND mus musculus AND children" }'

build-unit-tests-dependencies: db-migrations-unit-test
	cd tests/unit_tests && pip install -r requirements.txt
	cd infra/lambdas/docker/db_connection && python -m build && pip install dist/db_connection-$(DB_CONNECTION_LIB_VERSION)-py3-none-any.whl --force-reinstall
	cd infra/lambdas/docker/sqs_helper && python -m build && pip install dist/sqs_helper-$(SQS_HELPER_LIB_VERSION)-py3-none-any.whl --force-reinstall
	cd infra/lambdas/docker/s3_helper && python -m build && pip install dist/s3_helper-$(S3_HELPER_LIB_VERSION)-py3-none-any.whl --force-reinstall


integration-tests-server: build-lambda-dependencies
	cd tests/integration_tests && pip install -r requirements.txt
	cd infra && sam local start-lambda --debug --skip-pull-image --warm-containers LAZY --hook-name terraform --env-vars ../tests/integration_tests/environments.json
