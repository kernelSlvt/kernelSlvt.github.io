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

  configs: dict[str, str] = load_config()
  name: str = configs["name"]
  banner_img: str = configs["banner"]
  banner_link: str = f"<img src = '{banner_img}' alt = 'banner image'>"
  contact_dict = configs["contact"]

  blogs_path: Path = Path("./content/blog")
  blog_data: dict[str, list[str]] = walk_blogs(blogs_path)
  all_blogs_data: str = get_all_blogs(blog_data)
  recent_blogs_data: str = get_recent_blogs(blog_data)
  contact_list: str = get_contact_list(contact_dict)

  html: str = (
    templ.replace("{{ Name }}", name)
    .replace("{{ Title }}", title)
    .replace("{{ Date }}", date_)
    .replace("{{ Content }}", content)
    .replace("{{ All_blogs }}", all_blogs_data)
    .replace("{{ Recent_blogs }}", recent_blogs_data)
    .replace("{{ Banner_image }}", banner_link)
    .replace("{{ Contact }}", contact_list)
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


def get_all_blogs(blog_data: dict[str, list[str]]) -> str:
  blog_str: str = ""
  for link in blog_data:
    title: str = blog_data[link][0]
    date: str = blog_data[link][1].strftime("%d %b, %Y")  # pyright: ignore[reportAttributeAccessIssue]
    para_str: str = f'<p class = "blog-flex"><span><i>{date}</i></span><a href = "/blog/{link}">{title}</a></p>'
    blog_str += para_str
  return blog_str


def get_recent_blogs(blog_data: dict[str, list[str]]) -> str:
  blog_str: str = ""
  count: int = 0
  max_count: int = min(5, len(blog_data))
  for link in blog_data:
    count += 1
    if count > max_count:
      break
    title: str = blog_data[link][0]
    li_str: str = f'<li><a href = "/blog/{link}">{title}</a></li>'
    blog_str += li_str
  return blog_str


def get_contact_list(contact_list) -> str:
  contact_str: str = ""
  for contact in contact_list:
    values: list[str] = contact_list[contact]
    contact_str += f'<li><a href = "{values[1]}">{contact} {values[0]}</a></li>'
  return contact_str
