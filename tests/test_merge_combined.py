import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.helpers import FREEZE_TS, _cp, bkd


EN_COMBINED = (
  "dictionary=emoji:en,locale=en,"
  "description=Emoji dictionary,date=1000000000,version=3\n"
  " word=smile,f=200\n"
  " word=heart,f=150\n"
)


def test_merge_with_combined_basic(tmp_path):
  src = tmp_path / "emoji_en.combined"
  src.write_text(EN_COMBINED, encoding="utf-8")

  kaomoji = {"¯\\_(ツ)_/¯": ["shrug"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(
      kaomoji, str(src), "Kaomoji dictionary",
      word_joiner=False,
    )

  lines = result.split("\n")
  assert len(lines) == 5
  assert lines[0] == (
    "dictionary=kaomoji:en,locale=en,"
    f"description=Kaomoji dictionary (Emoji dictionary v3),date={FREEZE_TS},version=1"
  )
  assert lines[1] == " word=smile,f=200"
  assert lines[2] == " word=heart,f=150"
  assert lines[3] == f" word=shrug,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[4] == rf"  shortcut=¯\_(ツ)_/¯,f={bkd.KAOMOJI_FLAGS}"


def test_merge_with_combined_preserves_header_type_and_locale(tmp_path):
  src = tmp_path / "emoji_da.combined"
  src.write_text(
    "dictionary=emoji:da,locale=da,description=Dansk emoji,date=999999999,version=2\n",
    encoding="utf-8",
  )

  kaomoji = {"(◕‿◕)": ["glad"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(kaomoji, str(src), "Kaomoji")

  header = result.split("\n", maxsplit=1)[0]
  assert "dictionary=kaomoji:da" in header
  assert "locale=da" in header


def test_merge_with_combined_updates_description(tmp_path):
  src = tmp_path / "test.combined"
  src.write_text(
    "dictionary=emoji:en,locale=en,description=Old desc,date=1,version=1\n",
    encoding="utf-8",
  )

  kaomoji = {"foo": ["bar"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(kaomoji, str(src), "Updated description")

  header = result.split("\n", maxsplit=1)[0]
  assert "description=Updated description (Old desc v1)" in header


@pytest.mark.parametrize("content,error_cls,pattern", [
    (None, FileNotFoundError, "Combined file not found"),
    ("", ValueError, "Empty combined file"),
])
def test_merge_with_combined_errors(tmp_path, content, error_cls, pattern):
  if content is not None:
    src = tmp_path / "test.combined"
    src.write_text(content, encoding="utf-8")
    path = str(src)
  else:
    path = "/nonexistent/combined"
  with pytest.raises(error_cls, match=pattern):
    bkd.merge_with_combined({"foo": ["bar"]}, path)


def test_merge_with_combined_comma_in_description(tmp_path):
  """Commas inside description values must not break header parsing."""
  src = tmp_path / "test.combined"
  src.write_text(
    "dictionary=emoji:en,locale=en,description=Hello, world,date=1,version=1\n"
    " word=test,f=100\n",
    encoding="utf-8",
  )
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(
      {"foo": ["bar"]}, str(src), "Kaomoji", word_joiner=False
    )
  header = result.split("\n", maxsplit=1)[0]
  assert "description=Kaomoji (Hello, world v1)" in header


def test_merge_with_combined_no_existing_entries(tmp_path):
  src = tmp_path / "header_only.combined"
  src.write_text(
    "dictionary=emoji:en,locale=en,description=Only header,date=1,version=1\n",
    encoding="utf-8",
  )

  kaomoji = {"(╯°□°)╯︵┻━┻": ["tableflip"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(kaomoji, str(src), "Kaomoji")

  lines = result.split("\n")
  assert len(lines) == 3
  assert "version=1" in lines[0]
  assert "tableflip" in lines[1]


def test_merge_with_combined_multiple_kaomoji(tmp_path):
  src = tmp_path / "multi.combined"
  src.write_text(
    "dictionary=emoji:en,locale=en,description=Test,date=1,version=1\n"
    " word=existing,f=100\n",
    encoding="utf-8",
  )

  kaomoji = {"a": ["x", "y"], "b": ["z"]}
  with patch("time.time", return_value=FREEZE_TS):
    result = bkd.merge_with_combined(
      kaomoji, str(src), "Kaomoji", word_joiner=False
    )

  lines = result.split("\n")
  assert len(lines) == 8
  assert lines[1] == " word=existing,f=100"
  assert lines[2] == f" word=x,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[3] == f"  shortcut=a,f={bkd.KAOMOJI_FLAGS}"
  assert lines[4] == f" word=y,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[5] == f"  shortcut=a,f={bkd.KAOMOJI_FLAGS}"
  assert lines[6] == f" word=z,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[7] == f"  shortcut=b,f={bkd.KAOMOJI_FLAGS}"


def test_main_merge_combined(tmp_path):
  combined_file = tmp_path / "emoji_en.combined"
  combined_file.write_text(EN_COMBINED, encoding="utf-8")

  input_file = tmp_path / "kaomoji_en.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"¯\\_(ツ)_/¯": ["shrug"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-m", str(combined_file),
      "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[7] == "kaomoji_en_combined.dict"


def test_main_merge_combined_explicit_output(tmp_path):
  combined_file = tmp_path / "emoji_en.combined"
  combined_file.write_text(EN_COMBINED, encoding="utf-8")

  input_file = tmp_path / "kaomoji_en.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  explicit_out = tmp_path / "custom.dict"
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-m", str(combined_file),
      "-o", str(explicit_out),
      "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[7] == str(explicit_out)


def test_main_merge_combined_keep_combined(tmp_path, capsys):
  combined_file = tmp_path / "emoji_en.combined"
  combined_file.write_text(EN_COMBINED, encoding="utf-8")

  input_file = tmp_path / "kaomoji_en.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"(◕‿◕)": ["happy"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-m", str(combined_file),
      "--keep-combined",
      "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  out = capsys.readouterr().out
  assert "Wordlist written to: kaomoji_en_combined.combined" in out

  kept = Path("kaomoji_en_combined.combined")
  assert kept.exists()
  content = kept.read_text(encoding="utf-8")
  assert "happy" in content
  assert "smile" in content
  assert "heart" in content
  kept.unlink()


def test_main_merge_combined_missing_file(tmp_path):
  input_file = tmp_path / "kaomoji_en.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  jar_file = tmp_path / "dicttool_aosp.jar"
  jar_file.write_text("")

  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-m", str(tmp_path / "nonexistent.combined"),
      "--jar", str(jar_file),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"):
    with pytest.raises(SystemExit) as exc:
      bkd.main()
    assert exc.value.code == 1


# pylint: disable=protected-access

@pytest.mark.parametrize("kaomoji,locale,all_locales,expected", [
    ({"(╯°□°)╯︵┻━┻": ["tableflip", "rage"]},
     "en", False, ["tableflip", "rage"]),
    ({"(◕‿◕)": {"en": ["happy", "cute"], "da": ["glad", "sød"]}},
     "da", False, ["glad", "sød"]),
    ({"(╯°□°)╯︵┻━┻": {"en": ["tableflip", "rage"], "da": ["bordvæltning", "raseri"]}},
     "en", True, ["tableflip", "rage", "bordvæltning", "raseri"]),
    ({"(◕‿◕)": {"en": ["happy"]}},
     "da", False, []),
])
def test_extract_tags(kaomoji, locale, all_locales, expected):
  result = bkd._extract_tags(kaomoji, locale=locale, all_locales=all_locales)
  assert sorted(result[list(kaomoji.keys())[0]]) == sorted(expected)


def test_main_all_locales(tmp_path):
  combined_file = tmp_path / "emoji_en.combined"
  combined_file.write_text(EN_COMBINED, encoding="utf-8")

  input_file = tmp_path / "kaomoji.json"
  input_file.write_text(json.dumps({
    "locales": ["en", "da"],
    "kaomoji": {
      "(◕‿◕)": {"en": ["happy"], "da": ["glad"]},
    },
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "--locale", "en", "--all-locales",
      "-m", str(combined_file),
      "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[7] == "kaomoji_en_all_locales_combined.dict"


def test_main_all_locales_combined_desc(tmp_path, capsys):
  combined_file = tmp_path / "emoji_da.combined"
  combined_file.write_text(
    "dictionary=emoji:da,locale=da,description=Dansk emoji,date=1,version=1\n"
    " word=hej,f=100\n",
    encoding="utf-8",
  )

  input_file = tmp_path / "kaomoji.json"
  input_file.write_text(json.dumps({
    "locales": ["en", "da"],
    "description": {"en": "Eng dict", "da": "Da ordbog"},
    "kaomoji": {
      "(◕‿◕)": {"en": ["happy"], "da": ["glad"]},
    },
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "--locale", "da", "--all-locales",
      "-m", str(combined_file),
      "-o", str(tmp_path / "test.dict"),
      "--jar", str(tmp_path / "dummy.jar"),
      "--verbose",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  out = capsys.readouterr().out
  assert "Da ordbog <all locales> (Dansk emoji v1)" in out
