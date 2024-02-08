FROM python:3.11

ENV DB_CONNECTION_LIB_FOLDER=postgres_connection
ENV DB_CONNECTION_LIB_VERSION=0.0.2

ENV PARAMS_LIB_FOLDER=env_params
ENV PARAMS_LIB_VERSION=0.0.1

ENV DEPS_FOLDER=lambda-dependencies/python

RUN apt update && apt install -y zip && pip install wheel setuptools build

COPY ${DB_CONNECTION_LIB_FOLDER} ${DB_CONNECTION_LIB_FOLDER}
COPY ${PARAMS_LIB_FOLDER} ${PARAMS_LIB_FOLDER}

RUN cd ${DB_CONNECTION_LIB_FOLDER} && python -m build
RUN cd ${PARAMS_LIB_FOLDER} && python -m build

RUN mkdir -p ${DEPS_FOLDER}

RUN cd ${DEPS_FOLDER} \
    && pip install pysradb psycopg2-binary -t . \
    && cd .. \
    && zip -r9 ../dependencies.zip .

RUN cd ${DEPS_FOLDER} \
    && pip install /${DB_CONNECTION_LIB_FOLDER}/dist/${DB_CONNECTION_LIB_FOLDER}-${DB_CONNECTION_LIB_VERSION}-py3-none-any.whl -t . \
    && cd .. \
    && zip -ur9 ../dependencies.zip .

RUN cd ${DEPS_FOLDER} \
    && pip install /${PARAMS_LIB_FOLDER}/dist/${PARAMS_LIB_FOLDER}-${PARAMS_LIB_VERSION}-py3-none-any.whl -t . \
    && cd .. \
    && zip -ur9 ../dependencies.zip .
