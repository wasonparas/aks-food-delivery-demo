#!/usr/bin/env bash
set -euo pipefail
: "${INGRESS_IP:?Set INGRESS_IP to the external IP of ingress-nginx-controller}"
BASE_URL="http://${INGRESS_IP}"
echo "Checking Restaurant service..."
curl --fail --silent --show-error "${BASE_URL}/restaurants" >/dev/null
echo "Creating a demo order..."
curl --fail --silent --show-error \
  -X POST "${BASE_URL}/orders" \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":"rest-001","item":"Fish and chips","amount":24.50,"customer":"AKL Demo User"}'
echo
echo "Smoke test completed successfully."
