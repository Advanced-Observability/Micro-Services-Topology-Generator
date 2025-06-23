#! /bin/bash

set -euo pipefail

if ! command -v go
then
    echo "Cannot find \"go\" command"
    exit 1
fi

go get -u .
go mod tidy
CGO_ENABLED=0 go build -tags netgo -o service
