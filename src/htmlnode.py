class HTMlNode:
  def __init__(
    self,
    tag: str | None = None,
    value: str | None = None,
    children=None,
    props: dict[str, str] | None = None,
  ) -> None:
    self.tag: str | None = tag
    self.value: str | None = value
    self.children: list[HTMlNode] | None = children
    self.props: dict[str, str] | None = props

  def to_html(self):
    raise NotImplementedError()

  def props_to_html(self) -> str:
    if self.props:
      string: str = ""
      for key in self.props:
        string += f' {key}="{self.props[key]}"'
      return string
    else:
      return ""

  def __repr__(self) -> str:
    return (
      f"HTMLNode({self.tag}, {self.value}, children: {self.children}, {self.props})"
    )


class LeafNode(HTMlNode):
  # html node with no children
  def __init__(
    self, tag: str | None, value: str | None, props: dict[str, str] | None = None
  ) -> None:
    super().__init__(tag, value, None, props)

  def to_html(self) -> str:
    if self.value is None:
      raise ValueError("invalid html: no values. LOL")
    if self.tag is None:
      return self.value
    return f"<{self.tag}{self.props_to_html()}>{self.value}</{self.tag}>"

  def __repr__(self) -> str:
    return f"LeafNode({self.tag}, {self.value}, {self.props})"


class ParentNode(HTMlNode):
  # any node that is not a leaf node is a parent node
  def __init__(self, tag: str, children, props: dict[str, str] | None = None) -> None:
    super().__init__(tag, None, children, props)

  def to_html(self) -> str:
    if not self.tag:
      raise ValueError("invalid html: no tag available")
    if self.children is None:
      raise ValueError("invlaid parent node: no children available")

    inner_html: str = ""
    for node in self.children:
      inner_html += node.to_html()
    return f"<{self.tag}{self.props_to_html()}>{inner_html}</{self.tag}>"

  def __repr__(self) -> str:
    return f"ParentNode({self.tag}, children: {self.children}, {self.props})"
