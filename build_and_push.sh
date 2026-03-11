#!/bin/bash
# ============================================================
# Build and Push Docker Images for SentinelSQL
# Repository: jimsonrats
# ============================================================

REPO="jimsonrats"
TAG="latest"

# Array of services in the format "directory:image_name"
SERVICES=(
  "l1-identity-context:l1-identity"
  "l2-knowledge-graph-v3:l2-knowledge"
  "l3-intelligent-retrieval:l3-retrieval"
  "l4-policy-resolution:l4-policy"
  "l5-secure-generation:l5-generation"
  "l6-multi-gate-validation:l6-validation"
  "l7-secure-execution:l7-execution"
  "l8-audit-anomaly:l8-audit"
  "front-end:front-end"
  "frontend:frontend"
)

echo "Starting build and push to $REPO..."

# Ensure we're logged in (optional, will prompt if needed but better to do it before running)
# docker login

for service in "${SERVICES[@]}"; do
    DIR="${service%%:*}"
    APP_NAME="${service##*:}"
    IMAGE_NAME="$REPO/$APP_NAME:$TAG"
    
    echo "----------------------------------------"
    echo "Building $IMAGE_NAME from ./$DIR"
    echo "----------------------------------------"
    
    # Build the image
    docker build -t "$IMAGE_NAME" "./$DIR"
    
    if [ $? -eq 0 ]; then
        echo "Successfully built $IMAGE_NAME"
        echo "Pushing $IMAGE_NAME to Docker Hub..."
        docker push "$IMAGE_NAME"
        
        if [ $? -eq 0 ]; then
            echo "Successfully pushed $IMAGE_NAME"
        else
            echo "Failed to push $IMAGE_NAME"
            echo "Did you run 'docker login'?"
            exit 1
        fi
    else
        echo "Failed to build $IMAGE_NAME"
        exit 1
    fi
done

echo ""
echo "========================================"
echo "All images successfully built and pushed!"
echo "========================================"
echo ""
echo "To update your Kubernetes manifests to use these images, run:"
echo "sed -i 's/\${ACR_NAME}.azurecr.io\/sentinelsql/jimsonrats/g' k8s/*.yaml"
echo ""
