# Vibe-God Enterprise

Enterprise-grade AI automation platform for Digital India - upgraded from the original vibe-god repository to institutional level.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VIBE-GOD ENTERPRISE PLATFORM                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   API GW     │  │   Workers    │  │  Scheduler   │  │  Ollama    │  │
│  │  (FastAPI)   │  │  (Celery)    │  │ (APScheduler)│  │   (LLM)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                 │                │          │
│         └─────────────────┼─────────────────┼────────────────┘          │
│                           ▼                 ▼                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MESSAGE LAYER                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  RabbitMQ   │  │   Kafka     │  │      Redis Cache        │  │   │
│  │  │  (Commands) │  │  (Events)   │  │   (Sessions/Rate Limit) │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                           │                                             │
│         ┌─────────────────┼─────────────────┐                          │
│         ▼                 ▼                 ▼                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  PostgreSQL  │  │  Elasticache │  │   Object     │                 │
│  │  (Primary)   │  │   (Redis)    │  │   Storage    │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
│         │                                                 │            │
│         └─────────────────────┬─────────────────────────┘            │
│                               ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    OBSERVABILITY STACK                           │   │
│  │  Prometheus │ Grafana │ Jaeger │ OpenTelemetry │ AlertManager   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## ✨ Enterprise Features

### 🔒 Security & Compliance
- **Secrets Management**: HashiCorp Vault, AWS Secrets Manager, SOPS, Environment variables
- **Authentication**: JWT (RS256), OIDC/OAuth2, API Keys, mTLS
- **Authorization**: RBAC + ABAC with fine-grained permissions
- **Encryption**: AES-256 at rest, TLS 1.3 in transit, KMS integration
- **Compliance**: SOC2, ISO27001, GDPR ready with audit logging

### 📊 Observability
- **Structured Logging**: JSON format with OpenTelemetry correlation
- **Distributed Tracing**: Jaeger with B3 propagation
- **Metrics**: Prometheus + Grafana with custom business metrics
- **Health Checks**: Liveness, readiness, startup probes
- **Alerting**: AlertManager with PagerDuty/Slack/Email integrations

### 🛡️ Resilience Patterns
- **Circuit Breakers**: Three-state (Closed/Open/Half-Open) with metrics
- **Retry Policies**: Exponential backoff with jitter (multiple strategies)
- **Rate Limiting**: Token bucket, sliding window, fixed window algorithms
- **Bulkhead Isolation**: Semaphore and thread pool based isolation
- **Timeout Management**: Deadline propagation with context vars

### 📦 Messaging
- **RabbitMQ**: Commands, RPC, durable queues, publisher confirms
- **Kafka**: High-throughput events, exactly-once semantics
- **Redis**: Caching, sessions, distributed rate limiting
- **Middleware Chain**: Cross-cutting concerns (logging, tracing, auth)

### 🗄️ Database
- **PostgreSQL**: Async SQLAlchemy 2.0 with connection pooling
- **Read Replicas**: Automatic read/write splitting
- **Migrations**: Alembic with async support
- **Repository Pattern**: Type-safe CRUD with soft delete support

### ☸️ Kubernetes Native
- **Helm Charts**: Production-ready with values per environment
- **Kustomize**: Base + overlay pattern for dev/staging/prod
- **Network Policies**: Zero-trust network segmentation
- **Pod Disruption Budgets**: High availability guarantees
- **Horizontal Pod Autoscaling**: CPU, memory, custom metrics
- **Service Mesh Ready**: Istio mTLS, traffic management

### 🏗️ Infrastructure as Code
- **Terraform Modules**: VPC, EKS, RDS, ElastiCache, MQ, MSK
- **Multi-environment**: Dev, Staging, Production with workspaces
- **GitOps Ready**: ArgoCD/Flux compatible

### 🔄 CI/CD Pipeline
- **GitHub Actions**: Lint, test, security scan, build, deploy
- **Security**: Trivy (containers), Semgrep (code), Bandit (Python)
- **Quality Gates**: Coverage thresholds, type checking, linting
- **Progressive Delivery**: Canary, blue-green deployments

## 🚀 Quick Start

### Development with Docker Compose
```bash
cd docker
docker-compose up -d

# Services available at:
# API: http://localhost:8000
# RabbitMQ Management: http://localhost:15672
# Grafana: http://localhost:3000
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
```

### Production Deployment
```bash
# 1. Deploy infrastructure
cd terraform/environments/prod
terraform init
terraform plan
terraform apply

# 2. Deploy to Kubernetes
cd ../../k8s/overlays/prod
kubectl apply -k .

# 3. Or use Helm
cd ../../helm/vibe-god
helm install vibe-god . -f values-prod.yaml -n vibe-god
```

## 📁 Project Structure

```
vibe-god-enterprise/
├── .github/workflows/          # CI/CD pipelines
├── docker/                     # Dockerfiles & compose files
├── helm/vibe-god/              # Helm charts
├── k8s/                        # Kubernetes manifests (Kustomize)
│   ├── base/                   # Base resources
│   └── overlays/               # Environment overlays
├── terraform/                  # Infrastructure as Code
│   ├── modules/                # Reusable modules
│   └── environments/           # Environment configs
├── python/                     # Python monorepo
│   ├── apps/                   # Services
│   │   ├── api/               # FastAPI gateway
│   │   ├── worker/            # Background workers
│   │   └── scheduler/         # Task scheduler
│   ├── libs/                   # Shared libraries
│   │   ├── observability/     # Logging, tracing, metrics
│   │   ├── security/          # Auth, RBAC, secrets, encryption
│   │   ├── resilience/        # Circuit breaker, retry, rate limit
│   │   ├── messaging/         # RabbitMQ, Kafka clients
│   │   ├── database/          # SQLAlchemy, migrations, repos
│   │   └── testing/           # Test utilities
│   └── tools/                  # CLI tools
├── tests/                      # Test suites
│   ├── contract/              # Pact contract tests
│   ├── integration/           # Integration tests
│   ├── e2e/                   # Playwright E2E tests
│   ├── performance/           # k6 load tests
│   └── chaos/                 # Litmus chaos experiments
├── docs/                       # Documentation
│   ├── architecture/          # ADRs, diagrams
│   ├── runbooks/              # Operational runbooks
│   ├── api/                   # OpenAPI specs
│   └── compliance/            # SOC2, GDPR docs
└── scripts/                    # Operational scripts
```

## 🛠️ Development

### Setup
```bash
# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check .
black --check .
mypy python/
```

### Code Quality Standards
- **Type Hints**: 100% coverage required (mypy strict)
- **Test Coverage**: >80% (pytest-cov)
- **Linting**: ruff + black (line length 100)
- **Security**: bandit + trufflehog in CI
- **Documentation**: Google-style docstrings

## 🔧 Configuration

### Environment Variables
```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_FORMAT=json
APP_VERSION=1.0.0

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://:pass@host:6379/0

# Message Brokers
RABBITMQ_URL=amqp://user:pass@host:5672/
KAFKA_BOOTSTRAP_SERVERS=host1:9092,host2:9092

# LLM
OLLAMA_URL=http://ollama:11434

# Observability
OTLP_ENDPOINT=http://jaeger:4317
SENTRY_DSN=https://xxx@sentry.io/xxx

# Security
JWT_SECRET=xxx
ENCRYPTION_KEY=xxx
```

### Secrets Management
Secrets are loaded from multiple backends in priority order:
1. Environment variables
2. HashiCorp Vault
3. AWS Secrets Manager
4. SOPS-encrypted files (GitOps)
5. Local encrypted files (development)
6. Default values

## 📖 Documentation

- [Architecture Decision Records](docs/architecture/)
- [API Documentation](docs/api/)
- [Runbooks](docs/runbooks/)
- [Compliance](docs/compliance/)
- [Deployment Guide](docs/deployment.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run pre-commit hooks
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built on top of the original [vibe-god](https://github.com/vikassangwal/vibe-god) by [Vikassangwal](https://github.com/vikassangwal).

---

**Vibe-God Enterprise** - Powering Digital India Automation at Scale 🇮🇳