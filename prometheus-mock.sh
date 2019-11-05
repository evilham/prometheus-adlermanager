#!/bin/sh

SITE="status.lab.ungleich.ch"
SERVICE=dcl
COMPONENT=network
ALERTNAME=MockAlert

TOKEN=$(cat data/sites/${SITE}/tokens.txt | head -n1)
ADLERMANAGER="https://${SITE}"

#TODO token
curl -X POST \
     -H "Authorization: Bearer ${TOKEN}" \
     ${ADLERMANAGER}/api/v1/alerts \
     -d@- <<EOF
[
  {
    "labels": {
      "alertname": "${ALERTNAME}",
      "service":   "${SERVICE}",
      "component": "${COMPONENT}",
      "severity":  "error"
    },
    "annotations": {
      "summary": "This is a mock alert. Hello world!"
    }
  }
]
EOF
