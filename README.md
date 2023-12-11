# prometheus-adlermanager

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

### Dependencies

The easiest way to manage dependencies for deployment and development is with
pipenv:

- On Debian-based systems: `sudo apt install pipenv`
- On FreeBSD: `pkg install py39-pipenv` (or `devel/py-pipenv` from ports)

The actual dependencies are:

- attrs
- twisted[conch]
- service-identity
- pyyaml
- klein
- jinja2
- markdown

Using Pipenv you can install them for development with:

```sh
pipenv install --dev
```

And for deployment with:

```sh
pipenv install
```

### Configuration

This is done via environment variables, Pipenv will import them from a `.env`
file in the root of this repo.

You can use `dotenv.example` as a base for your settings:
```sh
cp dotenv.example .env
```

**Review** the available settings and their descriptions, particularly you will
want to check `DATA_DIR` and `SSH_KEYS_DIR`.

### SSH access

In order to access AdlerManager via SSH, you will need to add your public SSH
key in `authorized_keys` format to:
`${SSH_KEYS_DIR:-data}/ssh/users/myuser.key`

And give yourself access to the given site, by adding your username to its
`ssh_users` list.

### Running

To run the server for development you can one of the following commands:

```sh
# Using twistd
# https://docs.twisted.org/en/stable/core/howto/basics.html#twistd
pipenv run twistd -ny app.py
# Running as a module
python -m adlermanager
```

And for deployment, you can use [`twistd`][twistd] itself to run the process
in the background or any other daemon watching strategy of your liking
(including e.g. `runit` or `systemd`).
[twistd]: https://docs.twisted.org/en/stable/core/howto/basics.html#twistd

### Using

After that with the defaults you will have the public status web visible in
http://localhost:8080 and the ssh interface in localhost port 2222
which you can access with `ssh -p 2222 USER@localhost`.

## How does it work?

We aim to solve that by using the same source of information to publish
only the desired state/statistics.


### 1. Pretend to be an AlertManager

This is done by accepting `POST` requests from Prometheus on
`/api/v1/alerts`, see
[https://prometheus.io/docs/alerting/clients/](AlertManager) docs.

### 2. Structure Alerts into Services and Components

### 3. Web only lists alerts configured for AdlerManager (public!)

### 4. Keep track of incidents

### 5. Allow for public updates / accountability (via SSH!)
