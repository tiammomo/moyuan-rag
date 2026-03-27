ARG ELASTICSEARCH_BASE_IMAGE=docker.m.daocloud.io/library/elasticsearch:7.17.10
FROM ${ELASTICSEARCH_BASE_IMAGE}

COPY backend/docker/elasticsearch/elasticsearch-analysis-ik-7.17.10.zip /tmp/elasticsearch-analysis-ik-7.17.10.zip

RUN bin/elasticsearch-plugin install --batch file:///tmp/elasticsearch-analysis-ik-7.17.10.zip \
    && rm -f /tmp/elasticsearch-analysis-ik-7.17.10.zip
