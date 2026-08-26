# sarrthak.com

Personal site and static-site generator for [sarrthak.com](https://sarrthak.com).

## Setup

Requires Python 3.11 or newer.

```sh
python3 -m pip install -e .
```

## Commands

```sh
sitegen build                         # build the site into docs/
sitegen check                         # build, then validate links and metadata
sitegen serve --watch --port 8888     # rebuild on changes and serve locally
./test.sh                             # run the complete unittest suite
```

`python3 src/main.py` remains available as a build-only compatibility entrypoint.

## Deployment

GitHub Actions owns production deployment:

- `.github/workflows/ci.yml` verifies the generator on Python 3.11 and 3.13 for every pull request and push.
- `.github/workflows/deploy.yml` rebuilds and validates the site on `main`, uploads `docs/` as a Pages artifact, deploys it, and smoke-tests every public route.
- `.github/dependabot.yml` checks Python and workflow dependencies weekly.

`docs/` is generated local output and is intentionally ignored by Git. Do not commit it. GitHub Pages must use **GitHub Actions** as its source rather than the legacy `main:/docs` branch setting.

For a no-downtime migration, split the rollout: first push the workflow files while the existing tracked `docs/` remains available, then switch the Pages source to **GitHub Actions**, and only then commit the `docs/` removal. Do not push the staged `docs/` deletions before that source switch.
