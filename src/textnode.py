from enum import Enum

from htmlnode import LeafNode


class TextType(Enum):
  TEXT = "text"
  BOLD = "bold"
  ITALIC = "italic"
  CODE = "code"
  LINK = "link"
  IMAGE = "image"


class TextNode:
  def __init__(self, text: str, text_type: TextType, url: str | None = None) -> None:
    self.text: str = text
    self.text_type: TextType = text_type
    self.url: str | None = url

  def __eq__(self, other) -> bool:
    return (
      self.text == other.text
      and self.text_type == other.text_type
      and self.url == other.url
    )

  def __repr__(self) -> str:
    return f"TextNode({self.text}, {self.text_type.value}, {self.url})"


def text_node_to_html_node(text_node: TextNode) -> LeafNode:
  if text_node.text_type not in TextType:
    raise ValueError(f"invalid text type: {text_node.text_type}")

  match text_node.text_type:
    case TextType.TEXT:
      return LeafNode(None, text_node.text)
    case TextType.BOLD:
      return LeafNode("b", text_node.text)
    case TextType.ITALIC:
      return LeafNode("i", text_node.text)
    case TextType.CODE:
      return LeafNode("code", text_node.text)
    case TextType.LINK:
      return LeafNode("a", text_node.text, {"href": text_node.url})  # pyright: ignore[reportArgumentType]
    case TextType.IMAGE:
      return LeafNode("img", "", {"src": text_node.url, "alt": text_node.text})  # pyright: ignore[reportArgumentType]
