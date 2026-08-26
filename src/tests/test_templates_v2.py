import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from jinja2 import FileSystemLoader, StrictUndefined, UndefinedError

from sitegen.render import TemplateRenderer
from sitegen.templates import create_environment


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = PROJECT_ROOT / "templates"


def namespace(**values: object) -> SimpleNamespace:
  return SimpleNamespace(**values)


def rendered(
  html: str = "",
  *,
  reading_time: str = "1 min read",
  has_math: bool = False,
  has_code: bool = False,
) -> SimpleNamespace:
  return namespace(
    html=html,
    reading_time=reading_time,
    has_math=has_math,
    has_code=has_code,
  )


def page(
  *,
  title: str,
  route: str,
  template: str,
  published: date = date(2026, 8, 24),
  updated: date | None = None,
  description: str = "systems notes",
  social_image_url: str = "https://sarrthak.com/images/social.png",
  tags: tuple[str, ...] = (),
  body: SimpleNamespace | None = None,
) -> SimpleNamespace:
  return namespace(
    title=title,
    date=published,
    updated=updated,
    route=route,
    canonical_url=f"https://sarrthak.com{route}",
    description=description,
    social_image_url=social_image_url,
    tags=tags,
    rendered=body or rendered(),
    template=template,
  )


def config() -> SimpleNamespace:
  return namespace(
    site_url="https://sarrthak.com",
    email="hey@sarrthak.com",
    social_image="/images/social.png",
  )


def pagination_context(
  items: tuple[SimpleNamespace, ...],
  *,
  page_number: int = 2,
  total_pages: int = 3,
  previous_url: str | None = "/blogs/",
  next_url: str | None = "/blogs/page/3/",
  **extra: object,
) -> SimpleNamespace:
  return namespace(
    config=config(),
    items=items,
    page=page_number,
    total_pages=total_pages,
    previous_url=previous_url,
    next_url=next_url,
    **extra,
  )


class TemplateRenderingTestCase(unittest.TestCase):
  def setUp(self) -> None:
    self.environment = create_environment(TEMPLATE_ROOT)
    self.renderer = TemplateRenderer(self.environment)

  def render(self, target: SimpleNamespace, context: SimpleNamespace) -> str:
    return self.renderer.render_page(target, context)


class TestTemplateEnvironment(unittest.TestCase):
  def test_environment_loads_files_strictly_and_autoescapes_html(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      template_dir = Path(temp_dir)
      template_dir.joinpath("escaped.html").write_text(
        "{{ value }}", encoding="utf-8"
      )
      template_dir.joinpath("plain.txt").write_text("{{ value }}", encoding="utf-8")

      environment = create_environment(template_dir)

      self.assertIsInstance(environment.loader, FileSystemLoader)
      self.assertIs(environment.undefined, StrictUndefined)
      self.assertEqual(
        environment.get_template("escaped.html").render(value="<unsafe>"),
        "&lt;unsafe&gt;",
      )
      self.assertEqual(
        environment.get_template("plain.txt").render(value="<unsafe>"),
        "<unsafe>",
      )
      with self.assertRaises(UndefinedError):
        environment.get_template("escaped.html").render()

  def test_renderer_supports_build_facing_construction_and_archives(self) -> None:
    from sitegen.templates import TemplateRenderer as BuildTemplateRenderer

    site_config = namespace(
      template_dir=TEMPLATE_ROOT,
      site_url="https://sarrthak.com",
      email="hey@sarrthak.com",
      social_image="/images/social.png",
    )
    renderer = BuildTemplateRenderer(site_config)
    post = page(
      title="systems post",
      route="/blogs/systems/",
      template="blog.html",
      tags=("systems",),
    )
    index = namespace(posts=(post,), recent_posts=(post,))
    home = page(title="home", route="/", template="home.html")
    archive = page(title="all writings", route="/blogs/", template="writings.html")
    pagination = namespace(
      items=(post,),
      page=1,
      total_pages=1,
      route="/blogs/",
      previous_url=None,
      next_url=None,
    )
    tag = namespace(
      name="systems",
      slug="systems",
      route="/tags/systems/",
      items=(post,),
    )

    self.assertIn("systems post", renderer.render_page(home, index))
    self.assertIn("systems post", renderer.render_archive(archive, pagination, index))
    self.assertIn("systems post", renderer.render_tag(tag, index))
    self.assertTrue(renderer.template_digest("home.html"))


class TestSharedLayout(TemplateRenderingTestCase):
  def test_rendered_pages_do_not_contain_trailing_whitespace(self) -> None:
    home = page(
      title="home",
      route="/",
      template="home.html",
      body=rendered("<p>hello.</p>"),
    )
    context = namespace(
      config=config(),
      index=namespace(posts=(), recent_posts=()),
    )

    html = self.render(home, context)

    self.assertTrue(all(line == line.rstrip() for line in html.splitlines()))

  def test_shared_layout_preserves_metadata_navigation_and_footer(self) -> None:
    home = page(
      title="sλrthak — systems, models, machines",
      route="/",
      template="home.html",
      description="systems, models, and machines",
      body=rendered("<p>hello.</p>"),
    )
    context = namespace(
      config=config(),
      index=namespace(posts=(), recent_posts=()),
    )

    html = self.render(home, context)

    self.assertIn("<title>sλrthak — systems, models, machines</title>", html)
    self.assertIn('<link rel="canonical" href="https://sarrthak.com/"', html)
    self.assertIn('<meta property="og:type" content="website"', html)
    self.assertIn('<meta property="og:site_name" content="sλrthak"', html)
    self.assertIn(
      '<meta property="og:url" content="https://sarrthak.com/"', html
    )
    self.assertIn(
      '<meta property="og:image" content="https://sarrthak.com/images/social.png"',
      html,
    )
    self.assertIn('<meta name="twitter:card" content="summary_large_image"', html)
    self.assertIn('<link rel="describedby" href="/llms.txt"', html)
    self.assertIn('type="application/rss+xml"', html)
    self.assertIn('href="/feed.xml"', html)
    self.assertIn('<body class="home-page">', html)
    self.assertIn('<a class="skip-link" href="#main-content">skip to content</a>', html)
    self.assertIn('<a class="site-title" href="/">sλrthak</a>', html)
    self.assertIn('<span class="site-name">sarthak tomar</span>', html)
    self.assertIn('href="https://github.com/saarthak314">github</a>', html)
    self.assertIn('href="https://x.com/sarthak2143">twitter/x</a>', html)
    self.assertIn(
      'href="https://linkedin.com/in/sarthaktomar2143">linkedin</a>', html
    )
    self.assertIn(
      'href="https://discord.com/users/1226399791362080820">discord</a>', html
    )
    self.assertRegex(html, r"© \d{4} sarthak tomar\. built with love\.")
    self.assertIn('href="mailto:hey@sarrthak.com">email</a>', html)
    self.assertIn('href="/feed.xml">rss</a>', html)

  def test_ordinary_strings_escape_while_markdown_html_remains_safe(self) -> None:
    article = page(
      title="templates <script>alert(1)</script>",
      route="/blogs/templates/",
      template="blog.html",
      description='notes about <templates> & "escaping"',
      tags=("systems",),
      body=rendered("<p><em>trusted markdown</em></p>"),
    )

    html = self.render(article, namespace(config=config()))

    self.assertIn("templates &lt;script&gt;alert(1)&lt;/script&gt;", html)
    self.assertNotIn("templates <script>alert(1)</script>", html)
    self.assertIn(
      "notes about &lt;templates&gt; &amp; &#34;escaping&#34;",
      html,
    )
    self.assertIn("<p><em>trusted markdown</em></p>", html)
    self.assertNotIn("&lt;p&gt;&lt;em&gt;trusted markdown", html)

  def test_math_and_code_assets_follow_rendered_markdown_flags(self) -> None:
    plain_article = page(
      title="plain article",
      route="/blogs/plain/",
      template="blog.html",
      body=rendered("<p>plain.</p>"),
    )
    rich_article = page(
      title="rich article",
      route="/blogs/rich/",
      template="blog.html",
      body=rendered(
        "<p>rich.</p>",
        has_math=True,
        has_code=True,
      ),
    )

    plain_html = self.render(plain_article, namespace(config=config()))
    rich_html = self.render(rich_article, namespace(config=config()))

    self.assertNotIn("mathjax@3/es5/tex-chtml.js", plain_html)
    self.assertNotIn("highlight.min.js", plain_html)
    self.assertNotIn("/gruvbox-dark-hard.css", plain_html)
    self.assertIn("mathjax@3/es5/tex-chtml.js", rich_html)
    self.assertIn("highlight.min.js", rich_html)
    self.assertIn("/gruvbox-dark-hard.css", rich_html)


class TestHomeTemplate(TemplateRenderingTestCase):
  def test_home_renders_intro_recent_posts_and_archive_link(self) -> None:
    recent = page(
      title="recent post",
      route="/blogs/recent/",
      template="blog.html",
      published=date(2026, 8, 24),
    )
    older = page(
      title="older post",
      route="/blogs/older/",
      template="blog.html",
      published=date(2025, 7, 19),
    )
    home = page(
      title="sλrthak — systems, models, machines",
      route="/",
      template="home.html",
      body=rendered("<p>trusted <strong>intro</strong>.</p>"),
    )
    context = namespace(
      config=config(),
      index=namespace(posts=(recent, older), recent_posts=(recent,)),
    )

    html = self.render(home, context)

    self.assertIn(
      '<article class="home-intro"><p>trusted <strong>intro</strong>.</p></article>',
      html,
    )
    self.assertIn('<ul class="writing-list">', html)
    self.assertIn('<span class="writing-row__date">aug 2026</span>', html)
    self.assertIn(
      '<a class="writing-row__title" href="/blogs/recent/">recent post</a>',
      html,
    )
    self.assertNotIn("older post", html)
    self.assertIn(
      '<a class="home-writing-all" href="/blogs/">all writings</a>', html
    )


class TestWritingsTemplate(TemplateRenderingTestCase):
  def test_writings_renders_full_dates_and_pagination(self) -> None:
    first = page(
      title="first post",
      route="/blogs/first/",
      template="blog.html",
      published=date(2026, 8, 24),
    )
    second = page(
      title="second post",
      route="/blogs/second/",
      template="blog.html",
      published=date(2026, 7, 3),
    )
    archive = page(
      title="all writings",
      route="/blogs/page/2/",
      template="writings.html",
    )

    html = self.render(archive, pagination_context((first, second)))

    self.assertIn('<body class="writings-page">', html)
    self.assertIn('<h1 class="writings-heading">all writings</h1>', html)
    self.assertIn("everything i've written, newest first.", html)
    self.assertIn('<span class="writing-row__date">24 aug 2026</span>', html)
    self.assertIn('href="/blogs/first/">first post</a>', html)
    self.assertIn('<span class="writing-row__date">03 jul 2026</span>', html)
    self.assertIn('href="/blogs/second/">second post</a>', html)
    self.assertIn('<nav class="pagination" aria-label="Pagination">', html)
    self.assertIn('rel="prev" href="/blogs/">previous</a>', html)
    self.assertIn('<span>page 2 of 3</span>', html)
    self.assertIn('rel="next" href="/blogs/page/3/">next</a>', html)


class TestBlogTemplate(TemplateRenderingTestCase):
  def test_blog_renders_article_metadata_content_and_tags(self) -> None:
    article = page(
      title="strict templates",
      route="/blogs/strict-templates/",
      template="blog.html",
      published=date(2026, 8, 24),
      updated=date(2026, 8, 25),
      description="strict rendering without surprises",
      social_image_url="https://sarrthak.com/images/templates.png",
      tags=("systems", "inference"),
      body=rendered(
        '<p id="trusted">rendered <code>markdown</code>.</p>',
        reading_time="4 min read",
      ),
    )

    html = self.render(article, namespace(config=config()))

    self.assertIn('<body class="blog-page">', html)
    self.assertIn("<title>strict templates — sλrthak</title>", html)
    self.assertIn('<meta property="og:type" content="article"', html)
    self.assertIn(
      '<meta property="article:published_time" content="2026-08-24"', html
    )
    self.assertIn(
      '<meta property="article:modified_time" content="2026-08-25"', html
    )
    self.assertIn(
      '<meta name="twitter:description" content="strict rendering without surprises"',
      html,
    )
    self.assertIn(
      '<meta name="twitter:image" content="https://sarrthak.com/images/templates.png"',
      html,
    )
    self.assertIn('<a class="blog-back" href="/blogs/">&lt;- writing</a>', html)
    self.assertIn(
      '<time class="blog-date" datetime="2026-08-24">24 aug 2026</time>', html
    )
    self.assertIn('<span class="blog-reading-time">4 min read</span>', html)
    self.assertIn('<h1 class="blog-heading">strict templates</h1>', html)
    self.assertIn(
      '<article class="blog-article"><p id="trusted">rendered <code>markdown</code>.</p></article>',
      html,
    )
    self.assertIn('<nav class="blog-tags" aria-label="Article tags">', html)
    self.assertIn('href="/tags/systems/">systems</a>', html)
    self.assertIn('href="/tags/inference/">inference</a>', html)
    self.assertIn('href="/blogs/">all writings</a>', html)
    self.assertIn('href="#main-content">top</a>', html)
    self.assertRegex(html, r"© \d{4} sarthak tomar\. built by hand\.")


class TestTagsTemplate(TemplateRenderingTestCase):
  def test_tags_archive_does_not_require_pagination(self) -> None:
    tagged = page(
      title="tagged post",
      route="/blogs/tagged/",
      template="blog.html",
    )
    archive = page(
      title="systems",
      route="/tags/systems/",
      template="tags.html",
      description="writing tagged systems",
    )
    tag = namespace(name="systems", items=(tagged,))

    html = self.render(archive, namespace(config=config(), tag=tag))

    self.assertIn('<h1 class="tags-heading">systems</h1>', html)
    self.assertIn('href="/blogs/tagged/">tagged post</a>', html)
    self.assertNotIn('aria-label="Pagination"', html)

  def test_tags_archive_renders_items_and_pagination(self) -> None:
    tagged = page(
      title="tagged post",
      route="/blogs/tagged/",
      template="blog.html",
      published=date(2026, 8, 24),
    )
    archive = page(
      title="systems",
      route="/tags/systems/page/2/",
      template="tags.html",
      description="writing tagged systems",
    )
    context = pagination_context(
      (tagged,),
      previous_url="/tags/systems/",
      next_url="/tags/systems/page/3/",
      tag="systems",
    )

    html = self.render(archive, context)

    self.assertIn('<body class="tags-page">', html)
    self.assertIn('<h1 class="tags-heading">systems</h1>', html)
    self.assertIn('href="/blogs/tagged/">tagged post</a>', html)
    self.assertIn('<span class="writing-row__date">24 aug 2026</span>', html)
    self.assertIn('rel="prev" href="/tags/systems/">previous</a>', html)
    self.assertIn('<span>page 2 of 3</span>', html)
    self.assertIn(
      'rel="next" href="/tags/systems/page/3/">next</a>', html
    )


if __name__ == "__main__":
  unittest.main()
