#! /bin/bash

set -euxo pipefail

TAG="sha-${1}"

charmcraft pack

juju refresh \
    ubuntu-metrics \
    --model=desktop \
    --path=./ubuntu-metrics_ubuntu-22.04-amd64.charm \
    --force-units \
    --resource "image=ghcr.io/tim-hm/ubuntu-report:$TAG"
