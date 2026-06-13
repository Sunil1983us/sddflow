# Docker Configuration Templates
# Copy the services you need into docker-compose.yml

---

## docker-compose.yml — Full Stack Template

```yaml
version: "3.9"

services:

  # ── Application ──────────────────────────────────────────
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    container_name: ${APP_NAME:-app}
    ports:
      - "${APP_PORT:-8080}:8080"
    environment:
      SPRING_PROFILES_ACTIVE: ${SPRING_PROFILE:-mock}
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/${DB_NAME}
      SPRING_DATASOURCE_USERNAME: ${DB_USER}
      SPRING_DATASOURCE_PASSWORD: ${DB_PASSWORD}
      SPRING_DATA_REDIS_HOST: redis
      SPRING_DATA_REDIS_PORT: 6379
      SPRING_DATA_REDIS_PASSWORD: ${REDIS_PASSWORD}
      SPRING_RABBITMQ_HOST: rabbitmq
      SPRING_RABBITMQ_PORT: 5672
      SPRING_RABBITMQ_USERNAME: ${RABBITMQ_USER}
      SPRING_RABBITMQ_PASSWORD: ${RABBITMQ_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - app-network
    restart: unless-stopped

  # ── PostgreSQL ────────────────────────────────────────────
  postgres:
    image: postgres:15-alpine
    container_name: ${APP_NAME:-app}-postgres
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - app-network
    restart: unless-stopped

  # ── Redis ─────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: ${APP_NAME:-app}-redis
    ports:
      - "${REDIS_PORT:-6379}:6379"
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s
    networks:
      - app-network
    restart: unless-stopped

  # ── RabbitMQ ──────────────────────────────────────────────
  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: ${APP_NAME:-app}-rabbitmq
    ports:
      - "${RABBITMQ_PORT:-5672}:5672"
      - "${RABBITMQ_MGMT_PORT:-15672}:15672"
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
      RABBITMQ_DEFAULT_VHOST: ${RABBITMQ_VHOST:-/}
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 20s
    networks:
      - app-network
    restart: unless-stopped

  # ── MongoDB ───────────────────────────────────────────────
  # Remove if not using MongoDB
  mongodb:
    image: mongo:7-jammy
    container_name: ${APP_NAME:-app}-mongodb
    ports:
      - "${MONGO_PORT:-27017}:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: ${MONGO_DB}
    volumes:
      - mongo-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    networks:
      - app-network
    restart: unless-stopped

  # ── Kafka ─────────────────────────────────────────────────
  # Remove if not using Kafka
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    container_name: ${APP_NAME:-app}-zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - app-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    container_name: ${APP_NAME:-app}-kafka
    ports:
      - "${KAFKA_PORT:-9092}:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    depends_on:
      - zookeeper
    networks:
      - app-network

# ── Volumes ───────────────────────────────────────────────
volumes:
  postgres-data:
  redis-data:
  rabbitmq-data:
  mongo-data:

# ── Networks ──────────────────────────────────────────────
networks:
  app-network:
    driver: bridge
```

---

## .env.example

```bash
# Application
APP_NAME=your-service-name
APP_PORT=8080
SPRING_PROFILE=mock

# PostgreSQL
DB_NAME=ics_db
DB_USER=ics_user
DB_PASSWORD=change_me_dev
POSTGRES_PORT=5432

# Redis
REDIS_PASSWORD=change_me_dev
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_USER=ics_user
RABBITMQ_PASSWORD=change_me_dev
RABBITMQ_VHOST=/
RABBITMQ_PORT=5672
RABBITMQ_MGMT_PORT=15672

# MongoDB (remove if not using)
MONGO_USER=ics_user
MONGO_PASSWORD=change_me_dev
MONGO_DB=ics_db
MONGO_PORT=27017

# Kafka (remove if not using)
KAFKA_PORT=9092
```

---

## Dockerfile

```dockerfile
# Multi-stage build — no dev tools in prod image

# Stage 1 — Build
FROM maven:3.9-eclipse-temurin-21-alpine AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -q
COPY src ./src
RUN mvn package -DskipTests -q

# Stage 2 — Runtime
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# Non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Copy jar from build stage
COPY --from=build /app/target/*.jar app.jar

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

---

## docker-compose.test.yml
# Override for integration tests — lighter stack

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ics_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - "5433:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  rabbitmq:
    image: rabbitmq:3-alpine
    ports:
      - "5673:5672"
```

---

## Useful Commands

```bash
# Start full stack
docker-compose up -d

# Start specific services only
docker-compose up -d postgres redis

# View logs
docker-compose logs -f app
docker-compose logs -f postgres

# Check health
docker-compose ps

# Connect to PostgreSQL
docker exec -it {app}-postgres psql -U ${DB_USER} -d ${DB_NAME}

# Connect to Redis
docker exec -it {app}-redis redis-cli -a ${REDIS_PASSWORD}

# Connect to RabbitMQ management UI
open http://localhost:15672
# Login: RABBITMQ_USER / RABBITMQ_PASSWORD

# Stop and remove volumes (clean slate)
docker-compose down -v

# Rebuild app only
docker-compose up -d --build app
```

---

## Constitution P11 Docker — Crisp Version
# Replace the Docker rows in constitution P11 with this

| Rule | Detail |
|---|---|
| Base image | `-alpine` always — pin exact version |
| User | Non-root: `adduser appuser` |
| Secrets | `.env` file — never in compose or Dockerfile |
| Build | Multi-stage — no Maven/Node in prod image |
| Health | `healthcheck` on every service |
| Volumes | Named volumes for all persistent data |
| Networks | Single bridge network per stack |
| Depends | `condition: service_healthy` — not just `depends_on` |

