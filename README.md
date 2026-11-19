# AKS Food Delivery Microservices Demo

A sample Python Flask-based microservices application deployed on **Azure Kubernetes Service (AKS)**.

This project demonstrates how to build, containerise, deploy, expose, test, and troubleshoot a microservices-based application using Kubernetes.

It is intended for technical knowledge-sharing sessions and demonstrations of Kubernetes fundamentals, microservices communication, networking, scaling, and self-healing.

---

## 1. Project Overview

The Food Delivery application consists of three independent microservices:

| **Microservice**   | **Port** | **Responsibility**                  |
| ------------------ | -------- | ----------------------------------- |
| Restaurant Service | 8080     | Provides restaurant information     |
| Order Service      | 8081     | Creates and manages customer orders |
| Payment Service    | 8082     | Processes simulated payments        |

### Application Architecture

```
                         Customer
                            |
                            |
                     Public Internet
                            |
                            v
                   Azure Load Balancer
                            |
                            v
                      NGINX Ingress
                            |
                 +----------+----------+
                 |                     |
                 v                     v
          /restaurants              /orders
                 |                     |
                 v                     v
         Restaurant Service      Order Service
                 ^                     |
                 |                     |
                 +---------------------+
                                       |
                                       v
                                Payment Service
                                       |
                                       v
                               Payment Approved

```

### Request Flow

When a customer creates an order:

1. The customer sends a POST request to the Order Service.
2. The Order Service calls the Restaurant Service to retrieve restaurant information.
3. The Order Service calls the Payment Service to process a simulated payment.
4. The Payment Service returns the payment result.
5. The Order Service returns the order confirmation to the customer.

### Technologies Used

- Microsoft Azure
- Azure Kubernetes Service (AKS)
- Azure Container Registry (ACR)
- Docker
- Kubernetes
- Python
- Flask
- NGINX Ingress Controller
- Helm
- Linux / Azure Cloud Shell

---

## 2. Project Structure

```
aks-food-delivery-demo/
│
├── restaurant-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── order-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── payment-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── kubernetes/
│   ├── namespace.yaml
│   ├── restaurant.yaml
│   ├── order.yaml
│   ├── payment.yaml
│   ├── ingress.yaml
│   └── secrets.yaml
│
├── scripts/
│   ├── build-and-push.sh
│   └── deploy.sh
│
└── README.md

```

---

## 3. Prerequisites

Before starting, ensure the following tools are available:

| **Tool**  | **Purpose**                  |
| --------- | ---------------------------- |
| Azure CLI | Manage Azure resources       |
| kubectl   | Manage Kubernetes resources  |
| Docker    | Build container images       |
| Helm      | Install NGINX Ingress        |
| Git       | Clone and manage source code |

You also need:

- An active Azure subscription.
- Permission to create Azure resources.
- Permission to create an AKS cluster and Azure Container Registry.
- An appropriate Azure resource group and subscription.

Check installed tools:

```
az version
kubectl version --client
docker --version
helm version
git --version
```

---

## 4. Clone the Git Repository

Clone the project:

```
git clone <YOUR-GIT-REPOSITORY-URL>
```

Navigate to the project directory:

```
cd aks-food-delivery-demo
```

Check the project structure:

```
ls -la
```

---

## 5. Create Azure Resources

### Step 1: Configure Environment Variables

```
export LOCATION=australiaeast
export RESOURCE_GROUP=rg-aks-food-demo
export AKS_NAME=aks-food-demo
export ACR_NAME=<globally-unique-acr-name>
```

The ACR name must be globally unique and contain only supported characters.

### Step 2: Log in to Azure

```
az login
```

Check the active subscription:

```
az account show
```

If required, select the correct subscription:

```
az account set --subscription "<SUBSCRIPTION-ID>"
```

### Step 3: Create the Resource Group

```
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

If your organisation has Azure Policy requirements, include the mandatory resource group tags.

### Step 4: Create Azure Container Registry

```
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false
```

### Step 5: Create AKS Cluster

Create an AKS cluster with two worker nodes:

```
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --node-count 2 \
  --node-vm-size Standard_D2s_v5 \
  --generate-ssh-keys \
  --attach-acr $ACR_NAME
```

The `--attach-acr` option grants AKS permission to pull images from the Azure Container Registry.

### Step 6: Connect to AKS

```
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME
```

Verify the cluster connection:

```
kubectl get nodes
```

Expected: Two worker nodes should be listed as Ready.

---

## 6. Build and Push Docker Images

The application consists of three Docker images:

| **Service** | **Image**          |
| ----------- | ------------------ |
| Restaurant  | food-restaurant:v1 |
| Order       | food-order:v1      |
| Payment     | food-payment:v1    |

### Step 1: Log in to ACR

```
az acr login --name $ACR_NAME
```

### Step 2: Build and Push Images

From the project root:

```
chmod +x scripts/build-and-push.sh
./scripts/build-and-push.sh
```

The script should build and push all three images to ACR.

### Step 3: Verify Images in ACR

```
az acr repository list \
  --name $ACR_NAME \
  --output table
```

Check image tags:

```
az acr repository show-tags \
  --name $ACR_NAME \
  --repository food-restaurant \
  --output table

az acr repository show-tags \
  --name $ACR_NAME \
  --repository food-order \
  --output table

az acr repository show-tags \
  --name $ACR_NAME \
  --repository food-payment \
  --output table
```

Expected image references:

```
<ACR_NAME>.azurecr.io/food-restaurant:v1
<ACR_NAME>.azurecr.io/food-order:v1
<ACR_NAME>.azurecr.io/food-payment:v1

```

---

## 7. Install NGINX Ingress Controller

NGINX Ingress provides a single entry point to access the application from outside the Kubernetes cluster.

### Step 1: Add the Helm Repository

```
helm repo add ingress-nginx \
  https://kubernetes.github.io/ingress-nginx

helm repo update
```

### Step 2: Install NGINX Ingress

```
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

```
kubectl annotate service ingress-nginx-controller \
  -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz \
  --overwrite
```

### Step 3: Verify the Installation

```
kubectl get pods -n ingress-nginx
```

Check the Service:

```
kubectl get svc -n ingress-nginx
```

The `ingress-nginx-controller` Service should be created with type `LoadBalancer`.

### Step 4: Retrieve the Public IP

```
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

Retrieve the IP automatically:

```
export INGRESS_IP=$(kubectl get svc ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo $INGRESS_IP
```

---

## 8. Configure Kubernetes Secrets

The Payment Service uses a demo API key for simulated payment requests.

Configure the secret using the value expected by the application.

Edit:

```
vi kubernetes/secrets.yaml
```

Ensure the Secret contains the expected key and value.

**Security note:** Do not commit real credentials or API keys to Git. For a production deployment, use Azure Key Vault and an appropriate secrets integration.

---

## 9. Deploy the Application to AKS

### Step 1: Deploy the Namespace

```
kubectl apply -f kubernetes/namespace.yaml
```

Verify:

```
kubectl get namespaces
```

### Step 2: Deploy the Secrets

```
kubectl apply -f kubernetes/secrets.yaml
```

### Step 3: Deploy the Microservices

```
kubectl apply -f kubernetes/restaurant.yaml
kubectl apply -f kubernetes/payment.yaml
kubectl apply -f kubernetes/order.yaml
```

### Step 4: Deploy the Ingress

```
kubectl apply -f kubernetes/ingress.yaml
```

### Step 5: Verify Deployments

```
kubectl get deployments -n food-demo
kubectl get pods -n food-demo -o wide
kubectl get services -n food-demo
kubectl get ingress -n food-demo
```

Expected application deployments:

```
order-service
payment-service
restaurant-service

```

All deployments should become Available, and the application pods should be Running and Ready.

---

# 10. Application Testing Guide

Testing is divided into two areas:

1. **Internal testing:** Access services from inside the Kubernetes cluster.
2. **External testing:** Access services through the NGINX Ingress public IP.

## 10.1 Internal Application Testing

### Create a Debug Pod

Create a temporary pod to run curl commands inside the cluster:

```
kubectl run debug-curl \
  -n food-demo \
  --image=curlimages/curl \
  --restart=Never \
  --command -- sleep 36000
```

Wait for the pod:

```
kubectl wait --for=condition=Ready pod/debug-curl \
  -n food-demo --timeout=120s
```

Verify:

```
kubectl get pod debug-curl -n food-demo
```

### Test 1: Restaurant Service

Test the Restaurant Service health endpoint:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/health
```

Test the restaurant listing endpoint:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants
```

Test a specific restaurant:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants/rest-001
```

Expected:

- HTTP 200 response.
- Restaurant details should be returned.

### Test 2: Payment Service

The Payment Service processes simulated payments. It requires a valid API key and validates the payment request before approving it.

The application reads the API key from the `PAYMENT_API_KEY` environment variable. In Kubernetes, this value is supplied by the Secret named `food-demo-secrets`.

The Payment Service is exposed internally as a `ClusterIP` Service on port `8082`. It is not publicly exposed by the current Ingress configuration.

#### 2.1 Test the service root endpoint

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/
```

Expected: HTTP `200 OK`, with the service name, a message that payments are simulated, and the available endpoint list.

#### 2.2 Test the health endpoint

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

Expected: HTTP `200 OK`, with `status` set to `healthy`.

#### 2.3 Test the readiness endpoint

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/ready
```

Expected: HTTP `200 OK`, with `status` set to `ready`.

**Kubernetes probe note:** The current `payment.yaml` uses `/health` for both the readiness and liveness probes. The application also implements `/ready`, so you can optionally change the readiness probe to `/ready` while keeping the liveness probe on `/health`.

#### 2.4 Check the API key Secret configuration

Confirm that the Secret exists:

```bash
kubectl get secret food-demo-secrets -n food-demo
```

The Secret must provide an environment variable named `PAYMENT_API_KEY`. The deployment imports Secret keys using `envFrom`, so the key name in the Secret must match the environment variable name exactly.

To inspect only the key names (not their values):

```bash
kubectl get secret food-demo-secrets -n food-demo \
  -o json | python3 -c \
  'import json,sys; print("\n".join(json.load(sys.stdin).get("data", {}).keys()))'
```

Expected: `PAYMENT_API_KEY` should appear in the output.

Do not print or commit the actual API key. If the Secret is missing the key, update your secret configuration securely and re-apply it.

#### 2.5 Set the API key in the Cloud Shell session

Read the same key value that is configured in the Kubernetes Secret. Do not paste the actual key into the README or Git repository.

```bash
read -rsp "Enter Payment API key: " PAYMENT_API_KEY
export PAYMENT_API_KEY
echo
```

This exports the key in the current Cloud Shell session. The value is not automatically available inside the debug pod; the following commands pass it as a curl header from the shell running `kubectl exec`.

#### 2.6 Test a successful simulated payment

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "order_id": "ord-test-001",
    "amount": 25.50,
    "currency": "NZD"
  }'
```

Expected: HTTP `201 CREATED`.

Example response (the payment ID is generated dynamically):

```json
{
  "payment_id": "pay-example",
  "order_id": "ord-test-001",
  "amount": 25.5,
  "currency": "NZD",
  "status": "APPROVED",
  "simulated": true
}
```

The response confirms that the request was authenticated and accepted as a simulated payment.

#### 2.7 Test authentication with a missing API key

Send a payment request without the `X-Demo-Key` header:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ord-test-002",
    "amount": 25.50,
    "currency": "NZD"
  }'
```

Expected: HTTP `401 UNAUTHORIZED`.

#### 2.8 Test authentication with an incorrect API key

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: invalid-demo-key" \
  -d '{
    "order_id": "ord-test-003",
    "amount": 25.50,
    "currency": "NZD"
  }'
```

Expected: HTTP `401 UNAUTHORIZED`.

#### 2.9 Test a negative payment amount

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "order_id": "ord-test-004",
    "amount": -25.50,
    "currency": "NZD"
  }'
```

Expected: HTTP `400 BAD REQUEST`.

#### 2.10 Test a missing order ID

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "amount": 25.50,
    "currency": "NZD"
  }'
```

Expected: HTTP `400 BAD REQUEST`.

#### 2.11 Test an invalid currency

The application expects a three-letter alphabetic currency code.

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "order_id": "ord-test-005",
    "amount": 25.50,
    "currency": "US"
  }'
```

Expected: HTTP `400 BAD REQUEST`.

#### 2.12 Test invalid JSON

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d 'invalid-json'
```

Expected: HTTP `400 BAD REQUEST`.

#### 2.13 Test a missing or invalid amount

Missing amount:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "order_id": "ord-test-006",
    "currency": "NZD"
  }'
```

Expected: HTTP `400 BAD REQUEST`.

Zero amount:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: ${PAYMENT_API_KEY}" \
  -d '{
    "order_id": "ord-test-007",
    "amount": 0,
    "currency": "NZD"
  }'
```

Expected: HTTP `400 BAD REQUEST`.

#### 2.14 Test the service configuration error (optional)

The application returns HTTP `500` if `PAYMENT_API_KEY` is not configured in the Payment Service container. Do not remove the key from your working demo deployment just to run this test. If you reproduce this scenario in a separate test environment, the expected response is:

```json
{
  "error": "service_configuration_error",
  "message": "Payment service is not configured"
}
```

Expected: HTTP `500 INTERNAL SERVER ERROR`.

#### 2.15 Check Payment Service logs

```bash
kubectl logs deployment/payment-service \
  -n food-demo --tail=100
```

Look for messages indicating simulated payment approvals and warnings for unauthorized payment requests. The application logs payment IDs, order IDs, amounts, and currencies; do not add API key values to logs.

#### 2.16 Verify Payment Service Kubernetes resources

```bash
kubectl get deployment payment-service -n food-demo

kubectl get pods -n food-demo \
  -l app=payment-service

kubectl get service payment-service -n food-demo

kubectl describe deployment payment-service -n food-demo
```

Expected:

- Deployment has two replicas configured.
- Payment pods are Running and Ready.
- Service type is `ClusterIP`.
- Service port is `8082`.
- The deployment imports environment variables from `food-demo-secrets`.

**Important:** All payment transactions in this demo are simulated. No real payment gateway is integrated and no money is transferred. Do not expose `/payments/charge` publicly for this demonstration unless you intentionally configure and secure an Ingress route.

### Test 3: Order Service

Test the Order Service health endpoint:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/health
```

Test the readiness endpoint:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/ready
```

Expected:

- HTTP 200 response.
- Order Service should be healthy and ready.

### Test 4: End-to-End Order Creation

This is the most important internal integration test.

The Order Service communicates with both the Restaurant Service and Payment Service.

Create a new order:

```
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

Expected response:

```
{
  "amount": 25.5,
  "currency": "NZD",
  "customer": "AKS Demo Customer",
  "item": "Chicken Burger",
  "order_id": "ord-example",
  "payment": {
    "amount": 25.5,
    "currency": "NZD",
    "payment_id": "pay-example",
    "simulated": true,
    "status": "APPROVED"
  },
  "restaurant": "Kiwi Kitchen",
  "status": "CONFIRMED"
}
```

Expected:

- HTTP 201 CREATED.
- Restaurant details returned.
- Payment approved.
- Order status CONFIRMED.
- Unique order ID generated.

### Test 5: List All Created Orders

If the Order Service implements GET `/orders`:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/orders
```

Expected:

- HTTP 200 response.
- Total order count returned.
- Order details returned.

Example:

```
{
  "total_orders": 1,
  "orders": [
    {
      "order_id": "ord-example",
      "restaurant": "Kiwi Kitchen",
      "item": "Chicken Burger",
      "amount": 25.5,
      "currency": "NZD",
      "customer": "AKS Demo Customer",
      "status": "CONFIRMED"
    }
  ]
}
```

**Important:** If orders are stored in memory, they disappear when the relevant process restarts. With multiple Order Service replicas, each replica may have a different in-memory list. Use a shared database for reliable order persistence.

### Test 6: Test NGINX Ingress Internally

Test the Restaurant Service through the NGINX controller:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/restaurants
```

Test the Order Service through NGINX:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/orders
```

Test order creation through NGINX:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "rest-001",
    "item": "Chicken Burger",
    "amount": 25.50,
    "customer": "Ingress Demo Customer"
  }'
```

Expected:

- NGINX receives the request.
- NGINX routes it to the correct Kubernetes Service.
- The application returns the expected response.

## 10.2 Kubernetes Service Discovery Testing

Kubernetes provides internal DNS-based service discovery.

List the application Services:

```
kubectl get svc -n food-demo
```

Resolve the Restaurant Service:

```
kubectl exec -n food-demo debug-curl -- \
  nslookup restaurant-service
```

Resolve the Order Service:

```
kubectl exec -n food-demo debug-curl -- \
  nslookup order-service
```

Resolve the Payment Service:

```
kubectl exec -n food-demo debug-curl -- \
  nslookup payment-service
```

Test connectivity to each Service:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/health

kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/health

kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

## 10.3 External Application Testing

External testing verifies that the application is accessible through the public NGINX Ingress IP.

### Test 7: Retrieve the Ingress Public IP

```
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

Set the IP:

```
export INGRESS_IP=$(kubectl get svc ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo $INGRESS_IP
```

For the current demo environment, the previously allocated IP was:

```
export INGRESS_IP=20.193.20.29
```

### Test 8: External Restaurant Service

Test the restaurant listing:

```
curl -i http://${INGRESS_IP}/restaurants
```

Test a specific restaurant:

```
curl -i http://${INGRESS_IP}/restaurants/rest-001
```

Expected:

- HTTP 200 response.
- Restaurant details returned.

### Test 9: External Order Service

Create an order through the public Ingress IP:

```
curl -i -X POST http://${INGRESS_IP}/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "rest-001",
    "item": "Chicken Burger",
    "amount": 25.50,
    "customer": "External Demo Customer"
  }'
```

Expected:

- HTTP 201 CREATED.
- Order confirmation returned.
- Payment status APPROVED.

### Test 10: External Order Listing

If GET `/orders` is implemented and the Ingress routes `/orders` to the Order Service:

```
curl -i http://${INGRESS_IP}/orders
```

Expected:

- HTTP 200 response.
- Order list returned.

### Test 11: Test External Connectivity

Check the public endpoint:

```
curl -v --connect-timeout 10 \
  http://${INGRESS_IP}/restaurants
```

Check the NGINX Service:

```
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx -o wide
```

Check the Ingress configuration:

```
kubectl describe ingress food-demo -n food-demo
```

Check NGINX controller logs:

```
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

**Important:** External connectivity depends on the Azure Load Balancer, network security rules, routing, and healthy backend nodes. A public IP being allocated does not by itself guarantee that the endpoint is reachable.

The Payment Service is intended to be accessed internally unless you explicitly add a public Ingress route for it.

---

## 11. Scaling and Self-Healing

### Test 12: Scale the Order Service

Increase the Order Service replicas from two to three:

```
kubectl scale deployment order-service \
  --replicas=3 -n food-demo
```

Verify:

```
kubectl get pods -n food-demo
kubectl get deployment order-service -n food-demo
```

Restore the original replica count:

```
kubectl scale deployment order-service \
  --replicas=2 -n food-demo
```

### Test 13: Demonstrate Kubernetes Self-Healing

List the Order Service pods:

```
kubectl get pods -n food-demo \
  -l app=order-service
```

Delete one pod:

```
kubectl delete pod <ORDER-POD-NAME> -n food-demo
```

Watch Kubernetes recreate it:

```
kubectl get pods -n food-demo -w
```

Expected:

- Kubernetes detects the deleted pod.
- The Deployment controller creates a replacement pod.
- The desired replica count is restored.

This demonstrates Kubernetes self-healing.

### Test 14: Horizontal Pod Autoscaler

If HPA is configured:

```
kubectl get hpa -n food-demo
```

Get HPA details:

```
kubectl describe hpa -n food-demo
```

Monitor resource usage:

```
kubectl top pods -n food-demo
kubectl top nodes
```

**Note:** HPA requires the appropriate metrics source, commonly Metrics Server, and resource requests must be configured for CPU or memory utilisation-based scaling.

---

## 12. Application Logs and Troubleshooting

### Check Restaurant Service Logs

```
kubectl logs deployment/restaurant-service \
  -n food-demo --tail=100
```

### Check Order Service Logs

```
kubectl logs deployment/order-service \
  -n food-demo --tail=100
```

### Check Payment Service Logs

```
kubectl logs deployment/payment-service \
  -n food-demo --tail=100
```

### Check NGINX Ingress Logs

```
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

### Describe Application Pods

```
kubectl describe pods -n food-demo
```

### Check Kubernetes Events

```
kubectl get events -n food-demo \
  --sort-by=.metadata.creationTimestamp
```

### Check Deployment Status

```
kubectl rollout status deployment/restaurant-service \
  -n food-demo

kubectl rollout status deployment/order-service \
  -n food-demo

kubectl rollout status deployment/payment-service \
  -n food-demo
```

### Restart a Deployment

```
kubectl rollout restart deployment/restaurant-service \
  -n food-demo

kubectl rollout restart deployment/order-service \
  -n food-demo

kubectl rollout restart deployment/payment-service \
  -n food-demo
```

### Roll Back a Deployment

```
kubectl rollout history deployment/order-service \
  -n food-demo

kubectl rollout undo deployment/order-service \
  -n food-demo
```

---

## 13. Useful Kubernetes Commands

| **Task**             | **Command**                                      |
| -------------------- | ------------------------------------------------ |
| List nodes           | `kubectl get nodes`                              |
| List namespaces      | `kubectl get ns`                                 |
| List pods            | `kubectl get pods -n food-demo`                  |
| List deployments     | `kubectl get deployments -n food-demo`           |
| List services        | `kubectl get svc -n food-demo`                   |
| List Ingress         | `kubectl get ingress -n food-demo`               |
| Describe pod         | `kubectl describe pod <POD> -n food-demo`        |
| Pod logs             | `kubectl logs <POD> -n food-demo`                |
| Follow logs          | `kubectl logs -f <POD> -n food-demo`             |
| Execute into pod     | `kubectl exec -it <POD> -n food-demo -- /bin/sh` |
| Watch pods           | `kubectl get pods -n food-demo -w`               |
| Check resource usage | `kubectl top pods -n food-demo`                  |

---

## 14. Troubleshooting Guide

### Pods are in ImagePullBackOff

Check the pod:

```
kubectl describe pod <POD-NAME> -n food-demo
```

Check:

- ACR image name and tag.
- AKS-to-ACR permissions.
- Image availability in ACR.
- Image pull configuration.

Verify ACR attachment:

```
az aks show \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --query "identity"
```

### Pods are in CrashLoopBackOff

Check logs:

```
kubectl logs <POD-NAME> -n food-demo
```

Check previous container logs:

```
kubectl logs <POD-NAME> -n food-demo --previous
```

Describe the pod:

```
kubectl describe pod <POD-NAME> -n food-demo
```

### Order Service Cannot Reach Restaurant or Payment Service

Check Services:

```
kubectl get svc -n food-demo
```

Check DNS:

```
kubectl exec -n food-demo debug-curl -- \
  nslookup restaurant-service

kubectl exec -n food-demo debug-curl -- \
  nslookup payment-service
```

Test connectivity:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/health

kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

Check application configuration and environment variables if connectivity fails.

### Ingress Is Not Working

Check the Ingress resource:

```
kubectl get ingress -n food-demo
kubectl describe ingress food-demo -n food-demo
```

Check the controller:

```
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

Check the controller logs:

```
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

Test the NGINX controller internally:

```
kubectl exec -n food-demo debug-curl -- \
  curl -i http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/restaurants
```

If internal routing works but external access times out, investigate:

- Azure Load Balancer backend health.
- Azure network security group rules.
- NodePort reachability.
- Load Balancer health probes.
- User-defined routes and network configuration.

### External Public IP Is Not Reachable

Check the LoadBalancer IP:

```
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx -o wide
```

Check the Azure Load Balancer configuration and health probes in the AKS node resource group.

Check the Service configuration:

```
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx -o yaml
```

Remember that an allocated public IP does not guarantee that the Azure Load Balancer backend is healthy or that network traffic is permitted.

---

## 15. Security Considerations

This project is designed as a demonstration and is not a production-ready food delivery platform.

Consider the following before using a similar design in production:

- Use Azure Key Vault for secrets management.
- Avoid storing credentials in source code or Git.
- Use HTTPS and valid TLS certificates for public traffic.
- Apply Kubernetes RBAC and least-privilege access.
- Use Network Policies to control pod-to-pod traffic.
- Use a database for persistent order storage.
- Add authentication and authorisation for customer-facing APIs.
- Configure resource requests and limits.
- Configure monitoring, logging, and alerting.
- Restrict public exposure of internal services.
- Use an appropriate payment provider for real transactions.

---

## 16. Cleanup Azure Resources

To remove the demo application:

### Delete the application resources

```
kubectl delete namespace food-demo
```

### Remove NGINX Ingress

```
helm uninstall ingress-nginx -n ingress-nginx
kubectl delete namespace ingress-nginx
```

### Delete the AKS Cluster and ACR

If you want to remove all Azure resources created for this demo:

```
az aks delete \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --yes
```

Delete the Container Registry:

```
az acr delete \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --yes
```

Delete the resource group:

```
az group delete \
  --name $RESOURCE_GROUP \
  --yes \
  --no-wait
```

**Warning:** Deleting the resource group removes all resources inside it. Make sure it does not contain resources you want to retain.

---

## 17. Demo Presentation Flow

Suggested sequence for a knowledge-sharing session:

| **Step** | **Demonstration**                 | **What it shows**                    |
| -------- | --------------------------------- | ------------------------------------ |
| 1        | Show the application architecture | Microservices design                 |
| 2        | Show the Azure AKS cluster        | Kubernetes infrastructure            |
| 3        | Show Docker images in ACR         | Containerisation and image registry  |
| 4        | Show Deployments and Pods         | Kubernetes workload management       |
| 5        | Show Kubernetes Services          | Internal service discovery           |
| 6        | Test Restaurant Service           | Individual microservice              |
| 7        | Test Payment Service              | Simulated payment processing         |
| 8        | Create a customer order           | End-to-end microservices integration |
| 9        | List created orders               | Application API functionality        |
| 10       | Test NGINX Ingress internally     | Ingress routing                      |
| 11       | Test public Ingress IP            | External application access          |
| 12       | Scale the Order Service           | Kubernetes scaling                   |
| 13       | Delete a pod                      | Kubernetes self-healing              |
| 14       | Show application logs             | Monitoring and troubleshooting       |

### Key Learning Outcomes

By completing this demonstration, participants should understand:

- What Kubernetes provides for containerised applications.
- How Docker images are built and pushed to Azure Container Registry.
- How applications are deployed to AKS.
- How Kubernetes Pods, Deployments, and Services work.
- How microservices communicate using Kubernetes DNS.
- How NGINX Ingress routes external requests.
- How Kubernetes supports scaling and self-healing.
- How to troubleshoot application and infrastructure issues.

---

## 18. Git Commands

Check repository status:

```
git status
```

Add the updated README:

```
git add README.md
```

Commit changes:

```
git commit -m "Update AKS Food Delivery demo documentation"
```

Push to the remote repository:

```
git push
```

---

## Conclusion

This project demonstrates a simple but practical microservices application running on Azure Kubernetes Service.

It provides a foundation for understanding containerisation, Kubernetes orchestration, internal networking, Ingress, service-to-service communication, scaling, and self-healing.

The same concepts can be extended with persistent databases, observability tools, service mesh technologies such as Istio, CI/CD pipelines, and production-grade security controls.