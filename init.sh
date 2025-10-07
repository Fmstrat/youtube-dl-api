#!/bin/sh

if [ "${UPDATE_TO_MASTER}" = "true" ]; then
    youtube-dl --update-to master
fi

/youtube-dl-api.py $@