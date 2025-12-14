import unittest

from textnode import TextNode, TextType, text_node_to_html_node


class TestTextNode(unittest.TestCase):
  def test_eq1(self) -> None:
    node: TextNode = TextNode("This is a text node", TextType.BOLD)
    node2: TextNode = TextNode("This is a text node", TextType.BOLD)
    self.assertEqual(node, node2)

  def test_eq2(self) -> None:
    node1: TextNode = TextNode(
      "testing for same text", TextType.LINK, "https://google.com"
    )
    node2: TextNode = TextNode(
      "testing for same text", TextType.LINK, "https://google.com"
    )
    self.assertEqual(node1, node2)

  def test_not_eq1(self) -> None:
    node1: TextNode = TextNode("this is some text", TextType.LINK, "https://google.com")
    node2: TextNode = TextNode(
      "this is some diff text", TextType.LINK, "https://google.com"
    )
    self.assertNotEqual(node1, node2)

  def test_not_eq2(self) -> None:
    node1: TextNode = TextNode("this is some text", TextType.BOLD, None)
    node2: TextNode = TextNode("this is some text", TextType.ITALIC)
    self.assertNotEqual(node1, node2)

  def test_repr(self) -> None:
    node: TextNode = TextNode("This is a text node", TextType.TEXT)
    self.assertEqual("TextNode(This is a text node, text, None)", repr(node))


class TestTextToHtmlNode(unittest.TestCase):
  def test_text(self) -> None:
    node: TextNode = TextNode("this is a text node", TextType.TEXT)
    html_node = text_node_to_html_node(node)
    self.assertEqual(html_node.tag, None)
    self.assertEqual(html_node.value, "this is a text node")

  def test_bold(self) -> None:
    node: TextNode = TextNode("this is a bold node", TextType.BOLD)
    html_node = text_node_to_html_node(node)
    self.assertEqual(html_node.tag, "b")
    self.assertEqual(html_node.value, "this is a bold node")

  def test_image(self) -> None:
    node: TextNode = TextNode(
      "this is a image node", TextType.IMAGE, "https://some-image.com"
    )
    html_node = text_node_to_html_node(node)
    self.assertEqual(html_node.tag, "img")
    self.assertEqual(html_node.value, "")
    self.assertEqual(
      html_node.props, {"src": "https://some-image.com", "alt": "this is a image node"}
    )

  def test_link(self) -> None:
    node: TextNode = TextNode(
      "this is a link node", TextType.LINK, "https://google.com"
    )
    html_node = text_node_to_html_node(node)
    self.assertEqual(html_node.tag, "a")
    self.assertEqual(html_node.value, "this is a link node")
    self.assertEqual(html_node.props, {"href": "https://google.com"})


if __name__ == "__main__":
  unittest.main()
