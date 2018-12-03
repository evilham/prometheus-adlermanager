#!/bin/sh

SITE="status.lab.ungleich.ch"
SERVICE=dcl
COMPONENT=network
ALERTNAME=MockAlert
PORT=9000

TOKEN=$(cat data/sites/$SITE/tokens.txt | head -n1)

#TODO token
curl -X POST \
     -H "Authorization: Bearer $TOKEN" \
     http://localhost:9000/api/v1/alerts \
     -d@- <<EOF
[
  {
    "labels": {
      "alertname": "$ALERTNAME",
      "service":   "$SERVICE",
      "component": "$COMPONENT",
      "severity":  "error"
    },
    "annotations": {
      "summary": "This is a mock alert. Hello world!"
    }
  },
  ...
]
EOF
