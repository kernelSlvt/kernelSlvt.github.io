import unittest

from inline_md import (
  extract_markdown_images,
  extract_markdown_links,
  split_nodes_delimiter,
  split_nodes_image,
  split_nodes_link,
  text_to_textnodes,
)
from textnode import TextNode, TextType


class TestInlineMD(unittest.TestCase):
  def test_delim_bold(self) -> None:
    node = TextNode("text with **bold** word", TextType.TEXT)
    new_nodes = split_nodes_delimiter([node], "**", TextType.BOLD)
    self.assertListEqual(
      [
        TextNode("text with ", TextType.TEXT),
        TextNode("bold", TextType.BOLD),
        TextNode(" word", TextType.TEXT),
      ],
      new_nodes,
    )

  def test_delim_bold_double(self) -> None:
    node = TextNode("text with **bold** word and **another** bold word", TextType.TEXT)
    new_nodes = split_nodes_delimiter([node], "**", TextType.BOLD)
    self.assertListEqual(
      [
        TextNode("text with ", TextType.TEXT),
        TextNode("bold", TextType.BOLD),
        TextNode(" word and ", TextType.TEXT),
        TextNode("another", TextType.BOLD),
        TextNode(" bold word", TextType.TEXT),
      ],
      new_nodes,
    )

  def test_delim_bold_and_italic(self) -> None:
    node = TextNode("text with **bold** word and __italic__ word", TextType.TEXT)
    new_nodes = split_nodes_delimiter([node], "**", TextType.BOLD)
    new_nodes = split_nodes_delimiter(new_nodes, "__", TextType.ITALIC)
    self.assertListEqual(
      [
        TextNode("text with ", TextType.TEXT),
        TextNode("bold", TextType.BOLD),
        TextNode(" word and ", TextType.TEXT),
        TextNode("italic", TextType.ITALIC),
        TextNode(" word", TextType.TEXT),
      ],
      new_nodes,
    )

  def test_extract_md_images(self) -> None:
    text = "This is text with a ![rick roll](https://i.imgur.com/aKaOqIh.gif) and ![obi wan kenobi](https://i.imgur.com/fJRm4Vk.jpeg)"
    self.assertListEqual(
      [
        ("rick roll", "https://i.imgur.com/aKaOqIh.gif"),
        ("obi wan kenobi", "https://i.imgur.com/fJRm4Vk.jpeg"),
      ],
      extract_markdown_images(text),
    )

  def test_extract_markdown_links(self) -> None:
    text = "this is text with link to [google](https://google.com) and [this to git.gay](https://git.gay)"
    self.assertListEqual(
      [
        ("google", "https://google.com"),
        ("this to git.gay", "https://git.gay"),
      ],
      extract_markdown_links(text),
    )

  def test_extract_markdown_links_imgText(self) -> None:
    text = "This is text with a ![rick roll](https://i.imgur.com/aKaOqIh.gif) and ![obi wan kenobi](https://i.imgur.com/fJRm4Vk.jpeg)"
    self.assertListEqual([], extract_markdown_links(text))

  def test_split_images(self) -> None:
    node = TextNode(
      "This is text with an ![image](https://i.imgur.com/zjjcJKZ.png) and another ![second image](https://i.imgur.com/3elNhQu.png)",
      TextType.TEXT,
    )
    new_nodes = split_nodes_image([node])
    self.assertListEqual(
      [
        TextNode("This is text with an ", TextType.TEXT),
        TextNode("image", TextType.IMAGE, "https://i.imgur.com/zjjcJKZ.png"),
        TextNode(" and another ", TextType.TEXT),
        TextNode("second image", TextType.IMAGE, "https://i.imgur.com/3elNhQu.png"),
      ],
      new_nodes,
    )

  def test_split_single_image(self) -> None:
    node = TextNode("![image](https://some_link.com)", TextType.TEXT)
    new_nodes = split_nodes_image([node])
    self.assertListEqual(
      [TextNode("image", TextType.IMAGE, "https://some_link.com")], new_nodes
    )

  def test_split_links(self) -> None:
    node = TextNode(
      "This is a text with a [link to google](https://google.com) and [another link](https://git.gay) some more text",
      TextType.TEXT,
    )
    new_nodes = split_nodes_link([node])
    self.assertListEqual(
      [
        TextNode("This is a text with a ", TextType.TEXT),
        TextNode("link to google", TextType.LINK, "https://google.com"),
        TextNode(" and ", TextType.TEXT),
        TextNode("another link", TextType.LINK, "https://git.gay"),
        TextNode(" some more text", TextType.TEXT),
      ],
      new_nodes,
    )

  def test_text_to_textnodes(self) -> None:
    text = "This is **text** with an _italic_ word and a `code block` and an ![obi wan image](https://i.imgur.com/fJRm4Vk.jpeg) and a [link](https://google.com)"
    new_nodes: list[TextNode] = text_to_textnodes(text)
    self.assertListEqual(
      [
        TextNode("This is ", TextType.TEXT),
        TextNode("text", TextType.BOLD),
        TextNode(" with an ", TextType.TEXT),
        TextNode("italic", TextType.ITALIC),
        TextNode(" word and a ", TextType.TEXT),
        TextNode("code block", TextType.CODE),
        TextNode(" and an ", TextType.TEXT),
        TextNode("obi wan image", TextType.IMAGE, "https://i.imgur.com/fJRm4Vk.jpeg"),
        TextNode(" and a ", TextType.TEXT),
        TextNode("link", TextType.LINK, "https://google.com"),
      ],
      new_nodes,
    )


if __name__ == "__main__":
  unittest.main()
