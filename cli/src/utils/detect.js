// Project type detection — JavaScript port of setup.sh detect_project_type().
//
// Detection order must match setup.sh detect_project_type() and specify.prompt.md
// Step 0 table. Update all three together when adding a new type.
// INVARIANT: mobile checks must appear before fullstack.

import { existsSync, readdirSync, readFileSync } from 'fs';
import { join } from 'path';

export function detectProjectType(root = '.') {
  const at = (...parts) => join(root, ...parts);
  const has = (...parts) => existsSync(at(...parts));

  const readJson = (path) => {
    try { return JSON.parse(readFileSync(at(path), 'utf8')); }
    catch { return {}; }
  };

  const readText = (...parts) => {
    try { return readFileSync(at(...parts), 'utf8').toLowerCase(); }
    catch { return ''; }
  };

  // Mobile (Flutter/Dart) — before fullstack
  if (has('pubspec.yaml')) return 'mobile';

  // Node.js-based detection
  if (has('package.json')) {
    const pkg = readJson('package.json');
    const deps = Object.keys({ ...pkg.dependencies, ...pkg.devDependencies });

    // Mobile (React Native / Expo) — before fullstack
    if (deps.some(d => d === 'react-native' || d === 'expo')) return 'mobile';

    // Fullstack: JS frontend + separate backend (only after mobile ruled out)
    if (has('pom.xml') || has('build.gradle') || has('go.mod')) return 'fullstack';

    if (deps.includes('electron')) return 'desktop';
    if (['react', 'vue', 'svelte', 'next', 'nuxt'].some(d => deps.includes(d)) ||
        deps.some(d => d.startsWith('angular'))) return 'frontend-spa';
  }

  // Desktop (Tauri)
  if (has('tauri.conf.json') || has('src-tauri', 'tauri.conf.json')) return 'desktop';

  // Serverless
  if (has('serverless.yml')) return 'serverless';
  if (has('template.yaml') && readText('template.yaml').includes('awstemplateformatversion')) {
    return 'serverless';
  }

  // IaC
  const tfFiles = (() => {
    try {
      return readdirSync(root).some(f => f.endsWith('.tf'));
    } catch { return false; }
  })();
  if (tfFiles || has('Pulumi.yaml') || has('cdk.json')) return 'iac';

  // Rust
  if (has('Cargo.toml')) {
    return readText('Cargo.toml').includes('[[bin]]') ? 'cli' : 'library';
  }

  // Go
  if (has('go.mod')) {
    return has('cmd') ? 'cli' : 'backend-service';
  }

  // Python
  if (has('pyproject.toml') || has('requirements.txt')) {
    const pyDeps = readText('requirements.txt') + readText('pyproject.toml');
    if (/pandas|torch|tensorflow|sklearn|keras|jax|xgboost|lightgbm/.test(pyDeps)) {
      return 'data-ml';
    }
    const isLib = /install_requires|build-backend/.test(pyDeps) &&
                  !has('main.py') && !has('app') && !has('src', 'app');
    return isLib ? 'library' : 'backend-service';
  }

  // Java/Kotlin
  if (has('pom.xml') || has('build.gradle') || has('build.gradle.kts')) {
    return 'backend-service';
  }

  return null;
}

export const PROJECT_TYPES = [
  'backend-service', 'frontend-spa', 'mobile', 'fullstack',
  'cli', 'data-ml', 'serverless', 'library', 'iac', 'desktop',
];
