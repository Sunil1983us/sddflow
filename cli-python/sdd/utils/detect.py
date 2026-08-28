# Project type detection — Python port of cli/src/utils/detect.js
#
# Detection order must match setup.sh detect_project_type() and specify.prompt.md
# Step 0 table. Update all three together when adding a new type.
# INVARIANT: mobile checks must appear before fullstack.
from __future__ import annotations

import json
from pathlib import Path

PROJECT_TYPES = [
    "backend-service",
    "frontend-spa",
    "mobile",
    "fullstack",
    "cli",
    "data-ml",
    "serverless",
    "library",
    "iac",
    "desktop",
]


def detect_project_type(root: str = ".") -> str | None:
    r = Path(root)

    def has(*parts: str) -> bool:
        return (r / Path(*parts)).exists()

    def read_json(path: str) -> dict:
        try:
            return json.loads((r / path).read_text(encoding="utf-8"))
        except Exception:
            return {}

    def read_text(*parts: str) -> str:
        try:
            return (r / Path(*parts)).read_text(encoding="utf-8").lower()
        except Exception:
            return ""

    # Mobile (Flutter/Dart) — before fullstack
    if has("pubspec.yaml"):
        return "mobile"

    # Node.js-based detection
    if has("package.json"):
        pkg = read_json("package.json")
        deps = list(pkg.get("dependencies", {}).keys()) + list(
            pkg.get("devDependencies", {}).keys()
        )

        # Mobile (React Native / Expo) — before fullstack
        if "react-native" in deps or "expo" in deps:
            return "mobile"

        # Fullstack: JS frontend + separate backend (only after mobile ruled out)
        if has("pom.xml") or has("build.gradle") or has("go.mod"):
            return "fullstack"

        if "electron" in deps:
            return "desktop"

        spa_frameworks = {"react", "vue", "svelte", "next", "nuxt"}
        # "angular" in d (substring), not startswith: every real Angular 2+
        # project depends on scoped packages like "@angular/core", which
        # don't start with "angular" -- only ancient AngularJS 1.x used the
        # bare "angular" package name.
        if spa_frameworks & set(deps) or any("angular" in d for d in deps):
            return "frontend-spa"

    # Desktop (Tauri)
    if has("tauri.conf.json") or has("src-tauri", "tauri.conf.json"):
        return "desktop"

    # Serverless
    if has("serverless.yml"):
        return "serverless"
    if has("template.yaml") and "awstemplateformatversion" in read_text(
        "template.yaml"
    ):
        return "serverless"

    # IaC
    tf_files = list(r.glob("*.tf"))
    if tf_files or has("Pulumi.yaml") or has("cdk.json"):
        return "iac"

    # Rust
    if has("Cargo.toml"):
        return "cli" if "[[bin]]" in read_text("Cargo.toml") else "library"

    # Go
    if has("go.mod"):
        return "cli" if has("cmd") else "backend-service"

    # Python
    if has("pyproject.toml") or has("requirements.txt"):
        py_deps = read_text("requirements.txt") + read_text("pyproject.toml")
        ml_libs = {
            "pandas",
            "torch",
            "tensorflow",
            "sklearn",
            "keras",
            "jax",
            "xgboost",
            "lightgbm",
        }
        if any(lib in py_deps for lib in ml_libs):
            return "data-ml"
        is_lib = (
            ("install_requires" in py_deps or "build-backend" in py_deps)
            and not has("main.py")
            and not has("app")
            and not has("src", "app")
        )
        return "library" if is_lib else "backend-service"

    # Java/Kotlin
    if has("pom.xml") or has("build.gradle") or has("build.gradle.kts"):
        return "backend-service"

    return None
