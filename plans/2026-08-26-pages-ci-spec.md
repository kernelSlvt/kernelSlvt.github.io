# GitHub Pages CI/CD Design

## Goal

Replace the repository's legacy `main:/docs` GitHub Pages deployment with a verified, artifact-based GitHub Actions pipeline. Pull requests must prove the generator works; `main` deployments must build from source, validate the generated site, publish only the resulting artifact, and smoke-test production.

## Current State

GitHub Pages currently publishes committed files from `main:/docs`. The repository has no Actions workflows, no branch protection, and duplicated generated assets in Git history. The v2 generator already provides atomic builds, validation, and deterministic incremental output.

## Continuous Integration

`.github/workflows/ci.yml` runs on every pull request and push. Separate jobs test the supported floor, Python 3.11, and the current development runtime, Python 3.13. Each job installs the package, runs all unittests, compiles `src/`, performs a fresh non-incremental build, runs `sitegen check`, rejects unresolved Jinja markers, and runs `git diff --check`.

CI uses read-only repository permissions, pip caching, immutable action SHAs, and branch-specific concurrency cancellation so stale runs do not waste capacity.

## Deployment

`.github/workflows/deploy.yml` runs on pushes to `main` and manual dispatch. It repeats the complete verification boundary on Python 3.13, configures Pages, uploads `docs/` as the Pages artifact, and deploys through the `github-pages` environment. Permissions are limited to `contents: read`, `pages: write`, and `id-token: write`; production deployments are serialized.

After deployment, a smoke test retries `https://sarrthak.com` and checks the homepage, three article routes, RSS, sitemap, robots, and `llms.txt`.

## Generated Output

`docs/` remains the local output directory but is ignored by Git and removed from source tracking. CI is the only deployment authority. The custom domain continues to come from `static/CNAME`, so each clean build includes it in the artifact.

## Maintenance

`.github/dependabot.yml` checks Python and GitHub Actions dependencies weekly. Workflow tests enforce pinned action SHAs, required permissions, supported Python versions, deployment triggers, smoke-test routes, and ignored generated output.

## Live Migration Boundary

This implementation does not commit, push, or change the live Pages source. The safe rollout uses two commits: first merge the workflows while the existing tracked `docs/` remains available, then switch GitHub Pages from the legacy branch source to GitHub Actions, and only then commit the `docs/` removal. This prevents the legacy publisher from observing an empty source directory before the first artifact deployment.
