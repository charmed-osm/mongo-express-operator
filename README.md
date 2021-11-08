<!-- Copyright 2021 Canonical Ltd.
See LICENSE file for licensing details. -->

# Mongo Express Operator

[![codecov](https://codecov.io/gh/davigar15/charm-mongo-express/branch/main/graph/badge.svg?token=QO02OEH639)](https://codecov.io/gh/davigar15/charm-mongo-express)
[![code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black/tree/main)
[![Run-Tests](https://github.com/davigar15/charm-mongo-express/actions/workflows/ci.yaml/badge.svg)](https://github.com/davigar15/charm-mongo-express/actions/workflows/ci.yaml)

## Description

Mongo express is a web-based MongoDB admin interface written in Node.js, Express.js, and Bootstrap3.

## Usage

The Mongo Express Operator may be deployed using the Juju command line as in

```shell
$ juju add-model mongo-express
$ juju deploy mongodb-k8s  # deploy mongodb operator
$ juju deploy davigar15-mongo-express --channel edge
```

## Accessing the web UI

The IP of the Mongo Express User Interface may be found executing the following Juju command, in the units section.

```shell
$ juju status davigar15-mongo-express/0
```

The web UI will be available at port 8081.

To access the User Interface you need to get the credentials, that can be retrieved by executing the following Juju action.

```shell
$ juju run-action davigar15-mongo-express/0 get-credentials --wait
unit-davigar15-mongo-express-0:
  UnitId: davigar15-mongo-express/0
  id: "14"
  results:
    password: ********************
    username: admin
  status: completed
  timing:
    completed: 2021-11-08 09:48:15 +0000 UTC
    enqueued: 2021-11-08 09:48:11 +0000 UTC
    started: 2021-11-08 09:48:15 +0000 UTC
```

## OCI Images

- [mongo-express](https://hub.docker.com/layers/mongo-express/library/mongo-express/0.54.0/images/sha256-5bf035faae450d68247fb4364dda361bde60f89de185c179a6eda14e2aa731dc?context=explore)

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.
