FROM python:3.11

ENV LOG_LIB_FOLDER=log_support
ENV DEPS_FOLDER=lambda-dependencies/python

RUN apt update && apt install -y zip && pip install wheel setuptools build

COPY $LOG_LIB_FOLDER $LOG_LIB_FOLDER

RUN cd $LOG_LIB_FOLDER && python -m build

RUN mkdir -p $DEPS_FOLDER

RUN cd $DEPS_FOLDER \
    && pip install pysradb -t . \
    && pip install /$LOG_LIB_FOLDER/dist/lambda_log_support-0.0.1-py3-none-any.whl -t . \
    && cd .. \
    && zip -r9 ../dependencies.zip .
