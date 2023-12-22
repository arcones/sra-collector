FROM python:3.11

ENV DEPS_FOLDER=lambda-dependencies/python

RUN apt update && apt install -y zip

RUN mkdir -p $DEPS_FOLDER

COPY log_support/dist/* $DEPS_FOLDER

CMD cd $DEPS_FOLDER \
    && pip install pysradb -t . \
    && pip install lambda_log_support-0.0.1.tar.gz -t . \
    && cd .. \
    && zip -r9 ../dependencies.zip .
