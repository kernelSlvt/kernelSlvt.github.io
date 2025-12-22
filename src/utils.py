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
      date_ = date.fromisoformat(date_).strftime("%d %b, %Y")

  if not title or not date_:
    raise Exception("Invalid metadata provided.")

  return [title, date_]


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
  date_: str = metadata[1]

  html: str = (
    templ.replace("{{ Title }}", title)
    .replace("{{ Date }}", date_)
    .replace("{{ Content }}", content)
  )

  dest_path.parent.mkdir(parents=True, exist_ok=True)
  dest_path.write_text(html)
