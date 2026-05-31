import json
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
    result = bkd.merge_with_combined(kaomoji, str(src), "Kaomoji dictionary")

  lines = result.split("\n")
  assert len(lines) == 5
  assert lines[0] == (
    "dictionary=emoji:en,locale=en,"
    f"description=Kaomoji dictionary,date={FREEZE_TS},version=4"
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

  header = result.split("\n")[0]
  assert "dictionary=emoji:da" in header
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

  header = result.split("\n")[0]
  assert "description=Updated description" in header
  assert "Old desc" not in header


def test_merge_with_combined_file_not_found():
  with pytest.raises(FileNotFoundError, match="Combined file not found"):
    bkd.merge_with_combined({"foo": ["bar"]}, "/nonexistent/combined")


def test_merge_with_combined_empty_file(tmp_path):
  src = tmp_path / "empty.combined"
  src.write_text("", encoding="utf-8")

  with pytest.raises(ValueError, match="Empty combined file"):
    bkd.merge_with_combined({"foo": ["bar"]}, str(src))


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
  assert "version=2" in lines[0]
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
    result = bkd.merge_with_combined(kaomoji, str(src), "Kaomoji")

  lines = result.split("\n")
  assert len(lines) == 8
  assert lines[1] == " word=existing,f=100"
  assert lines[2] == f" word=x,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[3] == f"  shortcut=a,f={bkd.KAOMOJI_FLAGS}"
  assert lines[4] == f" word=y,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[5] == f"  shortcut=a,f={bkd.KAOMOJI_FLAGS}"
  assert lines[6] == f" word=z,f={bkd.KAOMOJI_FLAGS},not_a_word=true"
  assert lines[7] == f"  shortcut=b,f={bkd.KAOMOJI_FLAGS}"


def test_main_merge_combined(tmp_path, capsys):
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
  assert call_args[7] == str(tmp_path / "emoji_en.dict")


def test_main_merge_combined_explicit_output(tmp_path, capsys):
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

  kept_combined = tmp_path / "emoji_en.combined"
  assert kept_combined.exists()
  content = kept_combined.read_text(encoding="utf-8")
  assert "happy" in content
  assert "smile" in content
  assert "heart" in content

  out = capsys.readouterr().out
  assert "Wordlist written to" in out


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
