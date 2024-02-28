#! /bin/bash

set -uexo pipefail

charmcraft pack

juju refresh \
    ubuntu-reportd \
    --path=./ubuntu-reportd_ubuntu-22.04-amd64.charm \
    --force-units \
    --resource image=ghcr.io/tim-hm/ubuntu-report:sha-69ce01e