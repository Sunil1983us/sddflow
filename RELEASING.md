# Releasing

How a version bump in this repo turns into a GitHub Release and a PyPI
publish. Written for maintainers (human or AI) cutting a release, and for
the one-time PyPI setup only the project owner can do.

---

## The process

1. Ship the version bump normally — the `version-bump` skill, a commit,
   merged to `main`. This alone does **not** release or publish anything.
2. Once `main` has the version you want to release, tag it and push the
   tag:
   ```bash
   git checkout main && git pull
   git tag v3.4.0          # must exactly match cli-python/sdd/__init__.py's __version__
   git push origin v3.4.0
   ```
   The tag push is the deliberate trigger — nothing here fires
   automatically on every merge to `main`. This also means a `main`
   commit can be reverted or hotfixed without accidentally releasing
   half-finished work.
3. Pushing the tag fires two independent GitHub Actions workflows:
   - **`.github/workflows/release.yml`** — verifies the tag matches
     `__version__`, pulls that version's section out of `CHANGELOG.md`,
     and creates a GitHub Release with it. Works immediately, no setup
     needed.
   - **`.github/workflows/publish-pypi.yml`** — builds the wheel/sdist
     (same bundle-packs + build steps as `cli-python/publish.sh` and
     CI's `package-verify` job) and publishes to PyPI via **Trusted
     Publishing (OIDC)** — no `PYPI_TOKEN` secret involved. **This step
     fails until the one-time PyPI setup below is done** — that's
     expected and safe (nothing is uploaded, no token exists to leak);
     once configured, re-run the failed job from the Actions tab instead
     of re-tagging.

Both workflows independently re-verify the tag equals
`cli-python/sdd/__init__.py`'s `__version__` before doing anything —
a mistagged release (wrong version number in the tag) fails loudly
instead of shipping something that doesn't match its own manifest.

Git tags only start from whatever version is current when this process
was introduced (v3.4.0) — the 159 versions before that were never
tagged and are not being retroactively tagged; their history lives in
`CHANGELOG.md` and commit history instead.

Node CLI (`cli/`) publishing is **not** part of this automation — it
stays a manual `npm publish` from a maintainer's machine (see
`cli/README.md`), deliberately: the Node CLI is frozen at
scaffolding-only, maintenance-mode, and publishes rarely enough that
building OIDC automation for it isn't worth it right now.

---

## One-time PyPI setup (project owner only — can't be done from this repo)

PyPI Trusted Publishing links a specific GitHub repo + workflow file +
environment to a PyPI project, so GitHub Actions can request short-lived
publish credentials via OIDC with no stored token at all. This has to be
configured on PyPI's own site by whoever owns the `sddflow` project
there:

1. Go to https://pypi.org/manage/project/sddflow/settings/publishing/
   (log in as the project owner first).
2. Under "Add a new publisher", choose **GitHub** and fill in:
   - **Owner**: `Sunil1983us` (or whatever the repo's current owner is)
   - **Repository name**: `sddflow`
   - **Workflow name**: `publish-pypi.yml`
   - **Environment name**: `pypi`
3. Save. No token, no secret, nothing else to configure in this repo —
   `publish-pypi.yml` already targets the `pypi` GitHub Environment and
   requests `id-token: write`, which is everything Trusted Publishing
   needs on the GitHub side.
4. (Optional but recommended) In this repo's Settings → Environments →
   `pypi`, add required reviewers or restrict which branches/tags can
   deploy to it, for an extra approval gate before anything publishes.

Until step 1–3 are done, `publish-pypi.yml` will run and fail at the
"Publish to PyPI" step every time a tag is pushed — everything before
that (build, bundle-verification) still runs and still catches a broken
package, it just can't complete the actual upload.

`cli-python/publish.sh` (the older, manual, `PYPI_TOKEN`-based path) is
kept as-is for now — a documented manual fallback (and the only way to
push to TestPyPI, which this automation doesn't cover) rather than
something actively deprecated.
