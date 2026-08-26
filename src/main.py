from pathlib import Path

from sitegen.build import SiteBuilder


def main():
  return SiteBuilder(Path.cwd()).build()


if __name__ == "__main__":
  main()
