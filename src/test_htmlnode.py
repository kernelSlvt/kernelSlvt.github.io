import unittest

from htmlnode import HTMlNode, LeafNode, ParentNode


class TestHTMLNode(unittest.TestCase):
  def test_to_html_props(self) -> None:
    node: HTMlNode = HTMlNode(
      "div", "hello wolrd", None, {"class": "link", "href": "https://google.com"}
    )
    self.assertEqual(node.props_to_html(), ' class="link" href="https://google.com"')

  def test_values(self) -> None:
    node: HTMlNode = HTMlNode(
      "div", "some text lol", None, {"class": "article", "href": "https://git.gay"}
    )
    self.assertEqual(node.tag, "div")
    self.assertEqual(node.value, "some text lol")
    self.assertEqual(node.children, None)
    self.assertEqual(node.props, {"class": "article", "href": "https://git.gay"})

  def test_repr(self) -> None:
    node: HTMlNode = HTMlNode("p", "some text just to add", None, {"class": "primary"})
    self.assertEqual(
      node.__repr__(),
      "HTMLNode(p, some text just to add, children: None, {'class': 'primary'})",
    )


class TestLeafNode(unittest.TestCase):
  def test_leaf_to_html_p(self) -> None:
    node: LeafNode = LeafNode("p", "hello world")
    self.assertEqual(node.to_html(), "<p>hello world</p>")

  def test_leaf_to_html_a(self) -> None:
    node: LeafNode = LeafNode("a", "click me", {"href": "https://google.com"})
    self.assertEqual(node.to_html(), '<a href="https://google.com">click me</a>')

  def test_leaf_to_html_notag(self) -> None:
    node: LeafNode = LeafNode(None, "hello world")
    self.assertEqual(node.to_html(), "hello world")


class TestParentNode(unittest.TestCase):
  def test_to_html_with_children(self):
    child_node = LeafNode("span", "child")
    parent_node = ParentNode("div", [child_node])
    self.assertEqual(parent_node.to_html(), "<div><span>child</span></div>")

  def test_to_html_with_grandchildren(self):
    grandchild_node = LeafNode("b", "grandchild")
    child_node = ParentNode("span", [grandchild_node])
    parent_node = ParentNode("div", [child_node])
    self.assertEqual(
      parent_node.to_html(),
      "<div><span><b>grandchild</b></span></div>",
    )

  def test_to_html_many_children(self) -> None:
    node: ParentNode = ParentNode(
      "p",
      [
        LeafNode("b", "Bold text"),
        LeafNode(None, "Normal text"),
        LeafNode("i", "italic text"),
        LeafNode(None, "Normal text"),
      ],
    )
    self.assertEqual(
      node.to_html(), "<p><b>Bold text</b>Normal text<i>italic text</i>Normal text</p>"
    )


if __name__ == "__main__":
  unittest.main()
