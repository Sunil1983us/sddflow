# Unit tests for sdd/utils/detect.py's project-type auto-detection.
#
# detect_project_type() had no dedicated test coverage at all before this --
# only ever mocked out in test_init.py. This exercises it directly against
# ~20 synthetic project fixtures, the same set mirrored in cli/tests/
# detect.test.js and packs/_shared/tests/test-detect-fixtures.sh, so all
# three implementations are asserted against identical inputs. Building
# these fixtures surfaced two real, previously-unnoticed bugs (both fixed
# alongside this test): "react-native-web" was misclassified as mobile
# (setup.sh/setup.ps1 only), and modern Angular projects (scoped
# "@angular/core" style dependencies) were never detected at all
# (detect.py/detect.js only, via a startswith() check that scoped package
# names never satisfy).
from __future__ import annotations

import json

import pytest

from sdd.utils.detect import detect_project_type


def _write(root, relpath: str, content: str) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _pkg(**deps) -> str:
    return json.dumps({"dependencies": deps})


FIXTURES = [
    ("flutter", {"pubspec.yaml": "name: demo\n"}, "mobile"),
    ("react-native", {"package.json": _pkg(**{"react-native": "^0.73.0"})}, "mobile"),
    ("expo", {"package.json": _pkg(expo="^50.0.0")}, "mobile"),
    (
        "react-native-web-is-not-mobile",
        {"package.json": _pkg(**{"react-native-web": "^0.19.0", "react": "^18.0.0"})},
        "frontend-spa",
    ),
    (
        "react-native-plus-backend-monorepo",
        {
            "package.json": _pkg(**{"react-native": "^0.73.0"}),
            "pom.xml": "<project></project>",
        },
        "mobile",  # INVARIANT: mobile checked before fullstack
    ),
    (
        "js-frontend-plus-backend",
        {"package.json": _pkg(react="^18.0.0"), "pom.xml": "<project></project>"},
        "fullstack",
    ),
    ("electron", {"package.json": _pkg(electron="^28.0.0")}, "desktop"),
    ("react", {"package.json": _pkg(react="^18.0.0")}, "frontend-spa"),
    ("vue", {"package.json": _pkg(vue="^3.4.0")}, "frontend-spa"),
    (
        "angular-scoped-packages",
        {
            "package.json": _pkg(
                **{"@angular/core": "^17.0.0", "@angular/common": "^17.0.0"}
            )
        },
        "frontend-spa",
    ),
    (
        "sveltekit",
        {"package.json": _pkg(svelte="^4.0.0", **{"@sveltejs/kit": "^2.0.0"})},
        "frontend-spa",
    ),
    ("tauri", {"tauri.conf.json": "{}"}, "desktop"),
    ("serverless", {"serverless.yml": "service: demo\n"}, "serverless"),
    ("terraform", {"main.tf": 'resource "null_resource" "x" {}\n'}, "iac"),
    (
        "rust-cli",
        {"Cargo.toml": '[package]\nname = "demo"\n\n[[bin]]\nname = "demo"\n'},
        "cli",
    ),
    ("rust-library", {"Cargo.toml": '[package]\nname = "demo"\n'}, "library"),
    ("go-cli", {"go.mod": "module demo\n", "cmd/main.go": "package main\n"}, "cli"),
    ("go-backend", {"go.mod": "module demo\n"}, "backend-service"),
    (
        "python-ml",
        {"requirements.txt": "pandas>=2.0.0\nnumpy>=1.24.0\n"},
        "data-ml",
    ),
    (
        "python-library",
        {"pyproject.toml": "[project]\nname = 'demo'\nbuild-backend = 'hatchling'\n"},
        "library",
    ),
    ("python-backend", {"requirements.txt": "click>=8.0.0\n"}, "backend-service"),
    ("java-backend", {"pom.xml": "<project></project>"}, "backend-service"),
    ("empty", {}, None),
]


@pytest.mark.parametrize("name,files,expected", FIXTURES, ids=[f[0] for f in FIXTURES])
def test_detect_project_type_fixtures(tmp_path, monkeypatch, name, files, expected):
    monkeypatch.chdir(tmp_path)
    for relpath, content in files.items():
        _write(tmp_path, relpath, content)
    assert detect_project_type(str(tmp_path)) == expected
