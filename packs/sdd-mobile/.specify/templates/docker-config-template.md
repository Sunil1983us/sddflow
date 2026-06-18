# CI Build Container — Mobile (React Native / Flutter)
# A Docker image used by CI to run the mobile build/test pipeline.
# This is NOT a runtime image for the app — mobile apps ship as
# .apk/.aab (Android) or .ipa (iOS), not as containers.

---

## Scope

This template covers the **Android** build/test pipeline, which can run
fully inside a Linux container: lint, unit tests, JS/TS bundling (Metro/
Flutter build), and Gradle assembly of `.apk` / `.aab` artifacts.

**iOS builds cannot run in this container** — see "Platform Constraint —
iOS" below.

---

## Dockerfile — React Native (Android) CI Build Image

```dockerfile
# CI build image — Node + Java + Android SDK for RN Android builds
# Pin exact versions (constitution OPS-7)

FROM eclipse-temurin:17-jdk-jammy AS ci-build

# ── Node.js (pin exact version matching package.json "engines") ──────
ARG NODE_VERSION=20.11.1
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl unzip git ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Android SDK (cmdline-tools + platform + build-tools) ──────────────
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=${ANDROID_HOME}
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools

ARG ANDROID_CMDLINE_TOOLS_VERSION=11076708
ARG ANDROID_PLATFORM=android-34
ARG ANDROID_BUILD_TOOLS=34.0.0

RUN mkdir -p ${ANDROID_HOME}/cmdline-tools \
    && curl -fsSL -o /tmp/cmdline-tools.zip \
        "https://dl.google.com/android/repository/commandlinetools-linux-${ANDROID_CMDLINE_TOOLS_VERSION}_latest.zip" \
    && unzip -q /tmp/cmdline-tools.zip -d ${ANDROID_HOME}/cmdline-tools \
    && mv ${ANDROID_HOME}/cmdline-tools/cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest \
    && rm /tmp/cmdline-tools.zip \
    && yes | sdkmanager --licenses \
    && sdkmanager \
        "platform-tools" \
        "platforms;${ANDROID_PLATFORM}" \
        "build-tools;${ANDROID_BUILD_TOOLS}"

# ── Non-root build user ────────────────────────────────────────────────
RUN groupadd -r ciuser && useradd -r -g ciuser -m ciuser
USER ciuser
WORKDIR /workspace

# ── App dependencies (cached layer) ────────────────────────────────────
COPY --chown=ciuser:ciuser package.json package-lock.json ./
RUN npm ci

COPY --chown=ciuser:ciuser . .

# Health check — confirms toolchain is wired correctly
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD node --version && java -version && sdkmanager --version || exit 1

# Default: lint + unit test + Android assemble (override in CI job step)
CMD ["sh", "-c", "npm run lint && npm test -- --ci && cd android && ./gradlew assembleRelease"]
```

---

## Dockerfile — Flutter (Android) CI Build Image (alternative)

If this project's Tech Stack table (constitution.md Part 2) specifies
Flutter instead of React Native, use this image instead:

```dockerfile
FROM ghcr.io/cirruslabs/flutter:3.22.0 AS ci-build

# Android SDK is bundled in the cirruslabs/flutter image.
# Pin the exact Flutter image tag — never use ":latest" (constitution OPS-7).

RUN groupadd -r ciuser && useradd -r -g ciuser -m ciuser
USER ciuser
WORKDIR /workspace

COPY --chown=ciuser:ciuser pubspec.yaml pubspec.lock ./
RUN flutter pub get

COPY --chown=ciuser:ciuser . .

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD flutter --version || exit 1

CMD ["sh", "-c", "flutter analyze && flutter test && flutter build apk --release"]
```

---

## docker-compose.ci.yml — Local CI Reproduction

```yaml
version: "3.9"

services:
  mobile-ci:
    build:
      context: .
      dockerfile: docker/Dockerfile.ci
    container_name: ${APP_NAME:-mobile}-ci
    environment:
      # Build-time config injected via CI secrets — never committed
      - NODE_ENV=test
      - ANDROID_KEYSTORE_PATH=/secrets/release.keystore
      - ANDROID_KEYSTORE_PASSWORD=${ANDROID_KEYSTORE_PASSWORD}
    volumes:
      - .:/workspace
      - gradle-cache:/home/ciuser/.gradle
      # Mount secrets read-only — never bake into the image
      - ./secrets:/secrets:ro
    working_dir: /workspace

volumes:
  gradle-cache:
```

---

## .env.example

```bash
# Build-time configuration (injected by CI — never committed with real values)
ANDROID_KEYSTORE_PASSWORD=change_me_in_ci_secrets
ANDROID_KEY_ALIAS=release
ANDROID_KEY_ALIAS_PASSWORD=change_me_in_ci_secrets

# OTA update channel (CodePush / Expo EAS Update — if applicable)
OTA_DEPLOYMENT_KEY=change_me_in_ci_secrets

# Crash reporting (Crashlytics/Sentry) — symbol upload tokens
SENTRY_AUTH_TOKEN=change_me_in_ci_secrets
```

---

## Platform Constraint — iOS

Xcode/iOS builds **cannot run inside Linux containers** — Apple's
toolchain (Xcode, simulators, codesign, xcodebuild) requires macOS.

**Recommendation:**
- Use a **GitHub-hosted macOS runner** (`runs-on: macos-latest`) for the
  iOS lane of the CI pipeline — simplest if already on GitHub Actions.
- Alternatively, **Xcode Cloud** (Apple-native, tightly integrated with
  App Store Connect) or **Bitrise** (cross-platform mobile CI with managed
  macOS stacks) if a dedicated mobile CI provider is preferred.
- Code signing certificates and provisioning profiles must be injected via
  the chosen CI's secret store (e.g. GitHub Actions encrypted secrets +
  `fastlane match`) — never committed to the repo.
- The Android lane (this Dockerfile) and the iOS lane (macOS runner) run
  as two parallel jobs in the same pipeline; both must pass before a
  release build is promoted.

---

## Useful Commands

```bash
# Build the CI image locally
docker build -t ${APP_NAME:-mobile}-ci -f docker/Dockerfile.ci .

# Run lint + unit tests inside the container
docker run --rm -v $(pwd):/workspace ${APP_NAME:-mobile}-ci \
  sh -c "npm run lint && npm test -- --ci"

# Run a full Android release assembly (requires keystore mounted)
docker compose -f docker-compose.ci.yml run --rm mobile-ci \
  sh -c "cd android && ./gradlew assembleRelease"

# Verify toolchain versions match what's pinned in the Dockerfile
docker run --rm ${APP_NAME:-mobile}-ci sh -c "node --version && java -version && sdkmanager --version"
```

---

## Constitution Reference
This template implements the rules in constitution.md Part 1 →
"## Containerization & Build Pipeline (OPS-7)" table. That table is the
source of truth — do not duplicate or diverge from it here. Key rules it
covers: CI build agent runs in a pinned Docker container (Node + Android
SDK + Java for RN Android, or equivalent Flutter image), iOS builds use a
macOS CI runner (platform constraint — see above), code signing
certificates/keystores injected via CI secrets, app-store pipeline driven
by Fastlane (or equivalent), OTA updates versioned with staged rollout,
Crashlytics/Sentry initialised at startup with CI-uploaded symbol maps,
and a smoke-build step before any store submission job.
