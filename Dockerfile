FROM --platform=linux/amd64 python:3.11-bookworm

ARG USERNAME=containeruser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

COPY app.py /app/app.py
COPY app_config.py /app/app_config.py
COPY aad.config.json /app/aad.config.json
COPY requirements.txt /app/requirements.txt
COPY static /app/static
COPY templates /app/templates

WORKDIR /app

RUN mkdir /app/flask_session \
    && pip3 install -r requirements.txt \
    && groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && chown -R 1000:1000 /app/flask_session

USER $USERNAME

EXPOSE 8080

ENTRYPOINT [ "python3", "/app/app.py" ]