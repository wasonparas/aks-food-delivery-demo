# AKS Food Delivery Microservices Demo

A sample Python Flask-based microservices application deployed on **Azure Kubernetes Service (AKS)**.

This project demonstrates how to build, containerise, deploy, expose, test, and troubleshoot a microservices-based application using Kubernetes.

It is intended for technical knowledge-sharing sessions and demonstrations of Kubernetes fundamentals, microservices communication, networking, scaling, and self-healing.

---

## 1. Project Overview

The Food Delivery application consists of three independent microservices:

| Microservice | Port | Responsibility |
|---|---:|---|
| Restaurant Service | 8080 | Provides restaurant information |
| Order Service | 8081 | Creates and manages customer orders |
| Payment Service | 8082 | Processes simulated payments |

### Application Architecture

```text
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

```text
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

| Tool | Purpose |
|---|---|
| Azure CLI | Manage Azure resources |
| kubectl | Manage Kubernetes resources |
| Docker | Build container images |
| Helm | Install NGINX Ingress |
| Git | Clone and manage source code |

You also need:
- An active Azure subscription.
- Permission to create Azure resources.
- Permission to create an AKS cluster and Azure Container Registry.
- An appropriate Azure resource group and subscription.

Check installed tools:

```bash
az version
kubectl version --client
docker --version
helm version
git --version
```

---

## 4. Clone the Git Repository

Clone the project:

```bash
git clone <YOUR-GIT-REPOSITORY-URL>
```

Navigate to the project directory:

```bash
cd aks-food-delivery-demo
```

Check the project structure:

```bash
ls -la
```

---

## 5. Create Azure Resources

### Step 1: Configure Environment Variables

```bash
export LOCATION=australiaeast
export RESOURCE_GROUP=rg-aks-food-demo
export AKS_NAME=aks-food-demo
export ACR_NAME=<globally-unique-acr-name>
```

The ACR name must be globally unique and contain only supported characters.

### Step 2: Log in to Azure

```bash
az login
```

Check the active subscription:

```bash
az account show
```

If required, select the correct subscription:

```bash
az account set --subscription "<SUBSCRIPTION-ID>"
```

### Step 3: Create the Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

If your organisation has Azure Policy requirements, include the mandatory resource group tags.

### Step 4: Create Azure Container Registry

```bash
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false
```

### Step 5: Create AKS Cluster

Create an AKS cluster with two worker nodes:

```bash
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

```bash
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME
```

Verify the cluster connection:

```bash
kubectl get nodes
```

Expected: Two worker nodes should be listed as Ready.

---

## 6. Build and Push Docker Images

The application consists of three Docker images:

| Service | Image |
|---|---|
| Restaurant | food-restaurant:v1 |
| Order | food-order:v1 |
| Payment | food-payment:v1 |

### Step 1: Log in to ACR

```bash
az acr login --name $ACR_NAME
```

### Step 2: Build and Push Images

From the project root:

```bash
chmod +x scripts/build-and-push.sh
./scripts/build-and-push.sh
```

The script should build and push all three images to ACR.

### Step 3: Verify Images in ACR

```bash
az acr repository list \
  --name $ACR_NAME \
  --output table
```

Check image tags:

```bash
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

```text
<ACR_NAME>.azurecr.io/food-restaurant:v1
<ACR_NAME>.azurecr.io/food-order:v1
<ACR_NAME>.azurecr.io/food-payment:v1
```

---

## 7. Install NGINX Ingress Controller

NGINX Ingress provides a single entry point to access the application from outside the Kubernetes cluster.

### Step 1: Add the Helm Repository

```bash
helm repo add ingress-nginx \
  https://kubernetes.github.io/ingress-nginx

helm repo update
```

### Step 2: Install NGINX Ingress

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

```bash
kubectl annotate service ingress-nginx-controller \
  -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path=/healthz \
  --overwrite
```



### Step 3: Verify the Installation

```bash
kubectl get pods -n ingress-nginx
```

Check the Service:

```bash
kubectl get svc -n ingress-nginx
```

The `ingress-nginx-controller` Service should be created with type `LoadBalancer`.

### Step 4: Retrieve the Public IP

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

Retrieve the IP automatically:

```bash
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

```bash
vi kubernetes/secrets.yaml
```

Ensure the Secret contains the expected key and value.

**Security note:** Do not commit real credentials or API keys to Git. For a production deployment, use Azure Key Vault and an appropriate secrets integration.

---

## 9. Deploy the Application to AKS

### Step 1: Deploy the Namespace

```bash
kubectl apply -f kubernetes/namespace.yaml
```

Verify:

```bash
kubectl get namespaces
```

### Step 2: Deploy the Secrets

```bash
kubectl apply -f kubernetes/secrets.yaml
```

### Step 3: Deploy the Microservices

```bash
kubectl apply -f kubernetes/restaurant.yaml
kubectl apply -f kubernetes/payment.yaml
kubectl apply -f kubernetes/order.yaml
```

### Step 4: Deploy the Ingress

```bash
kubectl apply -f kubernetes/ingress.yaml
```

### Step 5: Verify Deployments

```bash
kubectl get deployments -n food-demo
kubectl get pods -n food-demo -o wide
kubectl get services -n food-demo
kubectl get ingress -n food-demo
```

Expected application deployments:

```text
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

```bash
kubectl run debug-curl \
  -n food-demo \
  --image=curlimages/curl \
  --restart=Never \
  --command -- sleep 36000
```

Wait for the pod:

```bash
kubectl wait --for=condition=Ready pod/debug-curl \
  -n food-demo --timeout=120s
```

Verify:

```bash
kubectl get pod debug-curl -n food-demo
```

### Test 1: Restaurant Service

Test the Restaurant Service health endpoint:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/health
```

Test the restaurant listing endpoint:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants
```

Test a specific restaurant:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/restaurants/rest-001
```

Expected:
- HTTP 200 response.
- Restaurant details should be returned.

### Test 2: Payment Service

Test the Payment Service health endpoint:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

Test the readiness endpoint:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/ready
```

Test a simulated payment:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i -X POST http://payment-service:8082/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-Demo-Key: YOUR_DEMO_API_KEY" \
  -d '{
    "order_id": "ord-test-001",
    "amount": 25.50,
    "currency": "NZD"
  }'
```

Replace `YOUR_DEMO_API_KEY` with the value configured in your Kubernetes Secret.

Expected:
- Payment request is accepted.
- Payment status should be APPROVED.
- Response should indicate that the payment is simulated.

**Note:** This is a simulated payment. No real financial transaction takes place.

### Test 3: Order Service

Test the Order Service health endpoint:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/health
```

Test the readiness endpoint:

```bash
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

Expected response:

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

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://order-service:8081/orders
```

Expected:
- HTTP 200 response.
- Total order count returned.
- Order details returned.

Example:

```json
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

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/restaurants
```

Test the Order Service through NGINX:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i \
  http://ingress-nginx-controller.ingress-nginx.svc.cluster.local/orders
```

Test order creation through NGINX:

```bash
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

```bash
kubectl get svc -n food-demo
```

Resolve the Restaurant Service:

```bash
kubectl exec -n food-demo debug-curl -- \
  nslookup restaurant-service
```

Resolve the Order Service:

```bash
kubectl exec -n food-demo debug-curl -- \
  nslookup order-service
```

Resolve the Payment Service:

```bash
kubectl exec -n food-demo debug-curl -- \
  nslookup payment-service
```

Test connectivity to each Service:

```bash
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

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx
```

Set the IP:

```bash
export INGRESS_IP=$(kubectl get svc ingress-nginx-controller \
  -n ingress-nginx \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo $INGRESS_IP
```

For the current demo environment, the previously allocated IP was:

```bash
export INGRESS_IP=20.193.20.29
```

### Test 8: External Restaurant Service

Test the restaurant listing:

```bash
curl -i http://${INGRESS_IP}/restaurants
```

Test a specific restaurant:

```bash
curl -i http://${INGRESS_IP}/restaurants/rest-001
```

Expected:
- HTTP 200 response.
- Restaurant details returned.

### Test 9: External Order Service

Create an order through the public Ingress IP:

```bash
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

```bash
curl -i http://${INGRESS_IP}/orders
```

Expected:
- HTTP 200 response.
- Order list returned.

### Test 11: Test External Connectivity

Check the public endpoint:

```bash
curl -v --connect-timeout 10 \
  http://${INGRESS_IP}/restaurants
```

Check the NGINX Service:

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx -o wide
```

Check the Ingress configuration:

```bash
kubectl describe ingress food-demo -n food-demo
```

Check NGINX controller logs:

```bash
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

**Important:** External connectivity depends on the Azure Load Balancer, network security rules, routing, and healthy backend nodes. A public IP being allocated does not by itself guarantee that the endpoint is reachable.

The Payment Service is intended to be accessed internally unless you explicitly add a public Ingress route for it.

---

## 11. Scaling and Self-Healing

### Test 12: Scale the Order Service

Increase the Order Service replicas from two to three:

```bash
kubectl scale deployment order-service \
  --replicas=3 -n food-demo
```

Verify:

```bash
kubectl get pods -n food-demo
kubectl get deployment order-service -n food-demo
```

Restore the original replica count:

```bash
kubectl scale deployment order-service \
  --replicas=2 -n food-demo
```

### Test 13: Demonstrate Kubernetes Self-Healing

List the Order Service pods:

```bash
kubectl get pods -n food-demo \
  -l app=order-service
```

Delete one pod:

```bash
kubectl delete pod <ORDER-POD-NAME> -n food-demo
```

Watch Kubernetes recreate it:

```bash
kubectl get pods -n food-demo -w
```

Expected:
- Kubernetes detects the deleted pod.
- The Deployment controller creates a replacement pod.
- The desired replica count is restored.

This demonstrates Kubernetes self-healing.

### Test 14: Horizontal Pod Autoscaler

If HPA is configured:

```bash
kubectl get hpa -n food-demo
```

Get HPA details:

```bash
kubectl describe hpa -n food-demo
```

Monitor resource usage:

```bash
kubectl top pods -n food-demo
kubectl top nodes
```

**Note:** HPA requires the appropriate metrics source, commonly Metrics Server, and resource requests must be configured for CPU or memory utilisation-based scaling.

---

## 12. Application Logs and Troubleshooting

### Check Restaurant Service Logs

```bash
kubectl logs deployment/restaurant-service \
  -n food-demo --tail=100
```

### Check Order Service Logs

```bash
kubectl logs deployment/order-service \
  -n food-demo --tail=100
```

### Check Payment Service Logs

```bash
kubectl logs deployment/payment-service \
  -n food-demo --tail=100
```

### Check NGINX Ingress Logs

```bash
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

### Describe Application Pods

```bash
kubectl describe pods -n food-demo
```

### Check Kubernetes Events

```bash
kubectl get events -n food-demo \
  --sort-by=.metadata.creationTimestamp
```

### Check Deployment Status

```bash
kubectl rollout status deployment/restaurant-service \
  -n food-demo

kubectl rollout status deployment/order-service \
  -n food-demo

kubectl rollout status deployment/payment-service \
  -n food-demo
```

### Restart a Deployment

```bash
kubectl rollout restart deployment/restaurant-service \
  -n food-demo

kubectl rollout restart deployment/order-service \
  -n food-demo

kubectl rollout restart deployment/payment-service \
  -n food-demo
```

### Roll Back a Deployment

```bash
kubectl rollout history deployment/order-service \
  -n food-demo

kubectl rollout undo deployment/order-service \
  -n food-demo
```

---

## 13. Useful Kubernetes Commands

| Task | Command |
|---|---|
| List nodes | `kubectl get nodes` |
| List namespaces | `kubectl get ns` |
| List pods | `kubectl get pods -n food-demo` |
| List deployments | `kubectl get deployments -n food-demo` |
| List services | `kubectl get svc -n food-demo` |
| List Ingress | `kubectl get ingress -n food-demo` |
| Describe pod | `kubectl describe pod <POD> -n food-demo` |
| Pod logs | `kubectl logs <POD> -n food-demo` |
| Follow logs | `kubectl logs -f <POD> -n food-demo` |
| Execute into pod | `kubectl exec -it <POD> -n food-demo -- /bin/sh` |
| Watch pods | `kubectl get pods -n food-demo -w` |
| Check resource usage | `kubectl top pods -n food-demo` |

---

## 14. Troubleshooting Guide

### Pods are in ImagePullBackOff

Check the pod:

```bash
kubectl describe pod <POD-NAME> -n food-demo
```

Check:
- ACR image name and tag.
- AKS-to-ACR permissions.
- Image availability in ACR.
- Image pull configuration.

Verify ACR attachment:

```bash
az aks show \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --query "identity"
```

### Pods are in CrashLoopBackOff

Check logs:

```bash
kubectl logs <POD-NAME> -n food-demo
```

Check previous container logs:

```bash
kubectl logs <POD-NAME> -n food-demo --previous
```

Describe the pod:

```bash
kubectl describe pod <POD-NAME> -n food-demo
```

### Order Service Cannot Reach Restaurant or Payment Service

Check Services:

```bash
kubectl get svc -n food-demo
```

Check DNS:

```bash
kubectl exec -n food-demo debug-curl -- \
  nslookup restaurant-service

kubectl exec -n food-demo debug-curl -- \
  nslookup payment-service
```

Test connectivity:

```bash
kubectl exec -n food-demo debug-curl -- \
  curl -i http://restaurant-service:8080/health

kubectl exec -n food-demo debug-curl -- \
  curl -i http://payment-service:8082/health
```

Check application configuration and environment variables if connectivity fails.

### Ingress Is Not Working

Check the Ingress resource:

```bash
kubectl get ingress -n food-demo
kubectl describe ingress food-demo -n food-demo
```

Check the controller:

```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

Check the controller logs:

```bash
kubectl logs deployment/ingress-nginx-controller \
  -n ingress-nginx --tail=100
```

Test the NGINX controller internally:

```bash
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

```bash
kubectl get svc ingress-nginx-controller \
  -n ingress-nginx -o wide
```

Check the Azure Load Balancer configuration and health probes in the AKS node resource group.

Check the Service configuration:

```bash
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

```bash
kubectl delete namespace food-demo
```

### Remove NGINX Ingress

```bash
helm uninstall ingress-nginx -n ingress-nginx
kubectl delete namespace ingress-nginx
```

### Delete the AKS Cluster and ACR

If you want to remove all Azure resources created for this demo:

```bash
az aks delete \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --yes
```

Delete the Container Registry:

```bash
az acr delete \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --yes
```

Delete the resource group:

```bash
az group delete \
  --name $RESOURCE_GROUP \
  --yes \
  --no-wait
```

**Warning:** Deleting the resource group removes all resources inside it. Make sure it does not contain resources you want to retain.

---

## 17. Demo Presentation Flow

Suggested sequence for a knowledge-sharing session:

| Step | Demonstration | What it shows |
|---:|---|---|
| 1 | Show the application architecture | Microservices design |
| 2 | Show the Azure AKS cluster | Kubernetes infrastructure |
| 3 | Show Docker images in ACR | Containerisation and image registry |
| 4 | Show Deployments and Pods | Kubernetes workload management |
| 5 | Show Kubernetes Services | Internal service discovery |
| 6 | Test Restaurant Service | Individual microservice |
| 7 | Test Payment Service | Simulated payment processing |
| 8 | Create a customer order | End-to-end microservices integration |
| 9 | List created orders | Application API functionality |
| 10 | Test NGINX Ingress internally | Ingress routing |
| 11 | Test public Ingress IP | External application access |
| 12 | Scale the Order Service | Kubernetes scaling |
| 13 | Delete a pod | Kubernetes self-healing |
| 14 | Show application logs | Monitoring and troubleshooting |

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

```bash
git status
```

Add the updated README:

```bash
git add README.md
```

Commit changes:

```bash
git commit -m "Update AKS Food Delivery demo documentation"
```

Push to the remote repository:

```bash
git push
```

---

## Conclusion

This project demonstrates a simple but practical microservices application running on Azure Kubernetes Service.

It provides a foundation for understanding containerisation, Kubernetes orchestration, internal networking, Ingress, service-to-service communication, scaling, and self-healing.

The same concepts can be extended with persistent databases, observability tools, service mesh technologies such as Istio, CI/CD pipelines, and production-grade security controls.