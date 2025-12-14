from htmlnode import HTMlNode, LeafNode, ParentNode
from textnode import TextNode, TextType


def main() -> None:
  newTextNode: TextNode = TextNode(
    "This is some text", TextType.LINK, "https://www.google.com"
  )
  print(newTextNode)

  someHtmlNode: HTMlNode = HTMlNode(
    "a", "click here", None, {"href": "https://google.com", "target": "_blank"}
  )
  print(someHtmlNode)
  print(someHtmlNode.props_to_html())

  newHtmlNode: HTMlNode = HTMlNode("p", "this is a paragraph", [someHtmlNode], None)
  print(newHtmlNode)

  newLeafNode: LeafNode = LeafNode("a", "click me", {"href": "https://google.com"})
  print(newLeafNode.to_html())

  node: ParentNode = ParentNode(
    "p",
    [
      LeafNode("b", "Bold text"),
      LeafNode(None, "Normal text"),
      LeafNode("i", "italic text"),
      LeafNode(None, "Normal text"),
    ],
  )

  print(node.to_html())


if __name__ == "__main__":
  main()
