import unittest

from block_md import (
  BlockType,
  block_to_block_type,
  markdown_to_blocks,
  markdown_to_html_node,
)


class TestBlockMd(unittest.TestCase):
  def test_markdown_to_blocks(self) -> None:
    md = """
this is **bolded** line

 this is another line with _italic_ text and
this is line with **bolded** text on the same line

- this is a list
- with items
"""
    blocks = markdown_to_blocks(md)
    self.assertListEqual(
      [
        "this is **bolded** line",
        "this is another line with _italic_ text and\nthis is line with **bolded** text on the same line",
        "- this is a list\n- with items",
      ],
      blocks,
    )

  def test_block_type_para(self) -> None:
    md = "hello my name is sarthak"
    self.assertEqual(BlockType.PARAGRAPH, block_to_block_type(md))

  def test_block_type_heading(self) -> None:
    md = "##this is a heading"
    self.assertEqual(BlockType.HEADING, block_to_block_type(md))

  def test_block_type_code(self) -> None:
    md = "```\nthis is my python code\n```"
    self.assertEqual(BlockType.CODE, block_to_block_type(md))

  def test_block_type_not_code(self) -> None:
    md = "```\nthis is my python code\n``"
    self.assertEqual(BlockType.PARAGRAPH, block_to_block_type(md))

  def test_block_type_quote(self) -> None:
    md = ">hello my name is sarthak\n>im 19"
    self.assertEqual(BlockType.QUOTE, block_to_block_type(md))

  def test_block_type_not_quote(self) -> None:
    md = ">hello my name is sarthak\nim 19"
    self.assertEqual(BlockType.PARAGRAPH, block_to_block_type(md))

  def test_block_type_unordered_list(self) -> None:
    md = "- this is a list\n- true, another line"
    self.assertEqual(BlockType.UNORDERED_LIST, block_to_block_type(md))

  def test_block_type_not_unordered_list(self) -> None:
    md = "- this is a list\ntrue, another line"
    self.assertEqual(BlockType.PARAGRAPH, block_to_block_type(md))

  def test_block_type_ordered_list(self) -> None:
    md = "1. this is a list\n2. true, another line"
    self.assertEqual(BlockType.ORDERED_LIST, block_to_block_type(md))

  def test_block_type_not_ordered_list(self) -> None:
    md = "1. this is a list\n- true, another line"
    self.assertEqual(BlockType.PARAGRAPH, block_to_block_type(md))

  def test_md_to_html_paragraphs(self) -> None:
    md = """
this is **bolded** paragraph
text in a p
tag here

this is another paragraph with _italic_ text and `code` here

"""
    node = markdown_to_html_node(md)
    html = node.to_html()
    self.assertEqual(
      html,
      "<div><p>this is <b>bolded</b> paragraph text in a p tag here</p><p>this is another paragraph with <i>italic</i> text and <code>code</code> here</p></div>",
    )

  def test_md_to_html_codeblock(self) -> None:
    md = """
```
this is text that _should_ remain
the **same** even with inline stuff
```
"""
    node = markdown_to_html_node(md)
    html = node.to_html()
    self.assertEqual(
      html,
      "<div><pre><code>this is text that _should_ remain\\nthe **same** even with inline stuff\\n</code></pre></div>",
    )

  def test_md_to_html_whole(self) -> None:
    md = """
## this is a h2 heading _italic word_

this is a paragraph with **bold** and _italic_ words with a [link](https://google.com)

this is an unordered list

1. apples
2. _organges_
3. [github](https://github.com)


tv girl albums name

- Who Really Cares
- French Exit
- Death of a Party Girl
- **bold** word and an _italic_ word with [link](https://spotify.com)


![image](https://cdn.pfps.gg/pfps/76557-old.gif)

```
print("hello world")
```

> this is a blockquote
> spanning into another line
"""
    node = markdown_to_html_node(md)
    html = node.to_html()
    self.maxDiff = None
    right_html = """<div><h2>this is a h2 heading <i>italic word</i></h2><p>this is a paragraph with <b>bold</b> and <i>italic</i> words with a <a href="https://google.com">link</a></p><p>this is an unordered list</p><ol><li>apples</li><li><i>organges</i></li><li><a href="https://github.com">github</a></li></ol><p>tv girl albums name</p><ul><li>Who Really Cares</li><li>French Exit</li><li>Death of a Party Girl</li><li><b>bold</b> word and an <i>italic</i> word with <a href="https://spotify.com">link</a></li></ul><p><img src="https://cdn.pfps.gg/pfps/76557-old.gif" alt="image"></img></p><pre><code>print("hello world")\\n</code></pre><blockquote>this is a blockquote\n spanning into another line</blockquote></div>"""
    self.assertEqual(html, right_html)


if __name__ == "__main__":
  unittest.main()
