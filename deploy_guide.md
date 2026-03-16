Step 1 — Build & Push


.\build_and_push.ps1
This builds 9 images (jimsonrats/l1-identity:latest through jimsonrats/react-frontend:latest) and pushes to Docker Hub.

Step 2 — Deploy to K8s


# Create namespace first
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/namespace-limits.yaml

# ConfigMap & Secrets (fill in real values first!)
kubectl apply -f k8s/configmap.yaml

# Deploy services
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/l1-identity.yaml
kubectl apply -f k8s/l2-knowledge.yaml
kubectl apply -f k8s/l3-retrieval.yaml
kubectl apply -f k8s/l4-policy.yaml
kubectl apply -f k8s/l5-generation.yaml
kubectl apply -f k8s/l6-validation.yaml
kubectl apply -f k8s/l7-execution.yaml
kubectl apply -f k8s/l8-audit.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/ingress-layers.yaml
Things to note before deploying:

ConfigMap has placeholders — configmap.yaml has REPLACE_WITH_* values for Neo4j, Postgres, Azure, etc. You need to fill those in with your actual credentials, or create a sentinelsql-secrets Secret with the sensitive values.

Duplicate frontend manifests — You have both front-end.yaml (port 8000, old Streamlit?) and frontend.yaml (port 80, React). The ingress routes to frontend on port 80, so use frontend.yaml (which matches build_and_push.ps1's react-frontend image).

nodeSelector/tolerations — All manifests require workload: sentinelsql node label and matching taint. Make sure your local k8s nodes have these, or remove the nodeSelector/tolerations blocks for local deployment.

No sentinelsql-secrets manifest — The deployments reference secretRef: sentinelsql-secrets but there's no secrets YAML. You'll need to create it:


kubectl create secret generic sentinelsql-secrets -n sentinelsql \
  --from-literal=NEO4J_PASSWORD=... \
  --from-literal=AZURE_OPENAI_API_KEY=... \
  --from-literal=MYSQL_PASSWORD=... \
  # etc.
Want me to help with any of these — like populating the configmap, creating the secrets manifest, or removing the nodeSelector/tolerations for local deployment?