#! /bin/bash

juju deploy \
    ./ubuntu-reportd_ubuntu-22.04-amd64.charm \
    --resource image=ghcr.io/tim-hm/ubuntu-report:dev
