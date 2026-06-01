import json
from unittest.mock import MagicMock, patch

import pytest

from tests.helpers import FREEZE_TS, _cp, bkd


def test_main_java_missing(tmp_path, capsys):
  fake_default = tmp_path / "kaomoji_en.json"
  fake_default.write_text(json.dumps({
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")
  with patch("sys.argv", ["build_kaomoji_dict.py"]), \
      patch("shutil.which", return_value=None), \
      patch("build_kaomoji_dict.SCRIPT_DIR", tmp_path):
    with pytest.raises(SystemExit) as exc:
      bkd.main()
  assert exc.value.code == 1
  out = capsys.readouterr().err
  assert "java" in out and "required" in out


def test_main_default_output_matches_locale(tmp_path):
  input_file = tmp_path / "da_kaomoji.json"
  input_file.write_text(json.dumps({
    "version": 1,
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "--locale", "da", "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  call_args = mock_run.call_args[0][0]
  assert call_args[7] == "kaomoji_da.dict"


def test_main_version_bumped_on_success(tmp_path):
  input_version = 5
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "version": input_version,
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", str(tmp_path / "out.dict"), "--jar", str(tmp_path / "dummy.jar"),
      "--bump",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["version"] == input_version + 1


def test_main_version_not_bumped_on_failure(tmp_path):
  input_version = 3
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps({
    "version": input_version,
    "kaomoji": {"foo": ["bar"]},
  }), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp(returncode=1, stderr="fail"))
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", str(tmp_path / "out.dict"), "--jar", str(tmp_path / "dummy.jar"),
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    with pytest.raises(SystemExit):
      bkd.main()

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["version"] == input_version


@pytest.mark.parametrize("input_overrides", [
    {"kaomoji": {"foo": ["bar"]}},
    {"version": "abc", "kaomoji": {"foo": ["bar"]}},
    {"version": 0, "kaomoji": {"foo": ["bar"]}},
])
def test_main_version_defaults_to_one_when_bumped(tmp_path, input_overrides):
  input_file = tmp_path / "test.json"
  input_file.write_text(json.dumps(input_overrides), encoding="utf-8")

  mock_run = MagicMock(return_value=_cp())
  with patch("sys.argv", [
      "build_kaomoji_dict.py", str(input_file),
      "-o", str(tmp_path / "out.dict"), "--jar", str(tmp_path / "dummy.jar"),
      "--bump",
    ]), \
      patch("shutil.which", return_value="/usr/bin/java"), \
      patch("pathlib.Path.is_file", return_value=True), \
      patch("subprocess.run", mock_run), \
      patch("time.time", return_value=FREEZE_TS):
    bkd.main()

  updated = json.loads(input_file.read_text(encoding="utf-8"))
  assert updated["version"] == 2
