all: fmt test

fmt:
	pipenv run isort -y
	pipenv run black .

test:
	pipenv run mypy .
	pipenv run pytest

test-watch:
	find . -name '*py' -or -name '*html' -or -name Pipfile.lock | entr -r -c make test
