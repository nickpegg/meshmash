FROM python:3.8-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

VOLUME /meshmash

ENV MESHMASH_STATE_PATH /meshmash/state.json

RUN pip install --no-cache-dir pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system

COPY . .

CMD gunicorn meshmash.http:app -w 4 --capture-output --access-logfile - --log-file - -b 0.0.0.0:8000
