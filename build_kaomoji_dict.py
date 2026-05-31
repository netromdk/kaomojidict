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
      "¯\\_(ツ)_/¯": ["shrug", "shrugging"],
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
DEFAULT_INPUT = "kaomoji_en.json"

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
    f"dictionary=emoji:{locale},locale={locale},"
    f"description={description},date={date},version={version}",
  ]
  for kaomoji, words in kaomoji_map.items():
    for word in words:
      lines.append(f" word={word},f={KAOMOJI_FLAGS},not_a_word=true")
      lines.append(f"  shortcut={kaomoji},f={KAOMOJI_FLAGS}")
  return "\n".join(lines)


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
    "--no-bump", action="store_true",
    help="Do not bump the version in the input JSON file",
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

  with open(args.input, encoding="utf-8") as f:
    data = json.load(f)
  kaomoji_map = data.get("kaomoji")
  if not isinstance(kaomoji_map, dict):
    print("error: input JSON must contain a 'kaomoji' object", file=sys.stderr)
    sys.exit(1)
  locale = args.locale if args.locale is not None else (data.get("locale") or "en")
  if args.output is None:
    args.output = f"kaomoji_{locale}.dict"
  description = data.get("description", args.description)
  version = data.get("version", args.version)
  if not isinstance(version, int) or version < 1:
    version = 1
  build_version = version + 1 if not args.no_bump else version

  combined = build_combined(kaomoji_map, locale, description, build_version)

  if args.keep_combined:
    combined_path = str(Path(args.output).with_suffix(".combined"))
    with open(combined_path, "w", encoding="utf-8") as f:
      f.write(combined)
    print(f"Wordlist written to: {combined_path}")

  if args.verbose:
    print(f"\nCombined wordlist ({len(kaomoji_map)} kaomoji):\n{combined}\n")
  print(f"Detected {len(kaomoji_map)} kaomoji")

  try:
    compile_dict(combined, args.output, args.jar)
  except RuntimeError as e:
    print(f"error: {e}", file=sys.stderr)
    sys.exit(1)

  if not args.no_bump:
    data["version"] = build_version
    with open(args.input, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=2, ensure_ascii=False)
      f.write("\n")
    print(f"Bumped {args.input} version to {build_version}")


if __name__ == "__main__":
  main()
