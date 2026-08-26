from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence, TextIO

from .build import BuildOptions, SiteBuilder
from .server import serve
from .validate import SiteValidator


def create_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(prog="sitegen")
  commands = parser.add_subparsers(dest="command", required=True)

  build_parser = commands.add_parser("build", help="build the site")
  _add_drafts_option(build_parser)
  build_parser.add_argument(
    "--no-incremental",
    action="store_true",
    help="render every output instead of reusing unchanged files",
  )

  check_parser = commands.add_parser("check", help="build and validate the site")
  _add_drafts_option(check_parser)

  serve_parser = commands.add_parser("serve", help="build and serve the site")
  _add_drafts_option(serve_parser)
  serve_parser.add_argument(
    "--watch",
    action="store_true",
    help="rebuild after source changes",
  )
  serve_parser.add_argument("--host", default="127.0.0.1")
  serve_parser.add_argument("--port", type=int, default=8888)

  return parser


def _add_drafts_option(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    "--drafts",
    action="store_true",
    help="include draft content",
  )


def _build_options(arguments: argparse.Namespace) -> BuildOptions:
  return BuildOptions(
    include_drafts=arguments.drafts,
    incremental=not getattr(arguments, "no_incremental", False),
  )


def _print_report(report: object, stdout: TextIO) -> None:
  print(
    f"built {report.rendered} page(s), reused {report.reused} -> {report.output_dir}",
    file=stdout,
  )


def main(
  argv: Sequence[str] | None = None,
  *,
  project_root: Path | None = None,
  builder_factory: Callable[[Path], SiteBuilder] = SiteBuilder,
  validator_factory: Callable[[], SiteValidator] = SiteValidator,
  serve_func: Callable[..., int] = serve,
  stdout: TextIO | None = None,
  stderr: TextIO | None = None,
) -> int:
  output = stdout or sys.stdout
  errors = stderr or sys.stderr
  root = Path.cwd() if project_root is None else Path(project_root)
  arguments = create_parser().parse_args(argv)
  options = _build_options(arguments)

  try:
    if arguments.command == "serve":
      result = serve_func(
        root,
        options,
        host=arguments.host,
        port=arguments.port,
        watch=arguments.watch,
        builder_factory=builder_factory,
        stdout=output,
        stderr=errors,
      )
      return 0 if result is None else result

    builder = builder_factory(root)
    report = builder.build(options)

    if arguments.command == "build":
      _print_report(report, output)
      return 0

    issues = validator_factory().validate(Path(report.output_dir))
    if issues:
      for issue in issues:
        print(issue.format(), file=errors)
      return 1

    print(f"valid: {report.output_dir}", file=output)
    return 0
  except Exception as error:
    print(f"error: {error}", file=errors)
    return 1
