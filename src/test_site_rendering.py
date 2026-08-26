import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from sitegen.build import BuildOptions, SiteBuilder


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestSiteRendering(unittest.TestCase):
  def setUp(self) -> None:
    self.temp_dir = tempfile.TemporaryDirectory()
    self.project_root = Path(self.temp_dir.name)
    for directory in ("content", "templates", "static"):
      shutil.copytree(PROJECT_ROOT / directory, self.project_root / directory)

    config = json.loads(PROJECT_ROOT.joinpath("config.json").read_text())
    self.project_root.joinpath("config.json").write_text(json.dumps(config))
    self.output_dir = SiteBuilder(self.project_root).build(
      BuildOptions(incremental=False)
    ).output_dir

  def tearDown(self) -> None:
    self.temp_dir.cleanup()

  def test_real_site_renders_shared_metadata_and_complete_archive(self) -> None:
    home = self.output_dir.joinpath("index.html").read_text()
    archive = self.output_dir.joinpath("blogs/index.html").read_text()
    article = self.output_dir.joinpath("blogs/learn_ocaml/index.html").read_text()

    for page in (home, archive, article):
      self.assertIn('type="application/rss+xml"', page)
      self.assertIn('property="og:title"', page)
      self.assertIn('name="twitter:card" content="summary_large_image"', page)
      self.assertIn('href="mailto:hey@sarrthak.com">email</a>', page)
      self.assertIn('href="/feed.xml">rss</a>', page)

    self.assertIn('rel="canonical" href="https://sarrthak.com/"', home)
    self.assertIn('property="og:type" content="website"', home)
    self.assertIn('property="og:type" content="article"', article)
    self.assertIn('class="home-writing-all" href="/blogs/">all writings</a>', home)

    for slug in ("make_cool_stuff", "learn_ocaml", "randomness_impl"):
      self.assertIn(f'href="/blogs/{slug}/"', archive)
    for published in ("30 aug 2025", "30 jul 2025", "19 jul 2025"):
      self.assertIn(published, archive)
    self.assertNotIn("&lt;- home", archive)

  def test_real_articles_preserve_accessibility_and_image_stability(self) -> None:
    ocaml = self.output_dir.joinpath("blogs/learn_ocaml/index.html").read_text()
    randomness = self.output_dir.joinpath(
      "blogs/randomness_impl/index.html"
    ).read_text()

    self.assertIn(
      'more<span class="visually-hidden"> at cs3110.github.io</span>',
      ocaml,
    )
    self.assertRegex(
      randomness,
      r'<img src="/images/reddit-meme\.jpg" alt="random number" loading="lazy" decoding="async" width="\d+" height="\d+"',
    )

  def test_feed_and_sitemap_use_the_shared_content_index(self) -> None:
    channel = ET.parse(self.output_dir / "feed.xml").getroot().find("channel")
    self.assertIsNotNone(channel)
    items = channel.findall("item")
    self.assertEqual(
      [item.findtext("title") for item in items],
      [
        "make cool stuff",
        "why you should learn ocaml",
        "on randomness and its implementation",
      ],
    )

    locations = [
      element.text
      for element in ET.parse(self.output_dir / "sitemap.xml").getroot().iter()
      if element.tag.endswith("loc")
    ]
    self.assertEqual(
      locations,
      [
        "https://sarrthak.com/",
        "https://sarrthak.com/blogs/",
        "https://sarrthak.com/blogs/learn_ocaml/",
        "https://sarrthak.com/blogs/make_cool_stuff/",
        "https://sarrthak.com/blogs/randomness_impl/",
      ],
    )

  def test_repository_specific_static_files_and_article_measure_are_preserved(self) -> None:
    robots = self.output_dir.joinpath("robots.txt").read_text()
    llms = self.output_dir.joinpath("llms.txt").read_text()
    css = self.output_dir.joinpath("index.css").read_text()

    self.assertEqual(
      robots,
      "User-agent: *\nAllow: /\nSitemap: https://sarrthak.com/sitemap.xml\n",
    )
    self.assertEqual(self.output_dir.joinpath("CNAME").read_text(), "sarrthak.com\n")
    self.assertIn("# sλrthak", llms)
    self.assertIn("[all writings](/blogs/)", llms)
    self.assertRegex(css, r"\.blog-article p \{\s+max-width: 68ch;")


if __name__ == "__main__":
  unittest.main()
