# Static Site Generator v2 Implementation Plan

> **For agentic workers:** Execute inline with TDD. Subagents are not used for this repository task.

**Goal:** Replace the brittle generator with a typed, CommonMark-compatible, atomic and incremental static-site engine.

**Architecture:** Build one validated `BuildContext` and `ContentIndex`, render with markdown-it-py and strict Jinja2 templates, validate staged output, then atomically publish it. CLI commands expose build, check, serve, draft, watch, and incremental behavior.

**Tech Stack:** Python 3.13, markdown-it-py 4.x, Jinja2 3.1.x, PyYAML 6.x, unittest.

**Spec:** `plans/2026-08-25-static-site-generator-v2-spec.md`

## Global Constraints

- Preserve existing public URLs and page copy.
- Keep Instrument Serif and mono typography unchanged.
- Do not alter article prose.
- Build failures must preserve the previous `docs/` directory.
- All new behavior starts with a failing test.

---

### Task 1: Models, Configuration, and Front Matter

**Files:** Create `src/sitegen/models.py`, `src/sitegen/config.py`, `src/sitegen/frontmatter.py`, `src/tests/test_frontmatter.py`; modify `pyproject.toml`.

**Interfaces:** Produce `SiteConfig.load(path)`, `PageMetadata`, `Page`, and `parse_document(path) -> ParsedDocument`.

- [ ] Add tests proving legacy and YAML front matter parse into typed dates, booleans, tags, slugs, permalinks, and per-page images.
- [ ] Add tests proving invalid dates, missing titles, malformed YAML, and invalid permalinks raise path-aware `ContentError` messages.
- [ ] Add project dependencies and implement the minimal typed models and parsers.
- [ ] Run `python3 -m unittest discover -s src/tests -p 'test_frontmatter.py'` until green.

### Task 2: CommonMark Rendering

**Files:** Create `src/sitegen/markdown.py`, `src/tests/test_markdown.py`.

**Interfaces:** Produce `MarkdownRenderer.render(markdown) -> RenderedMarkdown` containing HTML, description, reading time, heading IDs, and asset flags.

- [ ] Add failing tests for final blocks without newlines, malformed fences, nested emphasis, parentheses in URLs, inline-code math, escaped attributes, valid void images, duplicate heading IDs, tables, and fenced-code language classes.
- [ ] Configure markdown-it-py with HTML disabled, linkify disabled, typographer disabled, table support, deterministic heading anchors, and safe link validation.
- [ ] Preserve MathJax delimiters outside code and compute descriptions and reading times from tokens rather than regexing raw Markdown.
- [ ] Run the focused Markdown tests until green.

### Task 3: Discovery and Content Index

**Files:** Create `src/sitegen/content.py`, `src/tests/test_content.py`.

**Interfaces:** Produce `ContentRepository.discover(include_drafts=False) -> ContentIndex`; `ContentIndex` exposes pages, posts, tags, paginated posts, and a stable digest.

- [ ] Add failing fixture tests for drafts, updated dates, directory slugs, custom slugs, custom permalinks, duplicate routes, missing article files, tag normalization, and pagination.
- [ ] Discover and parse each source once, resolve routes, reject collisions, sort posts by date, and build tag/pagination views.
- [ ] Verify one discovery pass handles all consumers without repeated filesystem scans.

### Task 4: Strict Template Rendering

**Files:** Create `src/sitegen/templates.py`, `src/sitegen/render.py`, `templates/base.html`, `templates/partials/header.html`, `templates/partials/footer.html`, `templates/tags.html`; rewrite `templates/home.html`, `templates/writings.html`, `templates/blog.html`; create `src/tests/test_templates_v2.py`.

**Interfaces:** Produce `TemplateRenderer.render_page(page, context) -> str` and render archive/tag pagination pages.

- [ ] Add failing tests proving missing variables fail, text is escaped, rendered Markdown remains trusted HTML, metadata is page-specific, and navigation URLs remain unchanged.
- [ ] Configure Jinja2 `StrictUndefined`, autoescape, reusable partials, and explicit page contexts.
- [ ] Render recent posts, full archives, pagination controls, tag archives, canonical/Open Graph/Twitter metadata, MathJax, and highlight assets.

### Task 5: Atomic Incremental Build and Validation

**Files:** Create `src/sitegen/build.py`, `src/sitegen/manifest.py`, `src/sitegen/validate.py`, `src/sitegen/feeds.py`, `src/tests/test_build.py`, `src/tests/test_validate.py`.

**Interfaces:** Produce `SiteBuilder.build(options) -> BuildReport` and `SiteValidator.validate(root) -> list[ValidationIssue]`.

- [ ] Add failing tests proving build errors preserve existing output, successful builds replace it, unchanged pages are reused, changed templates invalidate affected pages, and removed sources remove stale outputs.
- [ ] Add failing tests for broken internal links, missing images, unresolved template markers, absent canonical metadata, invalid feed XML, and invalid sitemap XML.
- [ ] Generate pages, RSS, sitemap, robots, CNAME, pagination, and tag archives into staging; validate; atomically swap; persist a hash manifest.

### Task 6: CLI, Serve, Watch, and Check

**Files:** Create `src/sitegen/cli.py`, `src/sitegen/server.py`, `src/sitegen/__init__.py`, `src/sitegen/__main__.py`, `src/tests/test_cli.py`; rewrite `src/main.py`, `main.sh`, `test.sh`.

**Interfaces:** Produce `sitegen build`, `sitegen check`, and `sitegen serve` commands with `--drafts`, `--no-incremental`, `--watch`, `--host`, and `--port` options.

- [ ] Add failing parser and command tests for every option and non-zero exit on validation/build errors.
- [ ] Implement a polling watcher that snapshots source/config/template/static mtimes, debounces changes, rebuilds, and keeps serving the last valid output after failures.
- [ ] Keep `python3 src/main.py` as a compatibility build command.

### Task 7: Migration and End-to-End Verification

**Files:** Modify `README.md`, `AGENTS.md` only if repository commands changed; remove or convert legacy parser modules and tests once no production imports remain.

- [ ] Run all unit tests, compile checks, and `git diff --check`.
- [ ] Build twice and verify the second build reports reused outputs.
- [ ] Run `sitegen check` against the generated site.
- [ ] Verify `/`, `/blogs/`, pagination/tag routes when present, all articles, `/feed.xml`, `/sitemap.xml`, and `/robots.txt` through Chrome DevTools AXI at desktop and 320px.
- [ ] Inspect the final diff and remove legacy dead code or accidental generated changes outside the migration boundary.
