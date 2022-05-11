FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

VOLUME /meshmash

ENV MESHMASH_STATE_PATH /meshmash/state.json

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev

COPY . .

CMD poetry run gunicorn meshmash.http:app -w 4 --capture-output --access-logfile - --log-file - -b 0.0.0.0:8000
