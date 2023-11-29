#!/bin/sh

SITE="localhost"
SERVICE=dcl
COMPONENT=network
ALERTNAME=MockAlert

TOKEN=$(cat data/sites/${SITE}/tokens.txt | head -n1)
ADLERMANAGER="http://localhost:8080"

#TODO token
curl -X POST \
     -H "Authorization: Bearer ${TOKEN}" \
     localhost:8080/api/v1/alerts \
     -d@- <<EOF
[
  {
    "labels": {
      "adlermanager": "${SITE}",
      "alertname": "${ALERTNAME}",
      "service":   "${SERVICE}",
      "component": "${COMPONENT}",
      "severity":  "error"
    },
    "annotations": {
      "summary": "Hello world!",
      "description": "This is a mock alert"
    }
  }
]
EOF
