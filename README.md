# prometheus-adlermanager (Working title)

## What?

A self-hostable status webpage that uses Prometheus alerts to create and
maintain service status and incident tracking / customer information flow.

## Why?

[Prometheus](https://prometheus.io) is awesome!
And AlertManager and Grafana are quite wonderful too, but they expose
too much information.

This project allows you to choose which alerts/statistics get published in
a fashion suitable for user-facing status pages.

## I want it!

### Development environment

You need to have installed pipenv (on debian stable this is `sudo apt install pipenv`), and then, do

```sh
pipenv install --dev
```

you need an `.env` in the root path of this git repo with the suggested env vars

```sh
cat > .env <<END
DATA_DIR=./example-data
SSH_KEYS_DIR=./example-data/ssh
PYTHONPATH=./src
WEB_ENDPOINT="tcp6:interface=\:\::port=8080"
SSH_ENABLED="YES"
END
```

To get working ssh interface, add your ssh public key in the following location `example-data/ssh/users/myuser.key`

Finally, to run the server, use the following command

```sh
pipenv run twistd -ny app.py
```

After that you have the public status web visible in http://localhost:8080 and the ssh interface in localhost port 2222

### Deployment instructions

TODO: Maybe make this available / add deployment instructions.

## How does it work?

We aim to solve that by using the same source of information to publish
only the desired state/statistics.

### 1. Pretend to be an AlertManager

This is done by accepting `POST` requests from Prometheus on
`/api/v1/alerts`, see
[https://prometheus.io/docs/alerting/clients/](AlertManager) docs.

### 2. Filter out non-public Alerts

To mark an Alert as public, whitelist it by using the special labels:
TODO

### 3. Structure Alerts into Services and Components

### 4. Keep track of incidents

### 5. Allow for public updates / accountability
