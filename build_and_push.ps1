# ============================================================
# Build and Push Docker Images for SentinelSQL
# Repository: jimsonrats
# ============================================================

$Repo = "jimsonrats"
$Tag = "latest"

$ErrorActionPreference = "Stop"

# Array of services in the format "directory:image_name"
$Services = @(
  "l1-identity-context:l1-identity",
  "l2-knowledge-graph-v3:l2-knowledge",
  "l3-intelligent-retrieval:l3-retrieval",
  "l4-policy-resolution:l4-policy",
  "l5-secure-generation:l5-generation",
  "l6-multi-gate-validation:l6-validation",
  "l7-secure-execution:l7-execution",
  "l8-audit-anomaly:l8-audit",
  "front-end:front-end",
  "frontend:frontend"
)

Write-Host "Starting build and push to $Repo..." -ForegroundColor Cyan

foreach ($Service in $Services) {
    $Parts = $Service -split ":"
    $Dir = $Parts[0]
    $AppName = $Parts[1]
    
    $ImageName = "$Repo/$AppName`:$Tag"
    
    Write-Host "----------------------------------------"
    Write-Host "Building $ImageName from ./$Dir" -ForegroundColor Yellow
    Write-Host "----------------------------------------"
    
    # Build the image
    docker build -t $ImageName "./$Dir"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully built $ImageName" -ForegroundColor Green
        Write-Host "Pushing $ImageName to Docker Hub..." -ForegroundColor Yellow
        docker push $ImageName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Successfully pushed $ImageName" -ForegroundColor Green
        } else {
            Write-Host "Failed to push $ImageName" -ForegroundColor Red
            Write-Host "Did you run 'docker login'?" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Failed to build $ImageName" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "All images successfully built and pushed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
