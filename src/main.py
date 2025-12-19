import logging
import shutil
import time
from pathlib import Path

from utils import copy_files, generate_pages_recursive

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
  logging.basicConfig(filename="file_events.log", level=logging.INFO)
  logging.info(f"STARTED at {time.asctime()}")

  # clean the public/
  dest_path: Path = Path("./public")
  src_path: Path = Path("./static")
  if dest_path.exists():
    shutil.rmtree(dest_path)
  dest_path.mkdir(parents=True, exist_ok=True)
  # copy all the files and subdirectories from static/ to public/
  copy_files(src_path, dest_path)

  # generate the index page
  content_path: Path = Path("./content")
  template_path: Path = Path("./template.html")
  public_path: Path = Path("./public")
  generate_pages_recursive(content_path, template_path, public_path)

  logging.info(f"FINISHED at {time.asctime()}\n")


if __name__ == "__main__":
  main()
