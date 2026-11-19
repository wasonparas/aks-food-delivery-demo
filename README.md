# AKS Food Delivery Demo

A Git-ready, end-to-end Python Flask microservices application for learning Azure Kubernetes Service (AKS). It contains Restaurant, Order and Payment services. The Order service calls Restaurant and Payment over Kubernetes ClusterIP DNS. Payments are simulated only; no real payment provider or money movement is used.

## Repository layout

```text
aks-food-delivery-demo/
├── restaurant-service/       # Flask app + Dockerfile
├── order-service/            # Flask app + Dockerfile
├── payment-service/          # Flask app + Dockerfile
├── kubernetes/               # Namespace, Deployments, Services, Ingress, HPA
├── scripts/                  # ACR build, AKS deploy and smoke-test scripts
├── .gitignore
└── README.md
```

## Put this project in your Git repository

Download and extract the ZIP, then run these commands from the extracted project directory. Create an empty repository in GitHub first (do not initialise it with a README, licence or `.gitignore`).

```bash
git init
git add .
git commit -m "Initial AKS food delivery demo"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/aks-food-delivery-demo.git
git push -u origin main
```

To use it on another machine or in Azure Cloud Shell:

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/aks-food-delivery-demo.git
cd aks-food-delivery-demo
```

Replace `<YOUR_GITHUB_USERNAME>` with your GitHub username and use your organisation's approved Git authentication method.

## Architecture

- `restaurant-service` — list restaurants and retrieve a restaurant by ID (port 8080)
- `order-service` — create an order and orchestrate Restaurant + Payment calls (port 8081)
- `payment-service` — validates a demo API key and returns a simulated approval (port 8082)
- Kubernetes Ingress — routes `/restaurants`, `/orders` and `/payments` through NGINX
- HPA — scales Order Service from 2 to 5 replicas at a 60% average CPU target

## Prerequisites

- An Azure subscription with permission to create a resource group, AKS cluster and ACR
- Azure CLI (`az`), `kubectl`, Helm, and `envsubst` (Azure Cloud Shell includes the common tools)
- A supported AKS Kubernetes version

## 1. Set variables and create Azure resources

Run in Azure Cloud Shell (Bash). Choose globally unique names containing only lowercase letters and numbers for ACR.

```bash
az login
az account set --subscription <SUBSCRIPTION_ID>

export LOCATION=australiaeast
export RESOURCE_GROUP=rg-aks-food-demo
export AKS_NAME=aks-food-demo
export ACR_NAME=<globally-unique-acr-name>

az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic

az aks create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_NAME" \
  --location "$LOCATION" \
  --node-count 2 \
  --node-vm-size Standard_D2s_v5 \
  --generate-ssh-keys \
  --attach-acr "$ACR_NAME"

az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_NAME"
kubectl get nodes
export ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
echo "$ACR_LOGIN_SERVER"
```

If the selected VM size is unavailable in your region or subscription, choose an available AKS-supported size. The cluster and ACR incur Azure charges; delete them when finished.

## 2. Build and push the three images

From the project root directory:

```bash
export ACR_NAME=<same-acr-name>
chmod +x scripts/*.sh
./scripts/build-and-push.sh
az acr repository list --name "$ACR_NAME" -o table
```

`az acr build` builds in Azure, so a local Docker daemon is not required.

## 3. Install NGINX Ingress Controller

This demo uses the community ingress-nginx Helm chart and the `nginx` IngressClass. This is a learning setup; for production, select an ingress option supported by your AKS version and your organisation's security and support requirements.

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.replicaCount=2

kubectl get svc -n ingress-nginx -w
```

Wait for the `ingress-nginx-controller` Service to receive an external IP. Press Ctrl+C after it appears.

## 4. Configure the demo secret

Edit `kubernetes/secrets.yaml` and replace `replace-this-demo-key` with a non-production demo value. This file is committed as an example, so do not put real credentials in Git. For production, use Azure Key Vault and the Secrets Store CSI Driver / workload identity integration.

## 5. Deploy the application

From the project root:

```bash
export ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
./scripts/deploy.sh
```

Or apply the manifests manually after exporting `ACR_LOGIN_SERVER`; the deployment script uses `envsubst` to substitute the image registry in the three Deployment manifests.

## 6. Test the application

Get the Ingress IP:

```bash
kubectl get ingress -n food-demo
kubectl get svc ingress-nginx-controller -n ingress-nginx
export INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "$INGRESS_IP"
```

If DNS is not configured, send the Host header (the Ingress rule has no hostname):

```bash
curl "http://${INGRESS_IP}/restaurants"
curl "http://${INGRESS_IP}/restaurants/rest-001"

curl -i -X POST "http://${INGRESS_IP}/orders" \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":"rest-001","item":"Fish and chips","amount":24.50,"customer":"AKL Demo User"}'
```

A successful order returns HTTP 201 with `status: CONFIRMED` and a simulated payment result. A nonexistent restaurant ID should return HTTP 404.

Run the bundled smoke test:

```bash
export INGRESS_IP="$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
./scripts/smoke-test.sh
```

## 7. Useful demo commands

```bash
# View all application resources
kubectl get all,ingress,hpa -n food-demo

# Watch pods while scaling or deleting one
kubectl get pods -n food-demo -w

# Demonstrate self-healing (Deployment recreates the deleted pod)
kubectl delete pod -n food-demo -l app=restaurant-service --wait=false
kubectl get pods -n food-demo -w

# Demonstrate manual scaling
kubectl scale deployment/order-service -n food-demo --replicas=4
kubectl get deployment/order-service -n food-demo

# Inspect autoscaling (CPU metrics may take a minute to appear)
kubectl get hpa -n food-demo -w
kubectl top pods -n food-demo

# Logs and rollout status
kubectl logs -n food-demo deployment/order-service --tail=100
kubectl rollout status deployment/order-service -n food-demo

# Demonstrate a rolling update after building/pushing a new image tag
# Update the image tag in kubernetes/order.yaml, redeploy, then:
kubectl rollout history deployment/order-service -n food-demo
kubectl rollout undo deployment/order-service -n food-demo
```

The HPA controls the replica count, so a manual `kubectl scale` can be reconciled by the HPA. For a clean scaling demonstration, temporarily remove the HPA (`kubectl delete hpa order-service -n food-demo`) before manually scaling, then reapply it (`kubectl apply -f kubernetes/hpa.yaml`). CPU load testing is not included by default; generate controlled load only in a non-production demo cluster.

## 8. Troubleshooting

- `ImagePullBackOff`: verify image names/tags in ACR, `ACR_LOGIN_SERVER`, and that AKS has pull permission (`az aks check-acr -g "$RESOURCE_GROUP" -n "$AKS_NAME" --acr "$ACR_LOGIN_SERVER"`).
- Ingress has no address: check `kubectl get pods,svc -n ingress-nginx` and Azure load balancer provisioning events.
- HPA shows `<unknown>`: check `kubectl top nodes` and `kubectl top pods -n food-demo`; wait for metrics collection and confirm resource requests are set.
- Order returns `502`: inspect `kubectl logs deployment/order-service -n food-demo` and verify the restaurant/payment Services and endpoints.
- Secret mismatch: the `PAYMENT_API_KEY` value must be identical in the Order and Payment environment; both deployments read the same Kubernetes Secret.

## 9. Clean up Azure resources

```bash
az group delete --name "$RESOURCE_GROUP" --yes --no-wait
```

This removes the AKS cluster, ACR and other resources in that resource group. Confirm the resource group contains no resources you need before deleting it.

## Security and scope notes

- This is an intermediate learning/demo project, not a production reference architecture.
- The payment service simulates approval and never charges a card.
- The example Secret is for a sandbox only. Kubernetes Secrets are base64-encoded at rest unless encryption at rest is configured; use Key Vault for real credentials.
- Ingress is HTTP-only in this starter. Configure TLS, DNS, network policies, managed identities/workload identity, image scanning, and centralised monitoring before production use.
- The services use in-memory static restaurant data and do not persist orders.
