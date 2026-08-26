import importlib
import io
import json
import os
import sys
import tempfile
import time
import types
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from typing import Iterator


@dataclass(frozen=True)
class FakeBuildOptions:
  include_drafts: bool = False
  incremental: bool = True


class PlaceholderBuilder:
  def __init__(self, project_root: Path) -> None:
    self.project_root = project_root


class PlaceholderValidator:
  pass


@contextmanager
def import_sitegen_module(module_name: str) -> Iterator[types.ModuleType]:
  injected = {
    "sitegen.build": types.ModuleType("sitegen.build"),
    "sitegen.validate": types.ModuleType("sitegen.validate"),
  }
  injected["sitegen.build"].BuildOptions = FakeBuildOptions
  injected["sitegen.build"].SiteBuilder = PlaceholderBuilder
  injected["sitegen.validate"].SiteValidator = PlaceholderValidator
  managed_names = (*injected, "sitegen.cli", "sitegen.server")
  saved_modules = {name: sys.modules.get(name) for name in managed_names}

  for name in ("sitegen.cli", "sitegen.server"):
    sys.modules.pop(name, None)
  sys.modules.update(injected)

  try:
    yield importlib.import_module(module_name)
  finally:
    for name in managed_names:
      sys.modules.pop(name, None)
      if saved_modules[name] is not None:
        sys.modules[name] = saved_modules[name]


class RecordingBuilder:
  instances: list["RecordingBuilder"] = []
  error: Exception | None = None

  def __init__(self, project_root: Path) -> None:
    self.project_root = project_root
    self.options: list[FakeBuildOptions] = []
    self.output_dir = project_root / "docs"
    self.__class__.instances.append(self)

  def build(self, options: FakeBuildOptions) -> SimpleNamespace:
    self.options.append(options)
    if self.__class__.error is not None:
      raise self.__class__.error
    return SimpleNamespace(rendered=3, reused=2, output_dir=self.output_dir)


class FormattedIssue:
  def __init__(self, message: str) -> None:
    self.message = message

  def format(self) -> str:
    return self.message


class RecordingValidator:
  instances: list["RecordingValidator"] = []
  issues: list[FormattedIssue] = []

  def __init__(self) -> None:
    self.roots: list[Path] = []
    self.__class__.instances.append(self)

  def validate(self, root: Path) -> list[FormattedIssue]:
    self.roots.append(root)
    return list(self.__class__.issues)


class CliTestCase(unittest.TestCase):
  def setUp(self) -> None:
    RecordingBuilder.instances = []
    RecordingBuilder.error = None
    RecordingValidator.instances = []
    RecordingValidator.issues = []

  def run_cli(
    self,
    cli: types.ModuleType,
    arguments: list[str],
    project_root: Path,
    **overrides: object,
  ) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = cli.main(
      arguments,
      project_root=project_root,
      builder_factory=RecordingBuilder,
      validator_factory=RecordingValidator,
      stdout=stdout,
      stderr=stderr,
      **overrides,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


class TestBuildCommand(CliTestCase):
  def test_build_defaults_to_incremental_without_drafts(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, stdout, _ = self.run_cli(cli, ["build"], project_root)

    self.assertEqual(exit_code, 0)
    self.assertEqual(RecordingBuilder.instances[0].project_root, project_root)
    self.assertEqual(
      RecordingBuilder.instances[0].options,
      [FakeBuildOptions(include_drafts=False, incremental=True)],
    )
    self.assertIn("built 3 page(s), reused 2", stdout)
    self.assertIn(str(project_root / "docs"), stdout)

  def test_build_flags_enable_drafts_and_disable_incremental(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, _, _ = self.run_cli(
          cli,
          ["build", "--drafts", "--no-incremental"],
          project_root,
        )

    self.assertEqual(exit_code, 0)
    self.assertEqual(
      RecordingBuilder.instances[0].options,
      [FakeBuildOptions(include_drafts=True, incremental=False)],
    )

  def test_build_error_returns_nonzero_and_reports_the_failure(self) -> None:
    RecordingBuilder.error = RuntimeError("render exploded")

    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, stdout, stderr = self.run_cli(
          cli,
          ["build"],
          Path(temp_dir),
        )

    self.assertNotEqual(exit_code, 0)
    self.assertIn("render exploded", stdout + stderr)


class TestCheckCommand(CliTestCase):
  def test_check_build_error_returns_nonzero_without_validation(self) -> None:
    RecordingBuilder.error = RuntimeError("content invalid")

    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, stdout, stderr = self.run_cli(
          cli,
          ["check"],
          Path(temp_dir),
        )

    self.assertNotEqual(exit_code, 0)
    self.assertIn("content invalid", stdout + stderr)
    self.assertEqual(RecordingValidator.instances, [])

  def test_check_formats_every_issue_and_returns_nonzero(self) -> None:
    RecordingValidator.issues = [
      FormattedIssue("broken link: /missing/"),
      FormattedIssue("missing image: /images/nope.png"),
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, stdout, stderr = self.run_cli(
          cli,
          ["check", "--drafts"],
          project_root,
        )

    output = stdout + stderr
    self.assertNotEqual(exit_code, 0)
    self.assertIn("broken link: /missing/", output)
    self.assertIn("missing image: /images/nope.png", output)
    self.assertEqual(
      RecordingBuilder.instances[0].options,
      [FakeBuildOptions(include_drafts=True, incremental=True)],
    )
    self.assertEqual(
      RecordingValidator.instances[0].roots,
      [project_root / "docs"],
    )

  def test_check_returns_zero_when_the_generated_site_is_valid(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, _, _ = self.run_cli(cli, ["check"], Path(temp_dir))

    self.assertEqual(exit_code, 0)


class TestServeCommand(CliTestCase):
  def test_serve_uses_local_defaults(self) -> None:
    calls: list[tuple[str, int, bool]] = []

    def fake_serve(
      _project_root: Path,
      _options: FakeBuildOptions,
      *,
      host: str,
      port: int,
      watch: bool,
      **_: object,
    ) -> int:
      calls.append((host, port, watch))
      return 0

    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, _, _ = self.run_cli(
          cli,
          ["serve"],
          Path(temp_dir),
          serve_func=fake_serve,
        )

    self.assertEqual(exit_code, 0)
    self.assertEqual(calls, [("127.0.0.1", 8888, False)])

  def test_serve_passes_network_watch_and_draft_options(self) -> None:
    calls: list[tuple[Path, FakeBuildOptions, str, int, bool]] = []

    def fake_serve(
      project_root: Path,
      options: FakeBuildOptions,
      *,
      host: str,
      port: int,
      watch: bool,
      **_: object,
    ) -> int:
      calls.append((project_root, options, host, port, watch))
      return 0

    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, _, _ = self.run_cli(
          cli,
          [
            "serve",
            "--drafts",
            "--watch",
            "--host",
            "0.0.0.0",
            "--port",
            "4321",
          ],
          project_root,
          serve_func=fake_serve,
        )

    self.assertEqual(exit_code, 0)
    self.assertEqual(
      calls,
      [
        (
          project_root,
          FakeBuildOptions(include_drafts=True, incremental=True),
          "0.0.0.0",
          4321,
          True,
        )
      ],
    )

  def test_serve_error_returns_nonzero_and_reports_the_failure(self) -> None:
    def broken_serve(*_: object, **__: object) -> int:
      raise RuntimeError("port unavailable")

    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.cli") as cli:
        exit_code, stdout, stderr = self.run_cli(
          cli,
          ["serve"],
          Path(temp_dir),
          serve_func=broken_serve,
        )

    self.assertNotEqual(exit_code, 0)
    self.assertIn("port unavailable", stdout + stderr)


class TestServer(unittest.TestCase):
  def test_request_handler_declares_utf8_for_text_assets(self) -> None:
    with import_sitegen_module("sitegen.server") as server:
      handler = server.SiteRequestHandler.__new__(server.SiteRequestHandler)

      self.assertEqual(
        handler.guess_type("llms.txt"),
        "text/plain; charset=utf-8",
      )
      self.assertEqual(
        handler.guess_type("index.html"),
        "text/html; charset=utf-8",
      )
      self.assertEqual(handler.guess_type("image.png"), "image/png")

  def test_serve_snapshots_inputs_before_the_initial_build(self) -> None:
    events: list[object] = []
    initial_snapshot = {Path("content/post.md"): 1}

    class Builder:
      def __init__(self, project_root: Path) -> None:
        self.output_dir = project_root / "docs"

      def build(self, _options: FakeBuildOptions) -> SimpleNamespace:
        events.append("build")
        return SimpleNamespace(rendered=1, reused=0, output_dir=self.output_dir)

    class FakeWatcher:
      def __init__(
        self,
        _project_root: Path,
        _rebuild: object,
        *,
        initial_snapshot: dict[Path, int] | None = None,
      ) -> None:
        events.append(("watcher", initial_snapshot))

      def start(self) -> None:
        events.append("watcher-started")

      def stop(self) -> None:
        events.append("watcher-stopped")

    class FakeHttpServer:
      def __init__(self, _address: tuple[str, int], _handler: object) -> None:
        events.append("server")

      def __enter__(self) -> "FakeHttpServer":
        return self

      def __exit__(self, *_: object) -> None:
        pass

      def serve_forever(self) -> None:
        pass

    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.server") as server:
        server.snapshot_sources = lambda _root: events.append("snapshot") or initial_snapshot
        server.serve(
          project_root,
          FakeBuildOptions(),
          watch=True,
          builder_factory=Builder,
          server_factory=FakeHttpServer,
          watcher_factory=FakeWatcher,
          stdout=io.StringIO(),
        )

    self.assertEqual(
      events,
      [
        "snapshot",
        "build",
        "server",
        ("watcher", initial_snapshot),
        "watcher-started",
        "watcher-stopped",
      ],
    )

  def test_serve_builds_before_starting_threading_http_server(self) -> None:
    events: list[object] = []

    class Builder:
      def __init__(self, project_root: Path) -> None:
        self.output_dir = project_root / "public"

      def build(self, options: FakeBuildOptions) -> SimpleNamespace:
        events.append(("build", options))
        return SimpleNamespace(rendered=1, reused=0, output_dir=self.output_dir)

    class FakeHttpServer:
      def __init__(self, address: tuple[str, int], handler: object) -> None:
        events.append(("server", address, handler))

      def __enter__(self) -> "FakeHttpServer":
        return self

      def __exit__(self, *_: object) -> None:
        events.append("closed")

      def serve_forever(self) -> None:
        events.append("serve_forever")

    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.server") as server:
        server.serve(
          project_root,
          FakeBuildOptions(),
          host="127.0.0.1",
          port=9876,
          watch=False,
          builder_factory=Builder,
          server_factory=FakeHttpServer,
          stdout=io.StringIO(),
        )

    self.assertIs(server.ThreadingHTTPServer, ThreadingHTTPServer)
    self.assertEqual(events[0], ("build", FakeBuildOptions()))
    self.assertEqual(events[1][0:2], ("server", ("127.0.0.1", 9876)))
    self.assertEqual(
      os.fspath(events[1][2].keywords["directory"]),
      str(project_root / "public"),
    )
    self.assertEqual(events[2:], ["serve_forever", "closed"])

  def test_serve_does_not_open_a_socket_when_the_initial_build_fails(self) -> None:
    server_started = False

    class BrokenBuilder:
      def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

      def build(self, options: FakeBuildOptions) -> SimpleNamespace:
        raise RuntimeError("initial build failed")

    def server_factory(*_: object) -> object:
      nonlocal server_started
      server_started = True
      return object()

    with tempfile.TemporaryDirectory() as temp_dir:
      with import_sitegen_module("sitegen.server") as server:
        with self.assertRaisesRegex(RuntimeError, "initial build failed"):
          server.serve(
            Path(temp_dir),
            FakeBuildOptions(),
            host="127.0.0.1",
            port=8888,
            watch=False,
            builder_factory=BrokenBuilder,
            server_factory=server_factory,
          )

    self.assertFalse(server_started)

  def test_watch_rebuild_failure_keeps_server_running_and_stops_watcher(self) -> None:
    events: list[object] = []

    class Builder:
      def __init__(self, project_root: Path) -> None:
        self.output_dir = project_root / "docs"
        self.attempts = 0

      def build(self, options: FakeBuildOptions) -> SimpleNamespace:
        self.attempts += 1
        events.append(("build", self.attempts))
        if self.attempts == 2:
          raise RuntimeError("broken rebuild")
        return SimpleNamespace(rendered=1, reused=0, output_dir=self.output_dir)

    class FakeWatcher:
      def __init__(self, project_root: Path, rebuild: object, **_: object) -> None:
        self.project_root = project_root
        self.rebuild = rebuild
        events.append(("watcher", project_root))

      def start(self) -> None:
        events.append("watcher-started")
        self.rebuild()

      def stop(self) -> None:
        events.append("watcher-stopped")

    class FakeHttpServer:
      def __init__(self, _address: tuple[str, int], _handler: object) -> None:
        pass

      def __enter__(self) -> "FakeHttpServer":
        return self

      def __exit__(self, *_: object) -> None:
        events.append("server-closed")

      def serve_forever(self) -> None:
        events.append("serve_forever")

    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.server") as server:
        server.serve(
          project_root,
          FakeBuildOptions(),
          host="127.0.0.1",
          port=8888,
          watch=True,
          builder_factory=Builder,
          server_factory=FakeHttpServer,
          watcher_factory=FakeWatcher,
          stdout=io.StringIO(),
          stderr=stderr,
        )

    self.assertIn("broken rebuild", stderr.getvalue())
    self.assertEqual(
      events,
      [
        ("build", 1),
        ("watcher", project_root),
        "watcher-started",
        ("build", 2),
        "serve_forever",
        "watcher-stopped",
        "server-closed",
      ],
    )

  def test_watch_updates_the_served_directory_after_a_valid_move(self) -> None:
    captured_handler: list[object] = []

    class Builder:
      def __init__(self, project_root: Path) -> None:
        self.outputs = [project_root / "docs", project_root / "preview"]

      def build(self, _options: FakeBuildOptions) -> SimpleNamespace:
        output_dir = self.outputs.pop(0)
        return SimpleNamespace(rendered=1, reused=0, output_dir=output_dir)

    class FakeWatcher:
      def __init__(self, _project_root: Path, rebuild: object, **_: object) -> None:
        self.rebuild = rebuild

      def start(self) -> None:
        self.rebuild()

      def stop(self) -> None:
        pass

    class FakeHttpServer:
      def __init__(self, _address: tuple[str, int], handler: object) -> None:
        captured_handler.append(handler)

      def __enter__(self) -> "FakeHttpServer":
        return self

      def __exit__(self, *_: object) -> None:
        pass

      def serve_forever(self) -> None:
        pass

    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      with import_sitegen_module("sitegen.server") as server:
        server.serve(
          project_root,
          FakeBuildOptions(),
          watch=True,
          builder_factory=Builder,
          server_factory=FakeHttpServer,
          watcher_factory=FakeWatcher,
          stdout=io.StringIO(),
        )

    directory = captured_handler[0].keywords["directory"]
    self.assertEqual(os.fspath(directory), str(project_root / "preview"))


class TestPollingWatcher(unittest.TestCase):
  def test_snapshot_sources_tracks_only_build_inputs(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      tracked_paths = [
        project_root / "config.json",
        project_root / "content" / "post" / "index.md",
        project_root / "templates" / "blog.html",
        project_root / "static" / "index.css",
      ]
      ignored_paths = [
        project_root / "docs" / "index.html",
        project_root / "README.md",
      ]
      for path in tracked_paths + ignored_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.name)

      with import_sitegen_module("sitegen.server") as server:
        snapshot = server.snapshot_sources(project_root)

    self.assertEqual(set(snapshot), set(tracked_paths))
    self.assertTrue(all(isinstance(mtime, int) for mtime in snapshot.values()))

  def test_snapshot_sources_uses_configured_input_directories(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
      project_root = Path(temp_dir)
      project_root.joinpath("config.json").write_text(
        json.dumps(
          {
            "site_url": "https://example.com",
            "email": "hello@example.com",
            "social_image": "/social.png",
            "content_dir": "articles",
            "template_dir": "views",
            "static_dir": "assets",
          }
        )
      )
      configured_paths = [
        project_root / "articles" / "post.md",
        project_root / "views" / "page.html",
        project_root / "assets" / "site.css",
      ]
      default_path = project_root / "content" / "ignored.md"
      for path in configured_paths + [default_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(path.name)

      with import_sitegen_module("sitegen.server") as server:
        snapshot = server.snapshot_sources(project_root)

    self.assertEqual(
      set(snapshot),
      {project_root / "config.json", *configured_paths},
    )

  def test_polling_watcher_debounces_and_coalesces_changes(self) -> None:
    state = {"snapshot": {Path("content/post.md"): 1}}
    rebuilds: list[str] = []

    def snapshotter(_: Path) -> dict[Path, int]:
      return dict(state["snapshot"])

    with import_sitegen_module("sitegen.server") as server:
      watcher = server.PollingWatcher(
        Path("/project"),
        lambda: rebuilds.append("rebuilt"),
        debounce_seconds=0.2,
        snapshotter=snapshotter,
      )

      state["snapshot"] = {Path("content/post.md"): 2}
      watcher.poll(now=1.0)
      state["snapshot"] = {Path("content/post.md"): 3}
      watcher.poll(now=1.1)
      watcher.poll(now=1.29)
      watcher.poll(now=1.31)

    self.assertEqual(rebuilds, ["rebuilt"])

  def test_polling_watcher_survives_failure_and_rebuilds_next_change(self) -> None:
    state = {"snapshot": {Path("templates/blog.html"): 1}}
    attempts = 0

    def snapshotter(_: Path) -> dict[Path, int]:
      return dict(state["snapshot"])

    def rebuild() -> None:
      nonlocal attempts
      attempts += 1
      if attempts == 1:
        raise RuntimeError("bad template")

    with tempfile.TemporaryDirectory() as temp_dir:
      output = Path(temp_dir) / "docs" / "index.html"
      output.parent.mkdir(parents=True)
      output.write_text("last valid output")

      with import_sitegen_module("sitegen.server") as server:
        watcher = server.PollingWatcher(
          Path(temp_dir),
          rebuild,
          debounce_seconds=0.1,
          snapshotter=snapshotter,
          stderr=io.StringIO(),
        )

        state["snapshot"] = {Path("templates/blog.html"): 2}
        watcher.poll(now=1.0)
        watcher.poll(now=1.11)
        self.assertEqual(output.read_text(), "last valid output")

        state["snapshot"] = {Path("templates/blog.html"): 3}
        watcher.poll(now=2.0)
        watcher.poll(now=2.11)

    self.assertEqual(attempts, 2)

  def test_stop_waits_for_an_active_rebuild(self) -> None:
    state = {"snapshot": {Path("content/post.md"): 1}}
    rebuild_started = Event()
    release_rebuild = Event()

    def snapshotter(_: Path) -> dict[Path, int]:
      return dict(state["snapshot"])

    def rebuild() -> None:
      rebuild_started.set()
      release_rebuild.wait()

    with import_sitegen_module("sitegen.server") as server:
      watcher = server.PollingWatcher(
        Path("/project"),
        rebuild,
        debounce_seconds=0,
        poll_interval=0.01,
        snapshotter=snapshotter,
      )
      watcher.start()
      state["snapshot"] = {Path("content/post.md"): 2}
      self.assertTrue(rebuild_started.wait(timeout=1))

      releaser = Thread(
        target=lambda: (time.sleep(1.1), release_rebuild.set()),
        daemon=True,
      )
      releaser.start()
      started_at = time.monotonic()
      watcher.stop()
      elapsed = time.monotonic() - started_at
      releaser.join()

    self.assertGreaterEqual(elapsed, 1.05)
    self.assertFalse(watcher._thread.is_alive())


if __name__ == "__main__":
  unittest.main()
