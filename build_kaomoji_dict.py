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
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = "kaomoji.json"

# Flag bits for the AOSP dictionary combined format:
NOT_A_WORD = 2  # Entry is a shortcut, not a real word.
HAS_EMOJI = 4   # Render the shortcut content inline in suggestions.
PROBING = 8     # Include in suggestion-bar probing.
KAOMOJI_FLAGS = NOT_A_WORD | HAS_EMOJI | PROBING


def build_combined(
  kaomoji_map: dict[str, list[str]],
  locale: str = "en",
  description: str = "Kaomoji dictionary",
  version: int = 1,
  date: int | None = None,
) -> str:
  if date is None:
    date = int(time.time())
  lines = [
    f"dictionary=kaomoji:{locale},locale={locale},"
    f"description={description},date={date},version={version}",
  ]
  lines += _build_kaomoji_lines(kaomoji_map)
  return "\n".join(lines)


def merge_with_combined(
  kaomoji_map: dict[str, list[str]],
  combined_path: str | Path,
  description: str = "Kaomoji dictionary",
  version: int = 1,
  all_locales: bool = False,
  date: int | None = None,
) -> str:
  """Merge kaomoji entries into an existing .combined wordlist file."""
  if date is None:
    date = int(time.time())

  combined = Path(combined_path)
  if not combined.is_file():
    raise FileNotFoundError(f"Combined file not found: {combined_path}")

  with open(combined, encoding="utf-8") as f:
    content = f.read()

  lines = content.rstrip("\n").split("\n")
  if not lines or not lines[0].strip():
    raise ValueError("Empty combined file")

  header = lines[0]
  orig_desc = ""
  orig_version = None
  locale_from_header = ""
  for part in header.split(","):
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

  header = _patch_header(header, description=full_desc, date=date, version=version,
                         locale=locale_from_header)
  kaomoji_lines = _build_kaomoji_lines(kaomoji_map)
  existing = lines[1:] if len(lines) > 1 else []
  return "\n".join([header] + existing + kaomoji_lines)


def _patch_header(header: str, description: str, date: int, version: int = 1,
                  locale: str | None = None) -> str:
  parts = header.split(",")
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


def _build_kaomoji_lines(kaomoji_map: dict[str, list[str]]) -> list[str]:
  lines: list[str] = []
  for kaomoji, words in kaomoji_map.items():
    for word in words:
      lines.append(f" word={word.lower()},f={KAOMOJI_FLAGS},not_a_word=true")
      lines.append(f"  shortcut={kaomoji},f={KAOMOJI_FLAGS}")
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


def _sanitize_input(
  kaomoji_map: dict[str, list[str] | dict[str, list[str]]],
) -> dict[str, list[str] | dict[str, list[str]]]:
  for kaomoji in kaomoji_map:
    locales = kaomoji_map[kaomoji]

    if isinstance(locales, list):
      kaomoji_map[kaomoji] = sorted({t.lower() for t in locales})
      continue

    if not isinstance(locales, dict):
      continue

    locale_sets = {
      loc: {t.lower() for t in tags} for loc, tags in locales.items() if loc != "*"
    }
    if not locale_sets:
      continue

    existing = {t.lower() for t in locales.get("*", [])}
    if len(locale_sets) > 1:
      shared = set.intersection(*locale_sets.values())
    else:
      shared = set()

    star = existing | shared
    if not star:
      continue

    ordered: dict[str, list[str]] = {"*": sorted(star)}
    for loc in locales:
      if loc == "*":
        continue
      ordered[loc] = sorted(locale_sets[loc] - star)
    kaomoji_map[kaomoji] = ordered

  return kaomoji_map


def main() -> None:
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
    "-v", "--verbose", action="store_true",
    help="Print the full combined wordlist",
  )

  args = parser.parse_args()

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

  if args.sanitize_input:
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

  locale = args.locale if args.locale is not None else (
    data.get("locale") or data.get("locales", ["en"])[0]
  )

  if args.output is None:
    suffix = ""
    if args.all_locales:
      suffix = "_all_locales"
    if args.merge_combined:
      suffix += "_combined"
    args.output = f"kaomoji_{locale}{suffix}.dict"

  version = data.get("version", args.version)
  if not isinstance(version, int) or version < 1:
    version = 1
  build_version = version + 1 if args.bump else version

  desc_raw = data.get("description", args.description)
  description: str
  if isinstance(desc_raw, dict):
    fallback = desc_raw.get(data.get("locales", [None])[0], args.description)
    description = desc_raw.get(locale, fallback)
  else:
    description = desc_raw

  kaomoji_flat = _extract_tags(kaomoji_map, locale, args.all_locales,
                               no_star=args.no_star_locale)

  if args.merge_combined:
    combined_path = Path(args.merge_combined)
    if not combined_path.is_file():
      print(f"error: combined file not found: {args.merge_combined}", file=sys.stderr)
      sys.exit(1)
    combined = merge_with_combined(
      kaomoji_flat, str(combined_path), description,
      version=build_version, all_locales=args.all_locales,
    )
  else:
    combined = build_combined(kaomoji_flat, locale, description, build_version)

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
    data["version"] = build_version
    with open(args.input, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
      f.write("\n")
    print(f"Bumped {args.input} version to {build_version}")


if __name__ == "__main__":
  main()
