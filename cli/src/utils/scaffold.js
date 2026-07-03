import { existsSync, cpSync, readdirSync } from 'fs';
import { join, relative, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Types that have a dedicated pack. Everything else → sdd-universal.
export const TYPE_TO_PACK = {
  'backend-service': 'sdd-backend-service',
  'frontend-spa':    'sdd-frontend-spa',
  'fullstack':       'sdd-fullstack',
  'mobile':          'sdd-mobile',
};

export const PACK_DESCRIPTIONS = {
  'sdd-backend-service': 'REST APIs, microservices, databases, messaging',
  'sdd-frontend-spa':    'React / Vue / Angular single-page applications',
  'sdd-fullstack':       'Frontend + backend in the same repository',
  'sdd-mobile':          'React Native or Flutter mobile apps',
  'sdd-universal':       'Any project type — auto-detects from your codebase',
};

export const ALL_PACKS = Object.keys(PACK_DESCRIPTIONS);
export const UNIVERSAL_PACK = 'sdd-universal';

/**
 * Resolve the directory containing the sdd-* pack folders.
 *
 * Search order:
 * 1. Bundled packs inside the installed package  (npm install -g sdd-init)
 *    → <package-root>/packs/
 * 2. Repository root packs/ directory            (dev / npm link)
 *    → <repo-root>/packs/
 */
export function getPacksDir() {
  // 1. Bundled: cli/packs/ sits two levels up from cli/src/utils/
  const bundled = resolve(__dirname, '..', '..', 'packs');
  if (existsSync(bundled) && readdirSync(bundled).length > 0) {
    return bundled;
  }

  // 2. Dev / npm link: walk up to repo root from cli/src/utils/
  const repoPacks = resolve(__dirname, '..', '..', '..', '..', 'packs');
  if (existsSync(repoPacks) && readdirSync(repoPacks).length > 0) {
    return repoPacks;
  }

  throw new Error(
    'SDD pack files not found.\n' +
    '  Installed via npm?  Try: npm install -g sddkit --force\n' +
    '  Running from source? Ensure you cloned the full repository.'
  );
}

/** Return the recommended pack name for a detected project type. */
export function recommendedPack(projectType) {
  return TYPE_TO_PACK[projectType] ?? UNIVERSAL_PACK;
}

/**
 * Copy pack files into dest. Existing files are never overwritten.
 * Returns the number of files copied.
 */
export function scaffoldPack(packName, dest = '.') {
  const packsDir = getPacksDir();
  const packSrc = join(packsDir, packName);

  if (!existsSync(packSrc)) {
    throw new Error(
      `Pack '${packName}' not found in ${packsDir}.\n` +
      `Available packs: ${ALL_PACKS.join(', ')}`
    );
  }

  let count = 0;

  // cpSync with filter: skip files that already exist at destination
  cpSync(packSrc, dest, {
    recursive: true,
    filter: (src) => {
      const rel = relative(packSrc, src);
      if (!rel) return true;           // always recurse into the root
      const dst = join(dest, rel);
      if (existsSync(dst)) return false;  // skip existing files
      count++;
      return true;
    },
  });

  return count;
}
