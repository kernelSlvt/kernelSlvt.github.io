import unittest

from utils import extract_title


class TestMain(unittest.TestCase):
  def test_extract_title_with_extra_text(self) -> None:
    md = """
# this is a heading
## this is a heading too

this is a another line
"""
    self.assertEqual(extract_title(md), "this is a heading")

  def test_extract_title_with_extra_spaces(self) -> None:
    md = "#    title with extra spaces   "
    self.assertEqual(extract_title(md), "title with extra spaces")

  def test_extract_title_ignores_h2_before_h1(self) -> None:
    md = """
## not this one
# this is the title
"""
    self.assertEqual(extract_title(md), "this is the title")

  def test_extract_title_with_special_characters(self) -> None:
    md = "# Title with *markdown* and `code`"
    self.assertEqual(extract_title(md), "Title with *markdown* and `code`")

  def test_extract_title_first_line(self) -> None:
    md = "# First Line Title\n## Subheading"
    self.assertEqual(extract_title(md), "First Line Title")

  def test_extract_title_raises_exception(self) -> None:
    md = """
## only h2 here
### and h3
  """
    with self.assertRaises(Exception) as context:
      extract_title(md)
    self.assertIn("No h1 header found", str(context.exception))
