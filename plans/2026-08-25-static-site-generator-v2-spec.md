# Static Site Generator v2 Design

## Goal

Replace the current hand-written parsing and rendering pipeline with a reliable, typed, extensible generator while preserving the site's URLs, content, visual output, RSS feed, sitemap, robots file, and custom domain.

## Architecture

The generator becomes a `sitegen` Python package. A build loads and validates `config.json` once, discovers every Markdown source into typed `Page` objects, creates one immutable `ContentIndex`, renders Markdown with `markdown-it-py`, and renders HTML through Jinja2 with `StrictUndefined` and autoescaping. Feeds, pagination, tag archives, and sitemaps consume the same index rather than rescanning files.

Builds write into a sibling staging directory. The staging output is checked for unresolved templates, missing internal links, missing local images, and required metadata before it replaces `docs/`. Failed builds leave the previous output untouched. A manifest records input hashes so unchanged pages can be copied from the previous output during incremental builds.

## Content Model

Each page supports `title`, `date`, `updated`, `draft`, `slug`, `permalink`, `description`, `social_image`, `tags`, and `template`. Existing `-----` metadata remains supported; standard `---` YAML front matter is also accepted. Blog directory names remain the default slug. Drafts are excluded unless `--drafts` is passed.

## Commands

- `python3 -m sitegen build [--drafts] [--no-incremental]`
- `python3 -m sitegen check [--drafts]`
- `python3 -m sitegen serve [--drafts] [--watch] [--port 8888]`

`serve --watch` uses a polling watcher with debouncing and rebuilds after source, template, static, or config changes.

## Compatibility

The public site remains at `/`, `/blogs/`, and `/blogs/<slug>/`. Pagination uses `/blogs/page/<n>/`; tag archives use `/tags/<slug>/`. Existing Markdown content requires no migration. `src/main.py` remains as a thin compatibility entry point.

## Verification

Tests cover front matter validation, CommonMark edge cases, HTML escaping, content discovery, draft filtering, routing, pagination, tags, strict templates, incremental reuse, atomic failure behavior, internal link checking, feeds, sitemap output, and CLI parsing. The final built site is checked through Chrome DevTools AXI at desktop and mobile widths.
