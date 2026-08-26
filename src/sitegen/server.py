from __future__ import annotations

import json
import sys
import time
import webbrowser
from collections.abc import Callable
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock, Thread, current_thread
from typing import TextIO
from urllib.parse import parse_qs, urlsplit

from .build import BuildOptions, SiteBuilder
from .config import SiteConfig
from .live_reload import LiveReloadState, inject_live_reload


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
    self._changed_paths: set[Path] = set()
    self._stop_event = Event()
    self._thread: Thread | None = None

  def poll(self, *, now: float | None = None) -> bool:
    current_time = time.monotonic() if now is None else now
    current_snapshot = self.snapshotter(self.project_root)

    if current_snapshot != self._snapshot:
      paths = set(current_snapshot) | set(self._snapshot)
      self._changed_paths.update(
        path for path in paths if current_snapshot.get(path) != self._snapshot.get(path)
      )
      self._snapshot = current_snapshot
      self._changed_at = current_time
      return False

    if self._changed_at is None:
      return False
    if current_time - self._changed_at < self.debounce_seconds:
      return False

    self._changed_at = None
    changed_paths = tuple(sorted(self._changed_paths, key=str))
    self._changed_paths.clear()
    try:
      self.on_change(changed_paths)
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
  def __init__(
    self,
    *args: object,
    directory: str | Path | None = None,
    reload_state: LiveReloadState | None = None,
    **kwargs: object,
  ) -> None:
    self.reload_state = reload_state
    super().__init__(*args, directory=directory, **kwargs)

  def guess_type(self, path: str) -> str:
    content_type = super().guess_type(path)
    if content_type.startswith("text/") and "charset=" not in content_type:
      return f"{content_type}; charset=utf-8"
    return content_type

  def end_headers(self) -> None:
    if self.reload_state is not None:
      self.send_header("Cache-Control", "no-store")
    super().end_headers()

  def log_message(self, format: str, *args: object) -> None:
    if self.reload_state is not None:
      return
    super().log_message(format, *args)

  def do_GET(self) -> None:
    if self.reload_state is not None:
      if urlsplit(self.path).path == "/__sitegen/events":
        self._serve_events()
        return
      if self._serve_live_html():
        return
    super().do_GET()

  def _serve_events(self) -> None:
    query = parse_qs(urlsplit(self.path).query)
    supplied_version = query.get("version", ["0"])[0]
    last_event_id = self.headers.get("Last-Event-ID", supplied_version)
    try:
      version = int(last_event_id)
    except ValueError:
      version = 0

    event = self.reload_state.wait_for_update(version, timeout=15)
    if event is None:
      body = b": ping\nretry: 100\n\n"
    else:
      data = json.dumps({"message": event.message})
      body = (
        f"id: {event.version}\nevent: {event.kind}\ndata: {data}\nretry: 100\n\n"
      ).encode()

    self.send_response(200)
    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def _serve_live_html(self) -> bool:
    request_path = urlsplit(self.path).path
    translated = Path(self.translate_path(request_path))
    if translated.is_dir():
      if not request_path.endswith("/"):
        return False
      translated /= "index.html"
    if translated.suffix.lower() != ".html" or not translated.is_file():
      return False

    html = translated.read_text(encoding="utf-8")
    body = inject_live_reload(html, self.reload_state.version).encode("utf-8")
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
    return True


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
  live_reload: bool = False,
  open_browser: bool = False,
  builder_factory: Callable[[Path], SiteBuilder] = SiteBuilder,
  server_factory: Callable[..., ThreadingHTTPServer] = ThreadingHTTPServer,
  watcher_factory: Callable[..., PollingWatcher] = PollingWatcher,
  handler_factory: type[SimpleHTTPRequestHandler] = SiteRequestHandler,
  reload_state_factory: Callable[[], LiveReloadState] = LiveReloadState,
  browser_opener: Callable[[str], object] = webbrowser.open,
  clock: Callable[[], float] = time.perf_counter,
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
  reload_state = reload_state_factory() if live_reload else None
  handler = partial(
    handler_factory,
    directory=served_directory,
    reload_state=reload_state,
  )
  watcher: PollingWatcher | None = None

  def rebuild(changed_paths: tuple[Path, ...] = ()) -> None:
    started_at = clock()
    displayed_paths: list[str] = []
    for path in changed_paths:
      try:
        displayed_paths.append(path.relative_to(root).as_posix())
      except ValueError:
        displayed_paths.append(path.as_posix())
    changed = ", ".join(displayed_paths) or "source change"
    try:
      rebuilt = builder.build(options)
    except Exception as error:
      elapsed_ms = round((clock() - started_at) * 1000)
      message = f"rebuild failed in {elapsed_ms}ms [{changed}]: {error}"
      print(message, file=errors)
      if reload_state is not None:
        reload_state.publish("build-error", message)
      return
    elapsed_ms = round((clock() - started_at) * 1000)
    served_directory.update(Path(rebuilt.output_dir))
    print(
      f"rebuilt {rebuilt.rendered} page(s), reused {rebuilt.reused} "
      f"in {elapsed_ms}ms [{changed}]",
      file=output,
    )
    if reload_state is not None:
      event_kind = (
        "css"
        if changed_paths
        and all(path.suffix.lower() == ".css" for path in changed_paths)
        else "reload"
      )
      reload_state.publish(event_kind, changed)

  with server_factory((host, port), handler) as httpd:
    if watch:
      watcher = watcher_factory(
        root,
        rebuild,
        initial_snapshot=initial_snapshot,
      )
      watcher.start()

    print(f"serving {output_dir} at http://{host}:{port}", file=output)
    if open_browser:
      browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
      browser_opener(f"http://{browser_host}:{port}")
    try:
      httpd.serve_forever()
    except KeyboardInterrupt:
      pass
    finally:
      if watcher is not None:
        watcher.stop()

  return 0
