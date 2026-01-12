import logging
import shutil
import time
from pathlib import Path

from utils import (
  copy_files,
  generate_page,
  generate_pages_recursive,
)

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
  logging.basicConfig(filename="file_events.log", level=logging.INFO)
  logging.info(f"STARTED at {time.asctime()}")

  # clean the public/
  dest_path: Path = Path("./docs")
  src_path: Path = Path("./static")
  if dest_path.exists():
    shutil.rmtree(dest_path)
  dest_path.mkdir(parents=True, exist_ok=True)
  # copy all the files and subdirectories from static/ to public/
  copy_files(src_path, dest_path)

  # generate the index page
  index_path: Path = Path("./content/_index.md")
  index_template_path: Path = Path("./templates/home.html")
  index_dest_path: Path = Path("./docs/index.html")
  generate_page(index_path, index_template_path, index_dest_path)

  # generate the blog index page
  blog_index_path: Path = Path("./content/blog/_index.md")
  blog_index_template_path: Path = Path("./templates/blog_index.html")
  blog_index_dest_path: Path = Path("./docs/blog/index.html")
  generate_page(blog_index_path, blog_index_template_path, blog_index_dest_path)

  # generate the blogs dir
  blogs_path: Path = Path("./content/")
  blog_template_path: Path = Path("./templates/blogs.html")
  blogs_dest_path: Path = Path("./docs/")
  generate_pages_recursive(blogs_path, blog_template_path, blogs_dest_path)

  logging.info(f"FINISHED at {time.asctime()}\n")


if __name__ == "__main__":
  main()
