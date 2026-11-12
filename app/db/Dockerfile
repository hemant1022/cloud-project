FROM postgres:16-alpine

COPY init.sql /docker-entrypoint-initdb.d/01_init.sql
COPY seed /docker-entrypoint-initdb.d/seed
