#!/usr/bin/env bash
set -euo pipefail
: "${ACR_NAME:?Set ACR_NAME, for example export ACR_NAME=myuniqueacr}"
for service in restaurant order payment; do
  case "$service" in
    restaurant) dir=restaurant-service; image=food-restaurant ;;
    order) dir=order-service; image=food-order ;;
    payment) dir=payment-service; image=food-payment ;;
  esac
  echo "Building ${image}:v1 from ${dir}..."
  az acr build --registry "$ACR_NAME" --image "${image}:v1" "$dir"
done
