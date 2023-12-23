.EXPORT_ALL_VARIABLES:
SHELL=/bin/bash

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

db-migrations:
	docker run --rm -v $(shell pwd)/db/migrations:/flyway/sql -v $(shell pwd)/db:/flyway/conf  -e FLYWAY_PASSWORD flyway/flyway migrate
