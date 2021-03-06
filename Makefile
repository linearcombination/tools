build:
	docker-compose build

build-no-cache:
	docker-compose build --no-cache

up:
	docker-compose up -d

# Deal with instability with upstream translations.json
use-stable-translations-json:
ifeq ($(TRANSLATIONS_JSON_FROM_GIT),1)
	git checkout working/temp/translations.json
	touch working/temp/translations.json
else
	rm working/temp/translations.json
endif

server: up
	docker-compose run  api

# Run a local server outside Docker
local-server:
	uvicorn document.entrypoints.app:app --reload --host "127.0.0.1" --port "8000" --app-dir "./src/"

test: up
	docker-compose run --rm --no-deps --entrypoint=pytest api /tests/unit /tests/integration /tests/e2e

unit-tests: up use-stable-translations-json
	docker-compose run --rm --no-deps --entrypoint=pytest api /tests/unit

integration-tests: up use-stable-translations-json
	docker-compose run --rm --no-deps --entrypoint=pytest api /tests/integration

e2e-tests: up use-stable-translations-json
	docker-compose run --rm --no-deps --entrypoint=pytest api /tests/e2e

down:
	docker-compose down --remove-orphans

mypy:
	mypy src/document/*.py
	mypy src/document/**/*.py
	mypy tests/*.py
	mypy tests/**/*.py

pyicontract-lint:
	pyicontract-lint --dont_panic ./src/document/domain
	pyicontract-lint --dont_panic ./src/document/utils
	pyicontract-lint --dont_panic ./src/document/entrypoints

all: down build up test

all-plus-linting: mypy pyicontract-lint down build up test
