import json
from unittest.mock import MagicMock, patch

from tests.helpers import FREEZE_TS, _cp, bkd


def test_main_with_input_file(tmp_path, capsys):
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "locale": "de",
    "description": "German kaomoji",
    "version": 2,
    "kaomoji": {
      "(╯°□°)╯︵┻━┻": ["tischwurf"],
    },
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", "/tmp/test.dict", "--jar", "/tmp/jar", "--verbose",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[2] == "/tmp/jar"
  assert call_args[7] == "/tmp/test.dict"

  out = capsys.readouterr().out
  assert "de" in out
  assert "German kaomoji" in out


def test_main_without_input(tmp_path, capsys):
  fake_default = tmp_path / "kaomoji.json"
  fake_default.write_text(json.dumps({
    "kaomoji": {"¯\\_(ツ)_/¯": ["shrug"], "(╯°□°)╯︵┻━┻": ["tableflip"]},
  }), encoding="utf-8")
  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py",
      "-o", str(tmp_path / "default.dict"), "--jar", str(tmp_path / "jar"), "--verbose",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("build_kaomoji_dict.SCRIPT_DIR", tmp_path), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[7] == str(tmp_path / "default.dict")

  out = capsys.readouterr().out
  assert "shrug" in out
  assert "tableflip" in out


def test_main_without_input_non_en_locale_uses_default_json(tmp_path, capsys):
  fake_default = tmp_path / "kaomoji.json"
  fake_default.write_text(json.dumps({
    "kaomoji": {"¯\\_(ツ)_/¯": ["shrug"]},
  }), encoding="utf-8")
  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py",
      "--jar", str(tmp_path / "dummy.jar"),
      "--locale", "da",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("build_kaomoji_dict.SCRIPT_DIR", tmp_path), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  err = capsys.readouterr().err
  assert "Using default kaomoji set" in err


def test_main_keep_combined(tmp_path, capsys):
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "kaomoji": {"¯\\_(ツ)_/¯": ["shrug"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
    "build_kaomoji_dict.py", str(input_file),
    "-o", str(tmp_path / "out.dict"),
    "--keep-combined",
  ]), patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  combined_path = tmp_path / "out.combined"
  assert combined_path.exists()
  content = combined_path.read_text(encoding="utf-8")
  assert "shrug" in content

  out = capsys.readouterr().out
  assert "Wordlist written to" in out


def test_main_no_bump_keeps_file_unchanged(tmp_path):
  initial_version = 7
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "version": initial_version,
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", str(tmp_path / "out.dict"), "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["version"] == initial_version


def test_main_no_bump_uses_original_version_in_build(tmp_path, capsys):
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "version": 4,
    "kaomoji": {"¯\\_(ツ)_/¯": ["shrug"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", str(tmp_path / "out.dict"), "--jar", str(tmp_path / "dummy.jar"),
      "--verbose",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  out = capsys.readouterr().out
  assert "version=4" in out
  assert "Bumped" not in out
