import re

from textnode import TextNode, TextType


def split_nodes_delimiter(
  old_nodes: list[TextNode], delimiter: str, text_type: TextType
) -> list[TextNode]:
  new_nodes: list[TextNode] = []
  for node in old_nodes:
    if node.text_type != TextType.TEXT:
      new_nodes.append(node)
      continue

    split_nodes: list[TextNode] = []
    sections: list[str] = node.text.split(delimiter)
    if len(sections) % 2 == 0:
      print(old_nodes)
      raise ValueError("invalid md")

    for i in range(len(sections)):
      if sections[i] == "":
        continue
      if i % 2 == 0:
        split_nodes.append(TextNode(sections[i], TextType.TEXT))
      else:
        split_nodes.append(TextNode(sections[i], text_type))
    new_nodes.extend(split_nodes)
  return new_nodes


def extract_markdown_images(text: str) -> list[tuple[str, str]]:
  matches: list[tuple[str, str]] = re.findall(r"!\[([^\[\]]*)\]\(([^\(\)]*)\)", text)
  return matches


def extract_markdown_links(text: str) -> list[tuple[str, str]]:
  matches: list[tuple[str, str]] = re.findall(
    r"(?<!!)\[([^\[\]]*)\]\(([^\(\)]*)\)", text
  )
  return matches


def split_nodes_image(old_nodes: list[TextNode]) -> list[TextNode]:
  new_nodes: list[TextNode] = []
  for node in old_nodes:
    matches: list[tuple[str, str]] = extract_markdown_images(node.text)
    if not matches:
      new_nodes.append(node)
    else:
      original_text: str = node.text
      for match in matches:
        match_str: str = f"![{match[0]}]({match[1]})"
        sections: list[str] = original_text.split(match_str, 1)
        if sections[0]:
          new_nodes.append(TextNode(sections[0], TextType.TEXT))
        new_nodes.append(TextNode(match[0], TextType.IMAGE, match[1]))
        original_text = sections[1]
      if original_text:
        new_nodes.append(TextNode(original_text, TextType.TEXT))
  return new_nodes


def split_nodes_link(old_nodes: list[TextNode]) -> list[TextNode]:
  new_nodes: list[TextNode] = []
  for node in old_nodes:
    matches: list[tuple[str, str]] = extract_markdown_links(node.text)
    if not matches:
      new_nodes.append(node)
    else:
      original_text: str = node.text
      for match in matches:
        match_str: str = f"[{match[0]}]({match[1]})"
        sections: list[str] = original_text.split(match_str, 1)
        if sections[0]:
          new_nodes.append(TextNode(sections[0], TextType.TEXT))
        new_nodes.append(TextNode(match[0], TextType.LINK, match[1]))
        original_text = sections[1]
      if original_text:
        new_nodes.append(TextNode(original_text, TextType.TEXT))
  return new_nodes


def text_to_textnodes(text) -> list[TextNode]:
  node: TextNode = TextNode(text, TextType.TEXT)
  new_nodes: list[TextNode] = [node]
  # we will do repeated function calling
  # bold -> italic -> code -> links -> images
  new_nodes = split_nodes_delimiter(new_nodes, "**", TextType.BOLD)
  new_nodes = split_nodes_delimiter(new_nodes, "`", TextType.CODE)

  new_nodes = split_nodes_link(new_nodes)
  new_nodes = split_nodes_image(new_nodes)
  new_nodes = split_nodes_delimiter(new_nodes, "_", TextType.ITALIC)
  return new_nodes
