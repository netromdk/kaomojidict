#!/usr/bin/env python3
"""Build a kaomoji dictionary for HeliBoard / AOSP keyboards.

Usage:
  python build_kaomoji_dict.py <input.json> [-o output.dict] [--jar path/to/dicttool_aosp.jar]

Input JSON format:
  {
    "locale": "en",
    "description": "Kaomoji dictionary",
    "version": 1,
    "kaomoji": {
      "¯╲_(ツ)_╱¯": ["shrug", "shrugging"],
      "(╯°□°)╯︵┻━┻": ["tableflip", "rage"]
    }
  }

When --locale is not given, it is read from the input JSON file (fallback "en").
If no input file is given, kaomoji_en.json is used as the default.
"""

import argparse
import json
import re
import shutil
import string
import unicodedata
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = "kaomoji.json"

# Flag bits for the AOSP dictionary combined format:
NOT_A_WORD = 2  # Entry is a shortcut, not a real word.
HAS_EMOJI = 4   # Render the shortcut content inline in suggestions.
PROBING = 8     # Include in suggestion-bar probing.
KAOMOJI_FLAGS = NOT_A_WORD | HAS_EMOJI | PROBING

# Regex to split combined-file headers on commas that separate known fields, correctly handling
# commas inside values like descriptions.
_HEADER_RE = re.compile(r",(?=(?:description|date|version|dictionary|locale)=)")


def build_combined(
  kaomoji_map: dict[str, list[str]],
  locale: str = "en",
  description: str = "Kaomoji dictionary",
  version: int = 1,
  date: int | None = None,
  word_joiner: bool = False,
) -> str:
  if date is None:
    date = int(time.time())
  lines = [
    f"dictionary=kaomoji:{locale},locale={locale},"
    f"description={description},date={date},version={version}",
  ]
  lines += _build_kaomoji_lines(kaomoji_map, word_joiner=word_joiner)
  return "\n".join(lines)


def merge_with_combined(
  kaomoji_map: dict[str, list[str]],
  combined_path: str | Path,
  description: str = "Kaomoji dictionary",
  version: int = 1,
  all_locales: bool = False,
  date: int | None = None,
  word_joiner: bool = False,
) -> str:
  """Merge kaomoji entries into an existing .combined wordlist file."""
  if date is None:
    date = int(time.time())

  combined = Path(combined_path)
  if not combined.is_file():
    raise FileNotFoundError(f"Combined file not found: {combined_path}")

  with open(combined, encoding="utf-8") as f:
    content = f.read()

  parts = _HEADER_RE.split(header_line)
  for part in parts:
    if "=" not in part:
      raise ValueError(
        f"Malformed header part {part!r} in {combined_path}. "
        "This may indicate an unexpected comma in a header value."
      )
  orig_desc = ""
  orig_version = None
  locale_from_header = ""
  for part in parts:
    if part.startswith("description="):
      orig_desc = part.split("=", 1)[1]
    elif part.startswith("version="):
      orig_version = int(part.split("=", 1)[1])
    elif part.startswith("locale="):
      locale_from_header = part.split("=", 1)[1]

  marker = " <all locales>" if all_locales else ""
  full_desc = (
    f"{description}{marker} ({orig_desc} v{orig_version})"
    if orig_desc and orig_version is not None
    else description
  )

  header = _patch_header(header_line, description=full_desc, date=date, version=version,
                         locale=locale_from_header)
  kaomoji_lines = _build_kaomoji_lines(kaomoji_map, word_joiner=word_joiner)
  return "\n".join([header] + existing + kaomoji_lines)


def _patch_header(header: str, description: str, date: int, version: int = 1,
                  locale: str | None = None) -> str:
  parts = _HEADER_RE.split(header)
  seen_version = False
  new_parts = []
  for part in parts:
    if part.startswith("description="):
      new_parts.append(f"description={description}")
    elif part.startswith("date="):
      new_parts.append(f"date={date}")
    elif part.startswith("version="):
      new_parts.append(f"version={version}")
      seen_version = True
    elif part.startswith("dictionary=") and locale is not None:
      new_parts.append(f"dictionary=kaomoji:{locale}")
    else:
      new_parts.append(part)
  if not seen_version:
    new_parts.append(f"version={version}")
  return ",".join(new_parts)


def _with_word_joiner(s: str) -> str:
  """Insert Unicode Word Joiner (U+2060) between each character
  to prevent the Unicode line breaker from splitting the string.
  Strips any existing joiners first, making the function idempotent."""
  s = s.replace("\u2060", "")
  if len(s) == 0:
    return s
  s = "\u2060".join(s)
  return f"\u2060{s}\u2060"


def _build_kaomoji_lines(
  kaomoji_map: dict[str, list[str]],
  word_joiner: bool = False,
) -> list[str]:
  lines: list[str] = []
  for kaomoji, words in kaomoji_map.items():
    shortcut = _with_word_joiner(kaomoji) if word_joiner else kaomoji
    for word in words:
      lines.append(f" word={word.lower()},f={KAOMOJI_FLAGS},not_a_word=true")
      lines.append(f"  shortcut={shortcut},f={KAOMOJI_FLAGS}")
  return lines


def _extract_tags(
  kaomoji_map: dict[str, list[str] | dict[str, list[str]]],
  locale: str | None = None,
  all_locales: bool = False,
  no_star: bool = False,
) -> dict[str, list[str]]:
  """Flatten per-locale tags or pass through flat lists.

  A special "*" key provides tags common to all locales.
  Pass no_star=True to exclude "*" tags.
  """
  result: dict[str, list[str]] = {}
  for kaomoji, tags in kaomoji_map.items():
    if isinstance(tags, dict):
      common = [] if no_star else tags.get("*", [])
      if all_locales:
        merged: list[str] = list(common)
        for loc, loc_tags in tags.items():
          if loc != "*":
            merged.extend(loc_tags)
        result[kaomoji] = merged
      elif locale is not None and locale in tags:
        result[kaomoji] = common + tags[locale]
      else:
        result[kaomoji] = common
    else:
      result[kaomoji] = tags
  return result


def compile_dict(combined_content: str, output_path: str, jar_path: str) -> None:
  if not Path(jar_path).is_file():
    raise RuntimeError(f"jar not found: {jar_path}")

  fd, combined_path = tempfile.mkstemp(suffix=".combined", text=True)
  try:
    with open(fd, "w", encoding="utf-8") as f:
      f.write(combined_content)
    cmd = ["java", "-jar", jar_path, "makedict", "-s", combined_path, "-d", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603
    if result.returncode != 0:
      raise RuntimeError(result.stderr.strip())
    print(f"Dictionary created: {output_path}")
  finally:
    Path(combined_path).unlink(missing_ok=True)


def _sanitize_tag(t: str) -> str:
  r"""Lowercase and remove punctuation and whitespace.

  Strips:
  - ASCII punctuation: ! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _ ` { | } ~
  - ASCII whitespace
  - Unicode punctuation (category P*)
  - Unicode separators (category Z*), which includes all Unicode whitespace beyond ASCII
  """
  ascii_block = string.punctuation + string.whitespace
  result: list[str] = []
  for c in t.lower():
    if c in ascii_block:
      continue
    cat = unicodedata.category(c)
    if cat.startswith("P") or cat.startswith("Z"):
      continue
    result.append(c)
  return "".join(result)


def _sanitize_tag_list(tags: list[str], kaomoji: str, loc_label: str = "") -> dict[str, list[str]]:
  """Sanitize each tag in a list, collect collapse warnings, and return a dict mapping each
  sanitized form to its original source tags.
  """
  result: dict[str, list[str]] = {}
  prefix = f" for {kaomoji}" + (f" ({loc_label})" if loc_label else "")
  for t in tags:
    if not isinstance(t, str):
      print(f"  WARNING: Non-string tag {repr(t)}{prefix} ignored.")
      continue
    s = _sanitize_tag(t)
    if not s:
      print(f'  WARNING: Tag "{t}"{prefix} became empty after sanitization.')
      continue
    result.setdefault(s, []).append(t)

  for s, sources in result.items():
    if len(sources) > 1:
      print(f"  WARNING: Tags {sources}{prefix} all collapse to \"{s}\"")
  return result


def _sanitize_input(
  kaomoji_map: dict[str, list[str] | dict[str, list[str]]],
) -> dict[str, list[str] | dict[str, list[str]]]:
  for kaomoji in kaomoji_map:
    locales = kaomoji_map[kaomoji]

    if isinstance(locales, list):
      tag_map = _sanitize_tag_list(locales, kaomoji)
      if not tag_map:
        print(
          f"  WARNING: All tags for {kaomoji} were empty after sanitization. "
          "Entry left as empty list, add new tags.",
        )
      kaomoji_map[kaomoji] = sorted(tag_map.keys())
      continue

    if not isinstance(locales, dict):
      print(
        f"  WARNING: Entry for {kaomoji} is neither a list nor a dict "
        f"(got {type(locales).__name__}), replacing with [].",
      )
      kaomoji_map[kaomoji] = []
      continue

    locale_sets: dict[str, set[str]] = {}
    for loc, tags in locales.items():
      if loc == "*":
        continue
      if not isinstance(tags, list):
        print(
          f"  WARNING: Value for {kaomoji} ({loc}) is not a list "
          f"(got {type(tags).__name__}), skipping.",
        )
        locale_sets[loc] = set()
        continue
      tag_map = _sanitize_tag_list(tags, kaomoji, loc)
      locale_sets[loc] = set(tag_map.keys())

    star_raw = locales.get("*")
    if not isinstance(star_raw, list):
      if star_raw is not None:
        print(
          f"  WARNING: Star value for {kaomoji} is not a list "
          f"(got {type(star_raw).__name__}), skipping.",
        )
      star_raw = []
    tag_map_star = _sanitize_tag_list(star_raw, kaomoji, "*")
    existing = set(tag_map_star.keys())

    if not locale_sets and not existing:
      continue

    if not existing and all(not v for v in locale_sets.values()):
      print(
        f"  WARNING: All tags for {kaomoji} were empty after sanitization. "
        "Entry left with empty locale lists, add new tags.",
      )
      kaomoji_map[kaomoji] = {loc: [] for loc in locales}
      continue

    if len(locale_sets) > 1:
      shared = set.intersection(*locale_sets.values())
    else:
      shared = set()

    star = existing | shared
    if not star:
      if all(not v for v in locale_sets.values()):
        continue
      entry: dict[str, list[str]] = {}
      for loc in locales:
        if loc == "*":
          continue
        entry[loc] = sorted(locale_sets.get(loc, set()))
      kaomoji_map[kaomoji] = entry
      continue

    ordered: dict[str, list[str]] = {"*": sorted(star)}
    for loc in locales:
      if loc == "*":
        continue
      ordered[loc] = sorted(locale_sets.get(loc, set()) - star)
    kaomoji_map[kaomoji] = ordered

  return kaomoji_map


def _check_java(args: argparse.Namespace) -> Path:
  """Verify java is on PATH and the jar exists. Returns resolved jar Path."""
  if not shutil.which("java"):
    print("error: 'java' is required but not found on PATH", file=sys.stderr)
    sys.exit(1)

  jar_path = Path(args.jar)
  if not jar_path.is_file():
    msg = f"jar not found: {args.jar}"
    if args.jar == str(SCRIPT_DIR / "aosp-dictionary-tools" / "dicttool_aosp.jar"):
      msg += "\nRun: git submodule update --init --recursive"
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)
  return jar_path


def _load_input(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
  """Resolve input path, parse JSON, return (data, kaomoji_map)."""
  if not args.input:
    args.input = str(SCRIPT_DIR / DEFAULT_INPUT)
    print(f"Using default kaomoji set ({args.input})", file=sys.stderr)

  try:
    with open(args.input, encoding="utf-8") as f:
      data = json.load(f)
  except json.JSONDecodeError as e:
    print(f"error: invalid JSON in {args.input}: {e}", file=sys.stderr)
    sys.exit(1)

  kaomoji_map = data.get("kaomoji")
  if not isinstance(kaomoji_map, dict):
    print("error: input JSON must contain a 'kaomoji' object", file=sys.stderr)
    sys.exit(1)
  return data, kaomoji_map


def _handle_sanitize(
    data: dict[str, Any], kaomoji_map: dict[str, Any], args: argparse.Namespace
) -> None:
  """If --sanitize-input was passed, sanitize in place and exit."""
  if not args.sanitize_input:
    return
  print("Sanitizing input..")
  data["kaomoji"] = _sanitize_input(kaomoji_map)
  print("Saving modified input file..")
  try:
    with open(args.input, mode="w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
  except Exception as ex:
    print(f"error: failed to write star locales: {ex}", file=sys.stderr)
    sys.exit(1)
  sys.exit(0)


def _resolve_locale(data: dict[str, Any], args: argparse.Namespace) -> str:
  locale: str | None = args.locale
  if locale is not None:
    return locale
  return str(data.get("locale") or data.get("locales", ["en"])[0])


def _make_output_path(locale: str, args: argparse.Namespace) -> str:
  output: str | None = args.output
  if output is not None:
    return output
  parts = ["kaomoji", locale]
  if args.all_locales:
    parts.append("all_locales")
  if args.merge_combined:
    parts.append("combined")
  return "_".join(parts) + ".dict"


def _resolve_version(data: dict[str, Any], args: argparse.Namespace) -> tuple[int, int]:
  """Return (version, build_version)."""
  version = data.get("version", args.version)
  if not isinstance(version, int) or version < 1:
    version = 1
  build_version = version + 1 if args.bump else version
  return version, build_version


def _resolve_description(data: dict[str, Any], locale: str, args: argparse.Namespace) -> str:
  desc_raw = data.get("description", args.description)
  if isinstance(desc_raw, dict):
    loc = data.get("locales", [None])[0]
    fallback: str = args.description
    if loc is not None:
      fallback = desc_raw.get(loc, args.description)
    return str(desc_raw.get(locale, fallback))
  return str(desc_raw)


def _bump_version(data: dict[str, Any], build_version: int, input_path: str) -> None:
  """Write bumped version back to the input JSON file."""
  data["version"] = build_version
  with open(input_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
  print(f"Bumped {input_path} version to {build_version}")


def _build_arg_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description="Build kaomoji dictionary for HeliBoard")
  parser.add_argument("input", nargs="?", help="Input JSON file with kaomoji data")
  parser.add_argument(
    "-o", "--output", default=None,
    help="Output .dict file path (default: kaomoji_<locale>.dict)",
  )
  parser.add_argument(
    "--jar",
    default=str(SCRIPT_DIR / "aosp-dictionary-tools" / "dicttool_aosp.jar"),
    help="Path to dicttool_aosp.jar (default: %(default)s)",
  )
  parser.add_argument(
    "-m", "--merge-combined", default=None,
    help="Path to .combined wordlist to merge kaomoji into (preserves locale & entries)",
  )
  parser.add_argument(
    "--keep-combined", action="store_true",
    help="Keep the intermediate .combined file",
  )
  parser.add_argument(
    "--locale", default=None,
    help="Dictionary locale (default: from input file, or 'en')",
  )
  parser.add_argument(
    "--description", default="Kaomoji dictionary",
    help="Dictionary description (JSON field takes precedence; default: %(default)s)",
  )
  parser.add_argument(
    "--version", type=int, default=1,
    help="Dictionary version (JSON field takes precedence; default: %(default)s)",
  )
  parser.add_argument(
    "--bump", action="store_true",
    help="Bump the version in the input JSON file",
  )
  parser.add_argument(
    "--all-locales", action="store_true",
    help="Include tags from all locales (not just the selected one)",
  )
  parser.add_argument(
    "--no-star-locale", action="store_true",
    help="Exclude tags from the '*' shared locale",
  )
  parser.add_argument(
    "--sanitize-input", action="store_true",
    help="Lowercase tags, remove duplicates, promote tags shared by all locales to '*', and exit",
  )
  parser.add_argument(
    "--word-joiner", action="store_true",
    help="Enable insertion of Unicode Word Joiner (U+2060) between kaomoji characters",
  )
  parser.add_argument(
    "-v", "--verbose", action="store_true",
    help="Print the full combined wordlist",
  )
  return parser


def main() -> None:
  args = _build_arg_parser().parse_args()
  _check_java(args)
  data, kaomoji_map = _load_input(args)
  _handle_sanitize(data, kaomoji_map, args)

  locale = _resolve_locale(data, args)
  args.output = _make_output_path(locale, args)
  _, build_version = _resolve_version(data, args)
  description = _resolve_description(data, locale, args)

  kaomoji_flat = _extract_tags(kaomoji_map, locale, args.all_locales,
                               no_star=args.no_star_locale)
  use_word_joiner = args.word_joiner

  if args.merge_combined:
    combined_path = Path(args.merge_combined)
    if not combined_path.is_file():
      print(f"error: combined file not found: {args.merge_combined}", file=sys.stderr)
      sys.exit(1)
    combined = merge_with_combined(
      kaomoji_flat, str(combined_path), description,
      version=build_version, all_locales=args.all_locales,
      word_joiner=use_word_joiner,
    )
  else:
    combined = build_combined(kaomoji_flat, locale, description, build_version,
                              word_joiner=use_word_joiner)

  if args.keep_combined:
    combined_out = Path(args.output).with_suffix(".combined")
    with open(combined_out, "w", encoding="utf-8") as f:
      f.write(combined)
    print(f"Wordlist written to: {combined_out}")

  if args.verbose:
    print(f"\nCombined wordlist ({len(kaomoji_map)} kaomoji):\n{combined}\n")
  print(f"Detected {len(kaomoji_map)} kaomoji")

  try:
    compile_dict(combined, args.output, args.jar)
  except RuntimeError as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)

  if args.bump:
    _bump_version(data, build_version, args.input)


if __name__ == "__main__":
  main()
