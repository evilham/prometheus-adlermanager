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
