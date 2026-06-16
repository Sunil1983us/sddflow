# Kubernetes Manifests
# Use instead of docker-config-template.md when Orchestration = Kubernetes
# Copy the manifests you need into k8s/

---

## Deployment — k8s/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app-name}
  labels:
    app: {app-name}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {app-name}
  template:
    metadata:
      labels:
        app: {app-name}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: {app-name}
          image: {registry}/{app-name}:{tag}
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: {app-name}-config
            - secretRef:
                name: {app-name}-secrets
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 5
```

---

## Service — k8s/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {app-name}
spec:
  type: ClusterIP
  selector:
    app: {app-name}
  ports:
    - port: 80
      targetPort: 8080
```

---

## HorizontalPodAutoscaler — k8s/hpa.yaml

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {app-name}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {app-name}
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## NetworkPolicy — k8s/networkpolicy.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {app-name}
spec:
  podSelector:
    matchLabels:
      app: {app-name}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector: {}   # same-namespace only — narrow further per service
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to: []                # narrow to DB / downstream service CIDRs
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 443
```

---

## ConfigMap — k8s/configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {app-name}-config
data:
  SPRING_PROFILES_ACTIVE: "prod"
  SPRING_DATASOURCE_URL: "jdbc:postgresql://{db-host}:5432/{db-name}"
```

---

## Secret — k8s/secret.yaml
# Never commit populated values. This file shows the shape only — real
# clusters source secrets from Vault / cloud secrets manager via an
# external-secrets / CSI driver controller, not a checked-in Secret.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {app-name}-secrets
type: Opaque
stringData:
  DB_USER: "{from-secrets-manager}"
  DB_PASSWORD: "{from-secrets-manager}"
```

---

## Useful Commands

```bash
# Apply all manifests
kubectl apply -f k8s/

# Check rollout status
kubectl rollout status deployment/{app-name}

# View pods + logs
kubectl get pods -l app={app-name}
kubectl logs -f deployment/{app-name}

# Check HPA
kubectl describe hpa {app-name}

# Rollback (used in runbook-template.md §6)
kubectl rollout undo deployment/{app-name}
```

---

## Constitution Reference
These manifests implement the same rules as constitution.md Part 1 →
"Containerization (OPS-7)" table (non-root user, health checks, resource
limits, secrets never in plain config, multi-stage image from
docker-config-template.md's Dockerfile). Use this template instead of
docker-config-template.md's docker-compose.yml when Tech Stack →
Orchestration = Kubernetes; the Dockerfile and .env.example in
docker-config-template.md still apply.
