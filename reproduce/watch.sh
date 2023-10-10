#!/bin/bash

REPRO_WATCH_FILES=$(awk '/^watch = \[/ {gsub(/^watch = \[|\]$/, "", $0); n = split($0, arr, ","); result = ""; for (i = 1; i <= n; i++) { gsub(/^ *"|" *$|^ *| *$/, "", arr[i]); if (arr[i] != "") result = (result == "" ? arr[i] : result "," arr[i]); } print result;}' "${REPRODUCEWORKDIR}/config.toml")
#docker run --rm -i -v ${HOSTWORKDIR}:/home/jovyan reproduceworkdev nbdev_export && nbdev_readme && nbdev_preview
docker-compose -f reproduce/docker-compose-reproduce.yml up tex-prepare
cp -r ${HOSTWORKDIR}/${REPROWORKDIR}/tmp/document/latex/report.pdf ${HOSTWORKDIR}/document/report.pdf
docker-compose -f reproduce/docker-compose-reproduce.yml up tex-compile
cp -r /usr/src/app/${REPROWORKDIR}/tmp/document/latex/report.pdf /usr/src/app/document/report.pdf

# delete files in