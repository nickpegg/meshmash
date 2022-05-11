all: fmt test

fmt:
	poetry run isort meshmash tests
	poetry run black .

test:
	poetry run mypy .
	poetry run pytest

test-docker:
	docker-compose --file docker-compose.test.yml build
	docker-compose --file docker-compose.test.yml run sut

test-watch:
	find . -name '*py' -or -name '*html' -or -name poetry.lock | entr -r -c make test
