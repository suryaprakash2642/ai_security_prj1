## Build → Push → Rollout for a single service

The pattern is always the same 4 steps. Replace `l5-generation` / l5-secure-generation with the service you're working on:

**Step 1 — Commit your changes**
```powershell
cd c:\Users\jimso\Downloads\aisecupd\ai_security_prj1
git add <changed-files>
git commit --amend --no-edit     # keep amending the same commit, or use -m "msg"
git push --force-with-lease
```

**Step 2 — Build the Docker image** (from the service directory)
```powershell
cd l5-secure-generation
docker build -t jimsonrats/l5-generation:latest .
```

**Step 3 — Push to registry**
```powershell
docker push jimsonrats/l5-generation:latest
```

**Step 4 — Rollout restart + wait**
```powershell
kubectl rollout restart deployment/l5-generation -n sentinelsql
kubectl rollout status deployment/l5-generation -n sentinelsql --timeout=60s
```

**Service → image → deployment mapping:**

| Service dir | Docker image | K8s deployment |
|---|---|---|
| l3-intelligent-retrieval | `jimsonrats/l3-retrieval` | `l3-retrieval` |
| l4-policy-resolution | `jimsonrats/l4-policy` | `l4-policy` |
| l5-secure-generation | `jimsonrats/l5-generation` | `l5-generation` |
| l6-multi-gate-validation | `jimsonrats/l6-validation` | `l6-validation` |
| l7-secure-execution | `jimsonrats/l7-execution` | `l7-execution` |
| frontend | `jimsonrats/frontend` | frontend |

Made changes.