# AKS Food Delivery Demo

A Git-ready, end-to-end Python Flask microservices application for learning Azure Kubernetes Service (AKS).

The project contains three microservices:

- **Restaurant Service** – provides restaurant information.
- **Order Service** – creates orders and orchestrates Restaurant and Payment services.
- **Payment Service** – simulates payment approval.

The Order service communicates with Restaurant and Payment through Kubernetes ClusterIP Services and internal Kubernetes DNS.

> **Important:** Payments are simulated only. No real payment provider is integrated and no money is transferred.

---

## 1. Repository layout

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

## 2. Architecture

| Component | Description | Port |
|---|---|---:|
| Restaurant Service | Lists restaurants and retrieves restaurant details | 8080 |
| Order Service | Creates orders and calls Restaurant and Payment | 8081 |
| Payment Service | Validates demo API key and simulates payment approval | 8082 |
| NGINX Ingress | Routes external HTTP requests to application services | 80 / 443 |

### Request flow

```text
                    External Client
                          |
                          |
                Azure Load Balancer
                          |
                     Public IP
                          |
                          |
                 NGINX Ingress
                          |
              +-----------+-----------+
              |                       |
        /restaurants                /orders
              |                       |
              v                       v
      Restaurant Service       Order Service
              ^                       |
              |                       |
              +-----------------------+
                                      |
                                      v
                              Payment Service
                              (Simulated)
```

### Kubernetes configuration

- Namespace: `food-demo`
- Ingress namespace: `ingress-nginx`
- Ingress controller: NGINX
- Ingress routes: `/restaurants`, `/orders`, `/payments`
- Services: ClusterIP
- Order Service HPA: 2–5 replicas
- HPA CPU target: 60%

---

## 3. Put this project in your Git repository

Create an empty GitHub repository first. Do not initialise it with a README, licence or `.gitignore`.

From the extracted project directory:

```bash
git init
git add .
git commit -m "Initial AKS food delivery demo"
git branch -M main

git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/aks-food-delivery-demo.git

git push -u origin main
```

Replace `<YOUR_GITHUB_USERNAME>` with your GitHub username and use your organisation's approved Git authentication method.

### Clone the project on another machine or in Azure Cloud Shell

```bash
git clone https://github.com/<YOUR_GITHUB_USERNAME>/aks-food-delivery-demo.git

cd aks-food-delivery-demo
```

---

## 4. Prerequisites

You need:

- An Azure subscription with permission to create a resource group, AKS cluster and Azure Container Registry (ACR).
- Azure CLI (`az`).
- `kubectl`.
- Helm.
- `envsubst`.
- Git.
- `curl`.

Azure Cloud Shell includes many of these tools.

---

## 5. Set variables and create Azure resources

Run the following commands in Azure Cloud Shell (Bash).

Choose globally unique lowercase names containing only letters and numbers for ACR.

```bash
az login

az account set --subscription <SUBSCRIPTION_ID>

export LOCATION=australiaeast
export RESOURCE_GROUP=rg-aks-food-demo
export AKS_NAME=aks-food-demo
export ACR_NAME=<globally-unique-acr-name>
```

Create the resource group:

```bash
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"
```

Create Azure Container Registry:

```bash
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic
```

Create AKS:

```bash
az aks create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_NAME" \
  --location "$LOCATION" \
  --node-count 2 \
  --node-vm-size Standard_D2s_v5 \
  --generate-ssh-keys \
  --attach-acr "$ACR_NAME"
```

If the selected VM size is unavailable in your region or subscription, choose another AKS-supported size.

Get AKS credentials:

```bash
az aks get-credentials \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_NAME"
```

Verify the cluster:

```bash
kubectl get nodes
```

Get the ACR login server:

```bash
export ACR_LOGIN_SERVER="$(az acr show \
  --name "$ACR_NAME" \
  --query loginServer -o tsv)"

echo "$ACR_LOGIN_SERVER"
```

---

## 6. Build and push Docker images

From the project root directory:

```bash
export ACR_NAME=<same-acr-name>

chmod +x scripts/*.sh

./scripts/build-and-push.sh
```

The script builds and pushes all three application images.

Check the repositories:

```bash
az acr repository list \
  --name "$ACR_NAME" \
  -o table
```

Expected repositories:

```text
food-restaurant
food-order
food-payment
```

The `az acr build` command builds images in Azure, so a local Docker daemon is not required.

---

## 7. Install NGINX Ingress Controller

This demo uses the community ingress-nginx Helm chart and the `nginx` IngressClass.

```bash
helm repo add ingress-nginx \
  https://kubernetes.github.io/ingress-nginx

helm repo update
```

Install the controller:

```bash
helm upgrade --install ingress-nginx \
  ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2
```

Wait for the external IP:

```bash
kubectl get svc -n ingress-nginx -w
```

Wait until `ingress-nginx-controller` receives an external IP. Press `Ctrl+C` after it appears.

Check the controller:

```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
kubectl get ingressclass
```

> This is a learning setup. For production, select an ingress option supported by your AKS version and your organisation's security and support requirements.

---

## 8. Configure the demo secret

Edit:

```text
kubernetes/secrets.yaml
```

Replace:

```text
replace-this-demo-key
```

with a non-production demo value.

Do not commit real credentials to Git.

The `PAYMENT_API_KEY` value must be identical in the Order and Payment service environments. Both deployments should read the same Kubernetes Secret.

For production, use Azure Key Vault with the Secrets Store CSI Driver and an appropriate workload identity integration.

---

## 9. Deploy the application

From the project root:

```bash
export ACR_LOGIN_SERVER="$(az acr show \
  --name "$ACR_NAME" \
  --query loginServer -o tsv)"
```

Deploy:

```bash
./scripts/deploy.sh
```

Alternatively, apply the Kubernetes manifests manually after exporting `ACR_LOGIN_SERVER`. The deployment script uses `envsubst` to substitute the image registry in the Deployment manifests.

Verify the deployments:

```bash
kubectl get all -n food-demo
```

Check pods:

```bash
kubectl get pods -n food-demo -o wide
```

Check Ingress:

```bash
kubectl get ingress -n food-demo
```

Check HPA:

```bash
kubectl get hpa -n food-demo
```

---

# 10. Application testing

This section covers both internal and external testing.

## 10.1 Internal testing from inside Kubernetes

First, create a temporary curl testing pod if you do not already have one.

```bash
kubectl run debug-curl \
  --image=curlimages/curl:latest \
  --namespace food-demo \
  --restart=Never \
  --command -- sleep 3600
```

Wait until it is running:

```bash
kubectl get pod debug-curl -n food-demo -w
```

If you already have a running `debug-curl` or `curl-test` pod, you can use that instead.

### Test 1: Restaurant Service

List restaurants:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants
```

Expected:

```text
HTTP/1.1 200 OK
```

Retrieve a specific restaurant:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants/rest-001
```

Expected:

```text
HTTP/1.1 200 OK
```

### Test 2: Payment Service

Health check:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

Readiness check:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/ready
```

Expected: HTTP 200 responses.

### Test 3: Order Service

Health check:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/health
```

Readiness check:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/ready
```

### Test 4: End-to-end order creation

This is the most important internal integration test.

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://order-service:8081/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "rest-001",
    "item": "Chicken Burger",
    "amount": 25.50,
    "customer": "AKS Demo Customer"
  }'
```

Expected:

```text
HTTP/1.1 201 CREATED
```

Example response:

```json
{
  "amount": 25.5,
  "currency": "NZD",
  "customer": "AKS Demo Customer",
  "item": "Chicken Burger",
  "order_id": "ord-example",
  "payment": {
    "amount": 25.5,
    "currency": "NZD",
    "order_id": "ord-example",
    "payment_id": "pay-example",
    "simulated": true,
    "status": "APPROVED"
  },
  "restaurant": "Kiwi Kitchen",
  "status": "CONFIRMED"
}
```

The IDs will be generated dynamically and will differ between requests.

This test confirms:

1. The Order Service receives the request.
2. The Order Service calls Restaurant Service.
3. Restaurant Service returns restaurant information.
4. The Order Service calls Payment Service.
5. Payment Service validates the demo API key.
6. Payment Service returns a simulated approval.
7. The Order Service returns a confirmed order.

### Test 5: NGINX Ingress internally

Test the Restaurant route through NGINX:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/restaurants
```

Test a specific restaurant:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/restaurants/rest-001
```

Test order creation through NGINX:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "rest-001",
    "item": "Fish and Chips",
    "amount": 24.50,
    "customer": "Internal Ingress Test"
  }'
```

Expected: HTTP 201 CREATED.

These tests confirm that internal Kubernetes DNS, ClusterIP Services and NGINX path routing are working.

---

## 10.2 External testing through Azure public IP

Get the public IP:

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

Export the public IP automatically:

```bash
export INGRESS_IP="$(kubectl get svc \
  ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"

echo "$INGRESS_IP"
```

### Test 1: List restaurants

```bash
curl -i "http://${INGRESS_IP}/restaurants"
```

Expected: HTTP 200 OK.

### Test 2: Retrieve a restaurant

```bash
curl -i "http://${INGRESS_IP}/restaurants/rest-001"
```

Expected: HTTP 200 OK.

### Test 3: Create an order

```bash
curl -i -X POST "http://${INGRESS_IP}/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "rest-001",
    "item": "Fish and Chips",
    "amount": 24.50,
    "customer": "External Demo Customer"
  }'
```

Expected: HTTP 201 CREATED.

The response should contain:

- An order ID.
- Restaurant name.
- Order status `CONFIRMED`.
- Payment status `APPROVED`.
- `"simulated": true`.

### Test 4: Test from a Windows laptop

Open PowerShell or Windows Terminal:

```powershell
curl.exe -i --connect-timeout 10 http://<INGRESS_IP>/restaurants
```

Replace `<INGRESS_IP>` with the public IP displayed by Kubernetes.

Test order creation:

```powershell
curl.exe -i -X POST http://<INGRESS_IP>/orders `
  -H "Content-Type: application/json" `
  -d '{\"restaurant_id\":\"rest-001\",\"item\":\"Fish and Chips\",\"amount\":24.50,\"customer\":\"Windows Demo User\"}'
```

This verifies access from outside Azure Cloud Shell.

> If the public IP connection times out, check Azure Load Balancer health probes, backend pools, NSG rules, subnet security and routing. A working internal application does not guarantee that the public network path is open.

---

## 10.3 External connectivity troubleshooting

If internal tests pass but public requests time out, investigate the Azure Load Balancer and network configuration.

Check the NGINX Service:

```bash
kubectl describe svc ingress-nginx-controller \
  -n ingress-nginx
```

Check the Load Balancer rules:

```bash
az network lb rule list \
  --resource-group "$NODE_RG" \
  --lb-name "$LB_NAME" \
  -o table
```

Inspect the HTTP rule:

```bash
az network lb rule list \
  --resource-group "$NODE_RG" \
  --lb-name "$LB_NAME" \
  --query "[?frontendPort==\`80\`]" \
  -o json
```

Check health probes:

```bash
az network lb probe list \
  --resource-group "$NODE_RG" \
  --lb-name "$LB_NAME" \
  -o json
```

Check backend pools:

```bash
az network lb address-pool list \
  --resource-group "$NODE_RG" \
  --lb-name "$LB_NAME" \
  -o json
```

Check the AKS networking configuration:

```bash
az aks show \
  --resource-group "$AKS_RG" \
  --name "$AKS_NAME" \
  --query networkProfile \
  -o json
```

### Test the NGINX NodePort

Get the node IP addresses:

```bash
kubectl get nodes -o wide
```

Use an AKS node's `INTERNAL-IP`:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i --connect-timeout 5 http://<NODE-IP>:31522/
```

Test the restaurant route:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i --connect-timeout 5 http://<NODE-IP>:31522/restaurants
```

The NodePort shown above is an example for this deployment. Check the actual value with:

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

The Load Balancer health probe should be inspected carefully. Verify that its protocol, port and request path are compatible with the NGINX controller and the Service's traffic policy.

### Check NGINX controller logs

```bash
kubectl logs \
  -n ingress-nginx \
  deployment/ingress-nginx-controller \
  --tail=100
```

Follow logs in real time:

```bash
kubectl logs \
  -n ingress-nginx \
  deployment/ingress-nginx-controller \
  -f
```

In another terminal, send a public request:

```bash
curl -v --connect-timeout 10 \
  http://<INGRESS_IP>/restaurants
```

If no request appears in the NGINX logs, investigate the network path before the controller.

Do not open all inbound ports or change NSG rules indiscriminately. Use your organisation's approved network security rules.

---

## 10.4 Bundled smoke test

From the project root:

```bash
export INGRESS_IP="$(kubectl get svc \
  ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"

./scripts/smoke-test.sh
```

The smoke test checks the application through the configured Ingress IP. Review the script to confirm which endpoints it tests.

---

# 11. Useful Kubernetes demo commands

### View application resources

```bash
kubectl get all,ingress,hpa -n food-demo
```

### Watch pods

```bash
kubectl get pods -n food-demo -w
```

### Demonstrate self-healing

Delete a Restaurant Service pod:

```bash
kubectl delete pod \
  -n food-demo \
  -l app=restaurant-service \
  --wait=false
```

Watch Kubernetes recreate the pod:

```bash
kubectl get pods -n food-demo -w
```

### Demonstrate manual scaling

For a clean manual scaling demonstration, temporarily remove the HPA:

```bash
kubectl delete hpa order-service -n food-demo
```

Scale Order Service:

```bash
kubectl scale deployment/order-service \
  -n food-demo \
  --replicas=4
```

Verify:

```bash
kubectl get deployment order-service -n food-demo
kubectl get pods -n food-demo
```

Reapply the HPA:

```bash
kubectl apply -f kubernetes/hpa.yaml
```

The HPA controls the replica count, so manual scaling can otherwise be reconciled by the HPA.

### Demonstrate autoscaling

```bash
kubectl get hpa -n food-demo -w
```

Check CPU usage:

```bash
kubectl top nodes
kubectl top pods -n food-demo
```

CPU metrics may take a minute to appear. CPU load testing is not included by default. Generate controlled load only in a non-production demo cluster.

### Inspect logs

```bash
kubectl logs \
  -n food-demo \
  deployment/order-service \
  --tail=100
```

```bash
kubectl logs \
  -n food-demo \
  deployment/restaurant-service \
  --tail=100
```

```bash
kubectl logs \
  -n food-demo \
  deployment/payment-service \
  --tail=100
```

### Check rollout status

```bash
kubectl rollout status deployment/order-service \
  -n food-demo
```

### Demonstrate rolling updates and rollback

After building and pushing a new image tag and updating the Deployment:

```bash
kubectl rollout history deployment/order-service \
  -n food-demo
```

Rollback:

```bash
kubectl rollout undo deployment/order-service \
  -n food-demo
```

---

# 12. Troubleshooting

| Problem | What to check |
|---|---|
| ImagePullBackOff | Image names, image tags, ACR login server and AKS pull permission |
| Ingress has no address | NGINX controller pods, Service events and Azure Load Balancer provisioning |
| External IP connection timeout | Azure Load Balancer health probes, NSG rules, backend pool and routing |
| HPA shows `<unknown>` | Metrics Server, CPU metrics and resource requests |
| Order returns 502 | Order logs, Restaurant and Payment Services and endpoints |
| Payment returns unauthorized | Matching `PAYMENT_API_KEY` in both service environments |
| Internal DNS failure | Kubernetes Service names, namespace and CoreDNS |
| Pod CrashLoopBackOff | Pod logs, events, configuration and Secret references |

### Check ACR access

```bash
az aks check-acr \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_NAME" \
  --acr "$ACR_LOGIN_SERVER"
```

### Check endpoints

```bash
kubectl get endpoints -n food-demo
```

### Describe a failing pod

```bash
kubectl describe pod <POD_NAME> -n food-demo
```

### Check recent events

```bash
kubectl get events \
  -n food-demo \
  --sort-by=.metadata.creationTimestamp
```

---

# 13. Security and scope notes

This is an intermediate learning/demo project, not a production reference architecture.

- The Payment Service simulates approval and never charges a card.
- The example Secret is intended for sandbox use only.
- Kubernetes Secrets are not automatically equivalent to a full secrets-management solution.
- Use Azure Key Vault for production credentials.
- The example Ingress is HTTP-only. Configure TLS and DNS for production.
- Consider Kubernetes Network Policies, workload identity, managed identities, image scanning and centralised monitoring before production use.
- Follow your organisation's approved security and networking standards.

---

# 14. Clean up Azure resources

Azure resources incur charges while running.

When the demonstration is finished, confirm that the resource group contains no resources you need.

Delete the resource group:

```bash
az group delete \
  --name "$RESOURCE_GROUP" \
  --yes \
  --no-wait
```

This removes the AKS cluster, ACR and other resources contained in that resource group.

---

# 15. Demo checklist for knowledge-sharing sessions

Use this checklist during your Kubernetes demonstration.

- [ ] Explain the three microservices and their responsibilities.
- [ ] Show the Docker images in ACR.
- [ ] Show the Kubernetes Deployments and Pods.
- [ ] Show ClusterIP Services and internal DNS.
- [ ] Test Restaurant Service internally.
- [ ] Test Payment Service internally.
- [ ] Create an order through Order Service.
- [ ] Demonstrate Order → Restaurant → Payment communication.
- [ ] Show NGINX Ingress routing.
- [ ] Test application access through the public IP.
- [ ] Demonstrate Kubernetes self-healing by deleting a pod.
- [ ] Demonstrate manual scaling.
- [ ] Demonstrate HPA.
- [ ] Show application logs.
- [ ] Explain Azure Load Balancer and external traffic flow.
- [ ] Explain security considerations and cleanup.

## Learning outcomes

By completing this project, participants should understand:

1. How to containerise Python Flask applications using Docker.
2. How to build and push container images to Azure Container Registry.
3. How to deploy microservices to AKS.
4. How Kubernetes Deployments, Pods and Services work.
5. How ClusterIP and Kubernetes DNS enable internal service communication.
6. How Ingress exposes HTTP application routes.
7. How Azure Load Balancer connects external traffic to AKS.
8. How Kubernetes performs self-healing and scaling.
9. How to troubleshoot common AKS application and networking problems.
