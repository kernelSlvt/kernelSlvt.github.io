from __future__ import annotations

import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock, Thread, current_thread
from typing import Callable, TextIO

from .build import BuildOptions, SiteBuilder
from .config import SiteConfig


SOURCE_INPUTS = ("config.json", "content", "templates", "static")


def _source_inputs(project_root: Path) -> tuple[Path, ...]:
  defaults = tuple(project_root / name for name in SOURCE_INPUTS)
  try:
    config = SiteConfig.load(project_root)
  except (OSError, ValueError):
    return defaults
  return (
    project_root / "config.json",
    config.content_dir,
    config.template_dir,
    config.static_dir,
  )


def snapshot_sources(project_root: Path) -> dict[Path, int]:
  root = Path(project_root)
  snapshot: dict[Path, int] = {}

  for path in _source_inputs(root):
    if path.is_file():
      try:
        snapshot[path] = path.stat().st_mtime_ns
      except FileNotFoundError:
        pass
      continue

    if not path.is_dir():
      continue

    for child in sorted(path.rglob("*")):
      if not child.is_file():
        continue
      try:
        snapshot[child] = child.stat().st_mtime_ns
      except FileNotFoundError:
        pass

  return snapshot


class PollingWatcher:
  def __init__(
    self,
    project_root: Path,
    on_change: Callable[[], None],
    *,
    debounce_seconds: float = 0.25,
    poll_interval: float = 0.1,
    snapshotter: Callable[[Path], dict[Path, int]] = snapshot_sources,
    initial_snapshot: dict[Path, int] | None = None,
    stderr: TextIO | None = None,
  ) -> None:
    self.project_root = Path(project_root)
    self.on_change = on_change
    self.debounce_seconds = debounce_seconds
    self.poll_interval = poll_interval
    self.snapshotter = snapshotter
    self.stderr = stderr or sys.stderr
    self._snapshot = (
      dict(initial_snapshot)
      if initial_snapshot is not None
      else self.snapshotter(self.project_root)
    )
    self._changed_at: float | None = None
    self._stop_event = Event()
    self._thread: Thread | None = None

  def poll(self, *, now: float | None = None) -> bool:
    current_time = time.monotonic() if now is None else now
    current_snapshot = self.snapshotter(self.project_root)

    if current_snapshot != self._snapshot:
      self._snapshot = current_snapshot
      self._changed_at = current_time
      return False

    if self._changed_at is None:
      return False
    if current_time - self._changed_at < self.debounce_seconds:
      return False

    self._changed_at = None
    try:
      self.on_change()
    except Exception as error:
      print(f"rebuild failed: {error}", file=self.stderr)
    return True

  def run(self) -> None:
    while not self._stop_event.wait(self.poll_interval):
      self.poll()

  def start(self) -> None:
    if self._thread is not None and self._thread.is_alive():
      return
    self._stop_event.clear()
    self._thread = Thread(target=self.run, name="sitegen-watch", daemon=True)
    self._thread.start()

  def stop(self) -> None:
    self._stop_event.set()
    if self._thread is None or self._thread is current_thread():
      return
    self._thread.join()


class SiteRequestHandler(SimpleHTTPRequestHandler):
  def guess_type(self, path: str) -> str:
    content_type = super().guess_type(path)
    if content_type.startswith("text/") and "charset=" not in content_type:
      return f"{content_type}; charset=utf-8"
    return content_type


class ServedDirectory:
  def __init__(self, path: Path) -> None:
    self._path = Path(path)
    self._lock = Lock()

  def update(self, path: Path) -> None:
    with self._lock:
      self._path = Path(path)

  def __fspath__(self) -> str:
    with self._lock:
      return str(self._path)


def serve(
  project_root: Path,
  options: BuildOptions,
  *,
  host: str = "127.0.0.1",
  port: int = 8888,
  watch: bool = False,
  builder_factory: Callable[[Path], SiteBuilder] = SiteBuilder,
  server_factory: Callable[..., ThreadingHTTPServer] = ThreadingHTTPServer,
  watcher_factory: Callable[..., PollingWatcher] = PollingWatcher,
  handler_factory: type[SimpleHTTPRequestHandler] = SiteRequestHandler,
  stdout: TextIO | None = None,
  stderr: TextIO | None = None,
) -> int:
  output = stdout or sys.stdout
  errors = stderr or sys.stderr
  root = Path(project_root)
  initial_snapshot = snapshot_sources(root) if watch else None
  builder = builder_factory(root)
  report = builder.build(options)
  output_dir = Path(report.output_dir)
  served_directory = ServedDirectory(output_dir)
  handler = partial(handler_factory, directory=served_directory)
  watcher: PollingWatcher | None = None

  def rebuild() -> None:
    try:
      rebuilt = builder.build(options)
    except Exception as error:
      print(f"rebuild failed: {error}", file=errors)
      return
    served_directory.update(Path(rebuilt.output_dir))
    print(
      f"rebuilt {rebuilt.rendered} page(s), reused {rebuilt.reused}",
      file=output,
    )

  with server_factory((host, port), handler) as httpd:
    if watch:
      watcher = watcher_factory(
        root,
        rebuild,
        initial_snapshot=initial_snapshot,
      )
      watcher.start()

    print(f"serving {output_dir} at http://{host}:{port}", file=output)
    try:
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass
    finally:
      if watcher is not None:
        watcher.stop()

  return 0
