import json
import logging
import os
import shutil
from datetime import date
from pathlib import Path

from block_md import markdown_to_html_node
from htmlnode import ParentNode

logger: logging.Logger = logging.getLogger(__name__)


def extract_metadata(markdown: str) -> list[str]:
  metadata: list[str] = markdown.split("-----", 1)[0].strip().split("\n")
  title: str = ""
  date_: str = ""
  for line in metadata:
    if line.startswith("title"):
      title = line.split("title:", 1)[-1].strip()
    if line.startswith("date"):
      # print(line.split("date:", 1))
      date_ = line.split("date:", 1)[1].strip()
      date_ = date.fromisoformat(date_)  # pyright: ignore[reportAssignmentType]

  if not title or not date_:
    raise Exception("Invalid metadata provided.")

  return [title, date_]


def load_config() -> dict[str, str]:
  config_path: Path = Path("./config.json")
  data: dict[str, str] = json.loads(config_path.read_text())
  return data


def copy_files(src: Path, dest: Path) -> None:
  contents: list[str] = os.listdir(src)
  for content in contents:
    file_path: Path = src / content
    dest_path: Path = dest / content

    if file_path.is_file():
      logging.info(f"Copy {file_path}")
      shutil.copy(file_path, dest_path)
    else:
      dest_path.mkdir(exist_ok=True)
      copy_files(file_path, dest_path)


def generate_pages_recursive(
  dir_path_content: Path, template_path: Path, dest_dir_path: Path
) -> None:
  dest_dir_path.mkdir(exist_ok=True, parents=True)
  contents: list[str] = os.listdir(dir_path_content)
  for content in contents:
    file_path: Path = dir_path_content / content
    dest_path: Path = dest_dir_path / content

    if file_path.is_file():
      if file_path.name.startswith("_"):
        continue
      generate_page(file_path, template_path, dest_path)
      dest_path.rename(dest_path.with_suffix(".html"))
    else:
      dest_path.mkdir(exist_ok=True)
      generate_pages_recursive(file_path, template_path, dest_path)


def generate_page(from_path: Path, template_path: Path, dest_path: Path) -> None:
  logging.info(
    f"Generating page from {from_path} to {dest_path} using {template_path}."
  )

  markdown: str = from_path.read_text("utf-8")
  templ: str = template_path.read_text("utf-8")

  html_node: ParentNode = markdown_to_html_node(markdown)
  content: str = html_node.to_html()

  metadata: list[str] = extract_metadata(markdown)
  title: str = metadata[0]
  date_: str = metadata[1].strftime("%d %b, %Y")  # pyright: ignore[reportAttributeAccessIssue]

  blogs_path: Path = Path("./content/blogs")
  blog_data: dict[str, list[str]] = walk_blogs(blogs_path)
  blogs_listing: str = get_blogs(blog_data, "blogs")

  writeups_path: Path = Path("./content/writeups")
  writeups_data: dict[str, list[str]] = walk_blogs(writeups_path)
  writeups_listing: str = get_blogs(writeups_data, "writeups")

  html: str = (
    templ.replace("{{ Title }}", title)
    .replace("{{ Date }}", date_)
    .replace("{{ Content }}", content)
    .replace("{{ Blogs }}", blogs_listing)
    .replace("{{ Writeups }}", writeups_listing)
  )

  dest_path.parent.mkdir(parents=True, exist_ok=True)
  dest_path.write_text(html)


def walk_blogs(blog_path: Path) -> dict[str, list[str]]:
  if not blog_path.exists() or not blog_path.is_dir():
    raise Exception("Invalid blog path passed!")

  data: dict[str, list[str]] = {}
  contents: list[str] = os.listdir(blog_path)
  contents_path: list[Path] = [blog_path / content for content in contents]

  for content in contents_path:
    if content.is_dir():
      file_path: Path = Path(content / "index.md")
      metadata: list[str] = extract_metadata(file_path.read_text())
      title: str = metadata[0]
      date_: str = metadata[1]
      data[str(content.name)] = [title, date_]

  # sorting the dict based on the date
  sorted_items: list[tuple[str, list[str]]] = sorted(
    data.items(), key=lambda x: x[1][1], reverse=True
  )
  sorted_dict: dict[str, list[str]] = dict(sorted_items)

  return sorted_dict


def get_blogs(blog_data: dict[str, list[str]], type: str) -> str:
  if type not in ["blogs", "writeups"]:
    raise Exception("Invalid blog type passed\nAllowed: blogs, writeups")
  blog_str: str = ""
  for link in blog_data:
    title: str = blog_data[link][0]
    date: str = blog_data[link][1].strftime("%b %Y").lower()  # pyright: ignore[reportAttributeAccessIssue]
    p_str: str = (
      f'<p class = "home-list">[{date}] <a href = "/{type}/{link}">{title}</a></p>'
    )
    blog_str += p_str
  return blog_str
