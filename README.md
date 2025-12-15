idea:
- split md into blocks
- convert each block to tree of `HTMLNode` objs

  raw md -> `TextNode` -> `HTMLNode`
- join all html nodes

![architecture](architecture.png)
