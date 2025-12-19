from enum import Enum

from htmlnode import LeafNode, ParentNode
from inline_md import text_to_textnodes
from textnode import TextNode, TextType, text_node_to_html_node


class BlockType(Enum):
  PARAGRAPH = "paragraph"
  HEADING = "heading"
  CODE = "code"
  QUOTE = "quote"
  UNORDERED_LIST = "unordered-list"
  ORDERED_LIST = "ordered-list"


def block_to_block_type(markdown: str) -> BlockType:
  if markdown.startswith("#"):
    return BlockType.HEADING
  if markdown.startswith("```") and markdown.endswith("```"):
    return BlockType.CODE

  if _checkEachLine(markdown, ">"):
    return BlockType.QUOTE
  if _checkEachLine(markdown, "- "):
    return BlockType.UNORDERED_LIST

  isOL: bool = True
  lines: list[str] = markdown.split("\n")
  for i in range(len(lines)):
    line: str = lines[i]
    if not line.startswith(str(i + 1) + ". "):
      isOL = False
      break
  if isOL:
    return BlockType.ORDERED_LIST

  return BlockType.PARAGRAPH


def _checkEachLine(text: str, sep: str) -> bool:
  lines: list[str] = text.split("\n")
  return all([line.startswith(sep) for line in lines])


def _getHeadingSize(heading: str) -> int:
  size: int = 0
  for char in heading:
    if char != "#":
      break
    else:
      size += 1
  return min(size, 6)


def _text_to_children(text) -> list[LeafNode]:
  text_nodes: list[TextNode] = text_to_textnodes(text)
  return list(map(text_node_to_html_node, text_nodes))


def _convertToListItems(list_text: str) -> list[ParentNode]:
  list_items: list[ParentNode] = []
  li: list[str] = list_text.split("\n")
  text: str = ""
  if li[0][0] == "-":
    for lli in li:
      text = lli[2:]
      list_items.append(ParentNode("li", _text_to_children(text)))
  else:
    for lli in li:
      text = lli[3:]
      list_items.append(ParentNode("li", _text_to_children(text)))
  return list_items


def markdown_to_blocks(markdown: str) -> list[str]:
  text: list[str] = markdown.split("\n\n")
  blocks: list[str] = list(map(lambda x: x.strip(), text))
  return blocks


def markdown_to_html_node(markdown: str) -> ParentNode:
  parentNode: ParentNode = ParentNode("div", [])
  blocks: list[str] = markdown_to_blocks(markdown)
  for block in blocks:
    if block:
      match block_to_block_type(block):
        case BlockType.PARAGRAPH:
          text = block.strip().replace("\n", " ")
          paragraph: ParentNode = ParentNode("p", _text_to_children(text))
          parentNode.children.append(paragraph)  # pyright: ignore[reportOptionalMemberAccess]
        case BlockType.HEADING:
          size: int = _getHeadingSize(block)
          heading: str = block.split("#" * size, 1)[-1].lstrip()
          heading_node: ParentNode = ParentNode(f"h{size}", _text_to_children(heading))
          parentNode.children.append(heading_node)  # pyright: ignore[reportOptionalMemberAccess]
        case BlockType.QUOTE:
          lines: list[str] = block.split("\n")
          cleaned_lines: list[str] = [line.lstrip("> ").strip() for line in lines]
          cleaned_text: str = "\n".join(cleaned_lines)
          parentNode.children.append(  # pyright: ignore[reportOptionalMemberAccess]
            ParentNode("blockquote", _text_to_children(cleaned_text))
          )
        case BlockType.UNORDERED_LIST:
          list_items = _convertToListItems(block)
          unordered_list: ParentNode = ParentNode("ul", list_items)
          parentNode.children.append(unordered_list)  # pyright: ignore[reportOptionalMemberAccess]
        case BlockType.ORDERED_LIST:
          list_items = _convertToListItems(block)
          ordered_list: ParentNode = ParentNode("ol", list_items)
          parentNode.children.append(ordered_list)  # pyright: ignore[reportOptionalMemberAccess]
        case BlockType.CODE:
          text: str = block.replace("```", "").strip()
          code_node: TextNode = TextNode(text, TextType.CODE)
          code_leaf_node: LeafNode = text_node_to_html_node(code_node)
          code: ParentNode = ParentNode("pre", [code_leaf_node])
          parentNode.children.append(code)  # pyright: ignore[reportOptionalMemberAccess]
  return parentNode
