# sλrthak

the source behind [sarrthak.com](https://sarrthak.com): personal site, writings, and a small static-site generator built from scratch.

## map

- `content/` — pages and writings
- `templates/` — jinja layouts and partials
- `static/` — css, images, and public files
- `src/sitegen/` — the generator itself
- `.github/workflows/` — checks and deployment

## run it

requires python 3.11+.

```sh
python3 -m pip install -e .
sitegen dev --open
```

`dev` includes drafts, rebuilds on source changes, hot-swaps css, reloads changed pages, and keeps the last valid build visible when something breaks. use `--no-drafts` when needed.

## useful bits

```sh
sitegen build       # build into docs/
sitegen check       # validate the generated site
sitegen serve       # serve once without dev tooling
./test.sh           # run the test suite
```

`python3 src/main.py` still works as the old build-only entrypoint.

## how it ships

every push is checked on python 3.11 and 3.13. `main` is built, deployed to github pages, and smoke-tested against production.

`docs/` is generated output and stays out of git. dependabot checks python and action dependencies weekly.
