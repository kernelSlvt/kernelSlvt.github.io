import re
from datetime import date, datetime
from pathlib import Path

import yaml

from sitegen.models import ContentError, PageMetadata, ParsedDocument

LEGACY_DELIMITER = re.compile(r"(?m)^-----[ \t]*$")
YAML_DELIMITER = re.compile(r"(?m)^---[ \t]*$")
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")


def parse_document(path: Path) -> ParsedDocument:
  try:
    text = path.read_text(encoding="utf-8")
  except OSError as exc:
    raise ContentError(f"{path}: unable to read content: {exc}") from exc

  header, body = _split_front_matter(path, text)
  try:
    raw = yaml.safe_load(header) or {}
  except yaml.YAMLError as exc:
    raise ContentError(f"{path}: invalid YAML metadata: {exc}") from exc
  if not isinstance(raw, dict):
    raise ContentError(f"{path}: metadata must be a mapping")

  title = _required_string(path, raw, "title")
  published = _date_value(path, raw.get("date"), "date", required=True)
  updated = _date_value(path, raw.get("updated"), "updated", required=False)
  draft = raw.get("draft", False)
  if not isinstance(draft, bool):
    raise ContentError(f"{path}: draft must be true or false")

  slug = _optional_string(path, raw, "slug")
  if slug and not SLUG_PATTERN.fullmatch(slug):
    raise ContentError(
      f"{path}: slug must contain lowercase letters, digits, hyphens, or underscores"
    )

  permalink = _optional_string(path, raw, "permalink")
  if permalink:
    if not permalink.startswith("/") or not permalink.endswith("/"):
      raise ContentError(f"{path}: permalink must start and end with /")
    if ".." in permalink or "//" in permalink or "?" in permalink or "#" in permalink:
      raise ContentError(f"{path}: permalink contains an invalid path segment")

  tags = _tags_value(path, raw.get("tags"))
  metadata = PageMetadata(
    title=title,
    date=published,
    updated=updated,
    draft=draft,
    slug=slug,
    permalink=permalink,
    description=_optional_string(path, raw, "description"),
    social_image=_optional_string(path, raw, "social_image"),
    tags=tags,
    template=_optional_string(path, raw, "template"),
  )
  return ParsedDocument(metadata=metadata, body=body)


def _split_front_matter(path: Path, text: str) -> tuple[str, str]:
  if text.startswith("---\n") or text.startswith("---\r\n"):
    matches = list(YAML_DELIMITER.finditer(text))
    if len(matches) < 2:
      raise ContentError(f"{path}: unclosed YAML front matter")
    header = text[matches[0].end() : matches[1].start()].lstrip("\r\n")
    body = _remove_one_line_ending(text[matches[1].end() :])
    return header, body

  match = LEGACY_DELIMITER.search(text)
  if not match:
    raise ContentError(f"{path}: missing front matter delimiter")
  header = text[: match.start()].rstrip("\r\n")
  body = _remove_one_line_ending(text[match.end() :])
  return header, body


def _remove_one_line_ending(text: str) -> str:
  if text.startswith("\r\n"):
    return text[2:]
  if text.startswith("\n") or text.startswith("\r"):
    return text[1:]
  return text


def _required_string(path: Path, raw: dict, key: str) -> str:
  value = raw.get(key)
  if not isinstance(value, str) or not value.strip():
    raise ContentError(f"{path}: missing required {key}")
  return value.strip()


def _optional_string(path: Path, raw: dict, key: str) -> str | None:
  value = raw.get(key)
  if value is None:
    return None
  if not isinstance(value, str) or not value.strip():
    raise ContentError(f"{path}: {key} must be a non-empty string")
  return value.strip()


def _date_value(
  path: Path, value: object, key: str, *, required: bool
) -> date | None:
  if value is None:
    if required:
      raise ContentError(f"{path}: missing required {key}")
    return None
  if isinstance(value, datetime):
    return value.date()
  if isinstance(value, date):
    return value
  if isinstance(value, str):
    try:
      return date.fromisoformat(value)
    except ValueError as exc:
      raise ContentError(f"{path}: invalid {key}: expected YYYY-MM-DD") from exc
  raise ContentError(f"{path}: invalid {key}: expected YYYY-MM-DD")


def _tags_value(path: Path, value: object) -> tuple[str, ...]:
  if value in (None, ""):
    return ()
  if isinstance(value, str):
    candidates = value.split(",")
  elif isinstance(value, list):
    candidates = value
  else:
    raise ContentError(f"{path}: tags must be a list or comma-separated string")

  tags: list[str] = []
  for candidate in candidates:
    if not isinstance(candidate, str) or not candidate.strip():
      raise ContentError(f"{path}: every tag must be a non-empty string")
    tag = candidate.strip()
    if tag not in tags:
      tags.append(tag)
  return tuple(tags)
