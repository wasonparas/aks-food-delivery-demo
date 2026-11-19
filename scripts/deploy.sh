#!/usr/bin/env bash
set -euo pipefail
: "${ACR_LOGIN_SERVER:?Set ACR_LOGIN_SERVER, for example myuniqueacr.azurecr.io}"
command -v envsubst >/dev/null 2>&1 || { echo "envsubst is required. Install gettext or use Azure Cloud Shell."; exit 1; }
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kubectl apply -f "$ROOT_DIR/kubernetes/namespace.yaml"
kubectl apply -f "$ROOT_DIR/kubernetes/configmap.yaml"
kubectl apply -f "$ROOT_DIR/kubernetes/secrets.yaml"
for manifest in restaurant.yaml order.yaml payment.yaml; do
  envsubst < "$ROOT_DIR/kubernetes/$manifest" | kubectl apply -f -
done
kubectl apply -f "$ROOT_DIR/kubernetes/ingress.yaml"
kubectl apply -f "$ROOT_DIR/kubernetes/hpa.yaml"
echo "Waiting for deployments..."
kubectl rollout status deployment/restaurant-service -n food-demo --timeout=180s
kubectl rollout status deployment/order-service -n food-demo --timeout=180s
kubectl rollout status deployment/payment-service -n food-demo --timeout=180s
kubectl get pods,svc,ingress,hpa -n food-demo
