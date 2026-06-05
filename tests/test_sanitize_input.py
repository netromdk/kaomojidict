# pylint: disable=protected-access
import json
from unittest.mock import patch

import pytest

from tests.helpers import bkd


@pytest.mark.parametrize("kaomoji,expected", [
  (
    {"(◕‿◕)": ["happy"]},
    {"(◕‿◕)": ["happy"]},
  ),
  (
    {"(◕‿◕)": {"en": ["happy", "cute"], "da": ["glad", "sød"]}},
    {"(◕‿◕)": {"en": ["happy", "cute"], "da": ["glad", "sød"]}},
  ),
  (
    {"(◕‿◕)": {"en": ["happy"], "da": ["happy"]}},
    {"(◕‿◕)": {"en": [], "da": [], "*": ["happy"]}},
  ),
  (
    {"(◕‿◕)": {"*": ["smile"], "en": ["happy"], "da": ["glad"]}},
    {"(◕‿◕)": {"en": ["happy"], "da": ["glad"], "*": ["smile"]}},
  ),
  (
    {"(◕‿◕)": {"*": ["smile"], "en": ["happy", "smile"], "da": ["glad"]}},
    {"(◕‿◕)": {"en": ["happy"], "da": ["glad"], "*": ["smile"]}},
  ),
  (
    {"(◕‿◕)": {"en": ["hi", "bye"], "da": ["hi", "hej"]}},
    {"(◕‿◕)": {"en": ["bye"], "da": ["hej"], "*": ["hi"]}},
  ),
  (
    {"(◕‿◕)": {"en": ["a", "b"], "da": ["a", "b"]}},
    {"(◕‿◕)": {"en": [], "da": [], "*": ["a", "b"]}},
  ),
  (
    {"(◕‿◕)": {"*": ["shared"], "en": ["shared", "unique"], "da": ["shared", "unik"]}},
    {"(◕‿◕)": {"en": ["unique"], "da": ["unik"], "*": ["shared"]}},
  ),
  (
    {"(◕‿◕)": {"*": ["x"], "en": ["x", "y"], "da": ["x", "z"]},
     "¯\\_(ツ)_/¯": {"en": ["a"], "da": ["a"]}},
    {"(◕‿◕)": {"en": ["y"], "da": ["z"], "*": ["x"]},
     "¯\\_(ツ)_/¯": {"en": [], "da": [], "*": ["a"]}},
  ),
  (
    {"(◕‿◕)": {"en": ["Happy"], "da": ["happy"]}},
    {"(◕‿◕)": {"en": [], "da": [], "*": ["happy"]}},
  ),
  (
    {"(◕‿◕)": {"en": ["Happy", "cute"], "da": ["Cute", "glad"]}},
    {"(◕‿◕)": {"en": ["happy"], "da": ["glad"], "*": ["cute"]}},
  ),
  (
    {"(◕‿◕)": {"*": ["SMILE"], "en": ["smile", "happy"], "da": ["glad"]}},
    {"(◕‿◕)": {"en": ["happy"], "da": ["glad"], "*": ["smile"]}},
  ),
  (
    {"(◕‿◕)": ["A", "a", "B"]},
    {"(◕‿◕)": ["a", "b"]},
  ),
  (
    {"(◕‿◕)": ["UPPER", "upper", "Upper"]},
    {"(◕‿◕)": ["upper"]},
  ),
])
def test_sanitize_input(kaomoji, expected):
  result = bkd._sanitize_input(kaomoji)
  for k, v in expected.items():
    rv = result[k]
    if isinstance(rv, dict):
      for loc, tags in v.items():
        assert sorted(rv[loc]) == sorted(tags), f"{k}[{loc}]: {rv[loc]} != {tags}"
    else:
      assert rv == v, f"{k}: {rv} != {v}"


def test_sanitize_input_flat_unchanged():
  original = {"(◕‿◕)": ["flat"]}
  result = bkd._sanitize_input(original)
  assert result is original
  assert result["(◕‿◕)"] == original["(◕‿◕)"]


def test_sanitize_input_empty_map():
  assert not bkd._sanitize_input({})


def test_sanitize_input_no_locales():
  kaomoji = {"(◕‿◕)": {}}
  result = bkd._sanitize_input(kaomoji)
  assert result["(◕‿◕)"] == kaomoji["(◕‿◕)"]


def test_sanitize_input_only_star():
  kaomoji = {"(◕‿◕)": {"*": ["only"]}}
  result = bkd._sanitize_input(kaomoji)
  assert result["(◕‿◕)"] == kaomoji["(◕‿◕)"]


def test_sanitize_input_single_locale_no_shared():
  kaomoji = {"(◕‿◕)": {"en": ["hi"]}}
  result = bkd._sanitize_input(kaomoji)
  assert result["(◕‿◕)"] == kaomoji["(◕‿◕)"]


def test_sanitize_input_single_locale_with_existing_star():
  kaomoji = {"(◕‿◕)": {"*": ["global"], "en": ["global", "local"]}}
  result = bkd._sanitize_input(kaomoji)
  assert result["(◕‿◕)"] == {"en": ["local"], "*": ["global"]}


def test_sanitize_input_duplicates_in_input():
  kaomoji = {"(◕‿◕)": {"en": ["a", "a", "b"], "da": ["a", "b", "b"]}}
  result = bkd._sanitize_input(kaomoji)
  en = result["(◕‿◕)"]["en"]
  da = result["(◕‿◕)"]["da"]
  star = result["(◕‿◕)"]["*"]
  assert sorted(star) == ["a", "b"]
  assert not en
  assert not da


def test_sanitize_input_star_first():
  kaomoji = {"(◕‿◕)": {"en": ["a", "b"], "da": ["a", "c"]}}
  result = bkd._sanitize_input(kaomoji)
  keys = list(result["(◕‿◕)"].keys())
  assert keys[0] == "*", f"expected '*' first, got {keys}"


def test_sanitize_input_star_first_preserves_existing_star():
  kaomoji = {"(◕‿◕)": {"da": ["b"], "en": ["a"], "*": ["x"]}}
  result = bkd._sanitize_input(kaomoji)
  keys = list(result["(◕‿◕)"].keys())
  assert keys[0] == "*", f"expected '*' first, got {keys}"


def test_sanitize_input_star_first_when_no_shared():
  kaomoji = {"(◕‿◕)": {"da": ["a"], "en": ["b"], "*": ["x"]}}
  result = bkd._sanitize_input(kaomoji)
  keys = list(result["(◕‿◕)"].keys())
  assert keys[0] == "*", f"expected '*' first, got {keys}"


def test_main_sanitize_input_flag(tmp_path):
  input_file = tmp_path / "kaomoji.json"
  original = {
    "version": 1,
    "kaomoji": {
      "(◕‿◕)": {
        "en": ["happy", "cute"],
        "da": ["happy", "glad"],
      },
    },
  }
  input_file.write_text(json.dumps(original), encoding="utf-8")

  with patch("sys.argv", [
    "build_kaomoji_dict.py", str(input_file),
    "--sanitize-input",
  ]), patch("shutil.which", return_value="/usr/bin/java"):
    with pytest.raises(SystemExit) as exc:
      bkd.main()
  assert exc.value.code == 0

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  kaomoji = updated["kaomoji"]["(◕‿◕)"]
  assert kaomoji["*"] == ["happy"]
  assert kaomoji["en"] == ["cute"]
  assert kaomoji["da"] == ["glad"]


def test_main_sanitize_input_no_changes(tmp_path):
  input_file = tmp_path / "kaomoji.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"(◕‿◕)": ["flat"]},
  }), encoding="utf-8")

  with patch("sys.argv", [
    "build_kaomoji_dict.py", str(input_file),
    "--sanitize-input",
  ]), patch("shutil.which", return_value="/usr/bin/java"):
    with pytest.raises(SystemExit) as exc:
      bkd.main()
  assert exc.value.code == 0

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["kaomoji"]["(◕‿◕)"] == ["flat"]


def test_main_sanitize_input_preserves_other_data(tmp_path):
  input_file = tmp_path / "kaomoji.json"
  input_file.write_text(json.dumps({
    "version": 5,
    "description": "My kaomoji",
    "locales": ["en", "da"],
    "kaomoji": {
      "(◕‿◕)": {"en": ["a"], "da": ["a"]},
    },
  }), encoding="utf-8")

  with patch("sys.argv", [
    "build_kaomoji_dict.py", str(input_file),
    "--sanitize-input",
  ]), patch("shutil.which", return_value="/usr/bin/java"):
    with pytest.raises(SystemExit) as exc:
      bkd.main()
  assert exc.value.code == 0

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["version"] == 5
  assert updated["description"] == "My kaomoji"
  assert updated["locales"] == ["en", "da"]

  kaomoji = updated["kaomoji"]["(◕‿◕)"]
  assert kaomoji["*"] == ["a"]
  assert kaomoji["en"] == []
  assert kaomoji["da"] == []


@pytest.mark.parametrize("kaomoji,locale,all_locales,expected", [
  ({"(◕‿◕)": {"*": ["😄", ":D"], "en": ["happy", "cute"], "da": ["glad", "sød"]}},
   "en", False, ["😄", ":D", "happy", "cute"]),
  ({"(◕‿◕)": {"*": ["😄", ":D"], "en": ["happy", "cute"], "da": ["glad", "sød"]}},
   "da", False, ["😄", ":D", "glad", "sød"]),
  ({"(◕‿◕)": {"*": ["😄", ":D"], "en": ["happy", "cute"], "da": ["glad", "sød"]}},
   "en", True, ["😄", ":D", "happy", "cute", "glad", "sød"]),
  ({"(◕‿◕)": {"*": ["😄", ":D"], "en": ["happy"]}},
   "da", False, ["😄", ":D"]),
])
def test_extract_tags_with_star(kaomoji, locale, all_locales, expected):
  result = bkd._extract_tags(kaomoji, locale=locale, all_locales=all_locales)
  assert sorted(result[list(kaomoji.keys())[0]]) == sorted(expected)


@pytest.mark.parametrize("kaomoji,locale,all_locales,expected", [
  ({"(◕‿◕)": {"*": ["😄"], "en": ["happy", "cute"]}},
   "en", False, ["happy", "cute"]),
  ({"(◕‿◕)": {"*": ["😄"], "en": ["happy", "cute"]}},
   "en", True, ["happy", "cute"]),
])
def test_extract_tags_no_star(kaomoji, locale, all_locales, expected):
  result = bkd._extract_tags(kaomoji, locale=locale, all_locales=all_locales, no_star=True)
  assert sorted(result[list(kaomoji.keys())[0]]) == sorted(expected)
